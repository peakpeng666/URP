"""Small SQLite store for immutable imported research records. No experiment execution."""
from __future__ import annotations
import hashlib, json, math, re, sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

STATES = {'queued','running','completed','failed','partial','unknown'}
COMPARISON_KEYS = ('metric','unit','direction','cohort','protocol','budget','aggregation','reference')
ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')
SECRET_KEYS = {'api_key','apikey','password','access_token','refresh_token','secret_key','authorization','private_key'}
SECRET_BYTES = re.compile(rb'(?:-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\bAKIA[A-Z0-9]{16}\b|\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b|(?i:api[_-]?key|access[_-]?token|password|secret[_-]?key)["\x27]?\s*[:=]\s*["\x27]?[A-Za-z0-9_-]{20,})')

class StoreError(ValueError):
    def __init__(self, code, message, status=400):
        super().__init__(message); self.code=code; self.status=status

def now(): return datetime.now(timezone.utc).isoformat()
def canonical(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(data): return hashlib.sha256(data).hexdigest()
def identifier(value):
    if not isinstance(value,str) or not ID.fullmatch(value): raise StoreError('invalid_id','标识仅支持字母、数字、点、短横线和下划线。')
    return value

def safe_path(root: Path, relative: str):
    if not isinstance(relative,str) or '\\' in relative: raise StoreError('unsafe_path','文件必须使用安全的相对路径。')
    p=PurePosixPath(relative)
    if p.is_absolute() or not p.parts or any(part in {'..','.'} for part in p.parts): raise StoreError('unsafe_path','文件不能越过导入目录。')
    root=root.resolve(); current=root
    for part in p.parts:
        current=current/part
        if current.is_symlink(): raise StoreError('unsafe_path','导入不接受符号链接。')
    if not current.resolve().is_relative_to(root): raise StoreError('unsafe_path','文件不能越过导入目录。')
    return current

def no_secrets(value):
    if isinstance(value,dict):
        for key,child in value.items():
            if str(key).lower() in SECRET_KEYS: raise StoreError('secret_rejected','描述包含凭据字段，导入已停止。')
            no_secrets(child)
    elif isinstance(value,list):
        for child in value:no_secrets(child)

def read_artifact(root, artifact):
    relative=artifact['path']; p=safe_path(root,relative)
    if p.name.startswith('.env') or p.suffix.lower() in {'.pem','.key'} or p.name.lower() in {'credentials','credentials.json','id_rsa','id_ed25519'}:
        raise StoreError('secret_rejected','凭据文件不能导入科研产物。')
    if not p.is_file(): raise StoreError('missing_artifact',f'缺少产物：{relative}',404)
    if p.stat().st_size>32*1024*1024: raise StoreError('artifact_too_large','单项产物上限32MiB；请只导入所需研究证据。',413)
    data=p.read_bytes()
    if SECRET_BYTES.search(data): raise StoreError('secret_rejected','产物疑似包含凭据，导入已停止；未保存文件。')
    if p.suffix.lower()=='.json':
        try:no_secrets(json.loads(data))
        except (UnicodeDecodeError,json.JSONDecodeError):pass
    return data

def validate(d):
    if not isinstance(d,dict): raise StoreError('invalid_descriptor','实验描述必须是JSON对象。')
    no_secrets(d)
    if d.get('schema_version')!=1: raise StoreError('schema_version','仅支持实验描述schema_version=1。')
    identifier(d.get('id'))
    for key in ('title','domain','kind'):
        if not isinstance(d.get(key),str) or not d[key].strip():raise StoreError('invalid_descriptor',f'缺少{key}。')
    if d.get('status') not in STATES: raise StoreError('invalid_status','实验状态无效，缺失状态请明确填写unknown。')
    for c in d.get('counts',[]):
        value=c.get('value')
        if not isinstance(c.get('unit'),str) or not c.get('scope'):raise StoreError('invalid_count','计数需要unit与scope。')
        if value is not None and (isinstance(value,bool) or not isinstance(value,int) or value<0):raise StoreError('invalid_count','计数必须为非负整数或null；未知不能填写0。')
    artifacts=d.get('artifacts',[]); ids=[identifier(a.get('id')) for a in artifacts]
    if len(ids)!=len(set(ids)):raise StoreError('duplicate_artifact','产物ID重复。')
    metric_ids=[]
    for m in d.get('metrics',[]):
        metric_ids.append(identifier(m.get('id')))
        v=m.get('value')
        if v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v)):raise StoreError('invalid_metric','指标值必须有限数值或null。')
        if m.get('source',{}).get('artifact_id') not in ids or not m.get('source',{}).get('locator'):raise StoreError('missing_metric_source','指标必须指向随包产物及其中字段。')
        comparison=m.get('comparison',{})
        if set(comparison)!=set(COMPARISON_KEYS):raise StoreError('invalid_comparison','比较口径需明确metric/unit/direction/cohort/protocol/budget/aggregation/reference。')
        if comparison.get('direction') not in {'min','max',None}:raise StoreError('invalid_comparison','指标方向仅min/max或未知null。')
        if any(v is not None and not isinstance(v,str) for v in comparison.values()):raise StoreError('invalid_comparison','比较口径字段必须为字符串或未知null。')
    if len(metric_ids)!=len(set(metric_ids)):raise StoreError('duplicate_metric','指标ID重复。')
    canonical(d) # also rejects non-JSON values and NaN in auxiliary fields

class Store:
    def __init__(self, path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS experiments (
              id TEXT NOT NULL, revision INTEGER NOT NULL, fingerprint TEXT NOT NULL,
              imported_at TEXT NOT NULL, descriptor TEXT NOT NULL,
              PRIMARY KEY(id,revision), UNIQUE(id,fingerprint));
            CREATE TABLE IF NOT EXISTS artifacts (
              experiment_id TEXT NOT NULL, revision INTEGER NOT NULL, id TEXT NOT NULL,
              filename TEXT NOT NULL, media_type TEXT NOT NULL, sha256 TEXT NOT NULL,
              content BLOB NOT NULL, PRIMARY KEY(experiment_id,revision,id),
              FOREIGN KEY(experiment_id,revision) REFERENCES experiments(id,revision));
            ''')
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=20); db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON')
        try:
            with db: yield db
        finally: db.close()
    def import_package(self, package):
        root=Path(package).resolve(); manifest=safe_path(root,'experiment.json')
        try:d=json.loads(manifest.read_text())
        except (OSError,UnicodeDecodeError,json.JSONDecodeError) as e:raise StoreError('invalid_descriptor','无法读取experiment.json。') from e
        validate(d)
        # Read all selected data before the transaction. A rejected file leaves no partial import.
        blobs=[(a,read_artifact(root,a)) for a in d.get('artifacts',[])]
        fingerprint=sha(canonical({'descriptor':d,'artifacts':{a['id']:sha(b) for a,b in blobs}}).encode())
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT revision FROM experiments WHERE id=? AND fingerprint=?',(d['id'],fingerprint)).fetchone()
            if old:return {'id':d['id'],'revision':old['revision'],'fingerprint':fingerprint,'reused':True}
            rev=db.execute('SELECT COALESCE(MAX(revision),0)+1 FROM experiments WHERE id=?',(d['id'],)).fetchone()[0]
            db.execute('INSERT INTO experiments VALUES(?,?,?,?,?)',(d['id'],rev,fingerprint,now(),canonical(d)))
            for a,b in blobs:
                db.execute('INSERT INTO artifacts VALUES(?,?,?,?,?,?,?)',(d['id'],rev,a['id'],PurePosixPath(a['path']).name,a.get('media_type','application/octet-stream'),sha(b),b))
        return {'id':d['id'],'revision':rev,'fingerprint':fingerprint,'reused':False}
    def get(self,id,revision=None):
        identifier(id)
        with self.connect() as db:
            row=db.execute('SELECT * FROM experiments WHERE id=? AND (? IS NULL OR revision=?) ORDER BY revision DESC LIMIT 1',(id,revision,revision)).fetchone()
            if not row:raise StoreError('not_found','没有这个实验或版本。',404)
            d=json.loads(row['descriptor']); refs=db.execute('SELECT id,filename,media_type,sha256,length(content) AS bytes FROM artifacts WHERE experiment_id=? AND revision=?',(id,row['revision'])).fetchall()
        d['artifacts']=[dict(r) for r in refs]
        return {**d,'revision':row['revision'],'fingerprint':row['fingerprint'],'imported_at':row['imported_at']}
    def list(self):
        with self.connect() as db:ids=[r[0] for r in db.execute('SELECT id FROM experiments GROUP BY id ORDER BY id')]
        return [{k:v for k,v in self.get(id).items() if k not in {'metrics','artifacts'}} for id in ids]
    def artifact(self,id,artifact_id,revision=None):
        identifier(artifact_id); record=self.get(id,revision)
        with self.connect() as db:
            row=db.execute('SELECT * FROM artifacts WHERE experiment_id=? AND revision=? AND id=?',(id,record['revision'],artifact_id)).fetchone()
        if not row:raise StoreError('not_found','没有这个产物。',404)
        data=bytes(row['content'])
        if sha(data)!=row['sha256']:raise StoreError('corrupt_artifact','数据库内产物哈希不一致，停止下载。',409)
        return {'filename':row['filename'],'media_type':row['media_type'],'sha256':row['sha256'],'bytes':len(data),'revision':record['revision']},data
    def compare(self,items):
        if not isinstance(items,list) or len(items)<2:raise StoreError('comparison_needs_items','请提供至少两个指标。')
        records=[]
        for item in items:
            d=self.get(item['experiment_id'],item.get('revision'))
            if d['status']!='completed':raise StoreError('unfinished_experiment','运行中、失败或未知状态不作为完整结果比较。',409)
            m=next((m for m in d['metrics'] if m['id']==item['metric_id']),None)
            if not m:raise StoreError('not_found','指标未收录。',404)
            if m['value'] is None or any(not v for v in m['comparison'].values()):raise StoreError('unknown_metric','指标或比较口径未知，不能按0比较。',409)
            records.append({'experiment_id':d['id'],'revision':d['revision'],**m})
        comparison=records[0]['comparison'];different=sorted({k for r in records[1:] for k in COMPARISON_KEYS if r['comparison'][k]!=comparison[k]})
        if different:raise StoreError('incomparable_metrics','口径不可比：'+', '.join(different),409)
        return {'comparison':comparison,'items':records,'differences_from_first':[r['value']-records[0]['value'] for r in records], 'interpretation':'差值=该项−首项；只做同口径描述性比较，不做显著性推断。'}
