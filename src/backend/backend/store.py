"""Small SQLite store for immutable imported research records. No experiment execution."""
from __future__ import annotations
import hashlib, json, math, os, re, sqlite3, stat
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

STATES = {'queued','running','completed','failed','partial','unknown'}
COMPARISON_KEYS = ('metric','unit','direction','cohort','protocol','budget','aggregation','reference')
ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')
SECRET_KEYS = {'api_key','apikey','password','access_token','refresh_token','secret_key','authorization','private_key'}
SECRET_BYTES = re.compile(rb'(?:-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\bAKIA[A-Z0-9]{16}\b|\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b|(?i:api[_-]?key|access[_-]?token|password|secret[_-]?key)["\x27]?\s*[:=]\s*["\x27]?[A-Za-z0-9_-]{20,})')
MAX_DESCRIPTOR_BYTES = 1024 * 1024
MAX_ARTIFACT_BYTES = 32 * 1024 * 1024
MAX_PACKAGE_BYTES = 128 * 1024 * 1024
MEDIA_TYPE = re.compile(r'^[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+(?:;[ -~]*)?$')

class StoreError(ValueError):
    def __init__(self, code, message, status=400):
        super().__init__(message); self.code=code; self.status=status

def now(): return datetime.now(timezone.utc).isoformat()
def canonical(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(data): return hashlib.sha256(data).hexdigest()
def identifier(value):
    if not isinstance(value,str) or not ID.fullmatch(value): raise StoreError('invalid_id','标识仅支持字母、数字、点、短横线和下划线。')
    return value

def revision_number(value):
    if value is not None and (type(value) is not int or not 1 <= value <= 2**63-1):
        raise StoreError('invalid_revision','版本必须为正整数。')
    return value

def parse_json(data, code='invalid_json'):
    """Reject ambiguous keys and nonstandard/nonfinite JSON at the boundary."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('nonfinite JSON constant')
    try:
        return json.loads(data, object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise StoreError(code, 'JSON字段重复、格式无效或嵌套过深。') from exc

def relative_parts(relative):
    if (not isinstance(relative,str) or '\\' in relative
            or any(ord(c) < 32 or ord(c) == 127 for c in relative)
            or any(part in {'.','..'} for part in relative.split('/'))
            or (len(relative) > 1 and relative[1] == ':')):
        raise StoreError('unsafe_path','文件必须使用安全的相对路径。')
    p=PurePosixPath(relative)
    if p.is_absolute() or not p.parts or any(part in {'..','.'} for part in p.parts): raise StoreError('unsafe_path','文件不能越过导入目录。')
    return p.parts

def safe_path(root: Path, relative: str):
    parts=relative_parts(relative)
    root=root.resolve(); current=root
    for part in parts:
        current=current/part
        if current.is_symlink(): raise StoreError('unsafe_path','导入不接受符号链接。')
    if not current.resolve().is_relative_to(root): raise StoreError('unsafe_path','文件不能越过导入目录。')
    return current

def no_secrets(value):
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        if depth > 64:
            raise StoreError('invalid_descriptor', 'JSON嵌套不能超过64层。')
        if isinstance(item, dict):
            for key, child in item.items():
                if str(key).lower() in SECRET_KEYS:
                    raise StoreError('secret_rejected','描述包含凭据字段，导入已停止。')
                pending.append((child, depth+1))
        elif isinstance(item, list):
            pending.extend((child, depth+1) for child in item)

def read_package_file(root, relative, limit, size_code='artifact_too_large'):
    """Read a bounded regular file without following a swapped symlink.

    On POSIX, every relative component is opened against the preceding directory
    descriptor; validation and reading cannot race a path replacement. Root is
    an explicitly selected directory and may itself be a configured symlink.
    """
    path = safe_path(Path(root), relative)
    if not hasattr(os, 'O_NOFOLLOW') or os.open not in os.supports_dir_fd:
        # The supported execution host is Linux; keep read-only Windows usage.
        if not path.is_file():
            raise StoreError('missing_artifact', f'缺少产物：{relative}', 404)
        with path.open('rb') as handle:
            data = handle.read(limit+1)
    else:
        descriptors = []
        try:
            directory = os.open(Path(root).resolve(), os.O_RDONLY | os.O_DIRECTORY)
            descriptors.append(directory)
            parts = PurePosixPath(relative).parts
            for part in parts[:-1]:
                directory = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                    dir_fd=directory)
                descriptors.append(directory)
            fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                         dir_fd=directory)
            descriptors.append(fd)
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise StoreError('unsafe_path', '导入仅接受普通文件。')
            if info.st_size > limit:
                raise StoreError(size_code, '导入文件超出大小限制。', 413)
            with os.fdopen(os.dup(fd), 'rb') as handle:
                data = handle.read(limit+1)
        except FileNotFoundError as exc:
            raise StoreError('missing_artifact', f'缺少产物：{relative}', 404) from exc
        except OSError as exc:
            raise StoreError('unsafe_path', '无法安全读取导入文件。') from exc
        finally:
            for fd in reversed(descriptors):
                os.close(fd)
    if len(data) > limit:
        raise StoreError(size_code, '导入文件超出大小限制。', 413)
    return data

def read_artifact(root, artifact):
    relative=artifact['path']; p=safe_path(root,relative)
    if p.name.startswith('.env') or p.suffix.lower() in {'.pem','.key'} or p.name.lower() in {'credentials','credentials.json','id_rsa','id_ed25519'}:
        raise StoreError('secret_rejected','凭据文件不能导入科研产物。')
    data=read_package_file(root,relative,MAX_ARTIFACT_BYTES)
    if SECRET_BYTES.search(data): raise StoreError('secret_rejected','产物疑似包含凭据，导入已停止；未保存文件。')
    if p.suffix.lower()=='.json':
        try:no_secrets(json.loads(data))
        except (UnicodeDecodeError,json.JSONDecodeError):pass
    return data

def validate(d):
    if not isinstance(d,dict): raise StoreError('invalid_descriptor','实验描述必须是JSON对象。')
    no_secrets(d)
    if type(d.get('schema_version')) is not int or d['schema_version']!=1: raise StoreError('schema_version','仅支持实验描述schema_version=1。')
    identifier(d.get('id'))
    for key in ('title','domain','kind'):
        if not isinstance(d.get(key),str) or not d[key].strip():raise StoreError('invalid_descriptor',f'缺少{key}。')
    if not isinstance(d.get('status'),str) or d['status'] not in STATES: raise StoreError('invalid_status','实验状态无效，缺失状态请明确填写unknown。')
    for key in ('counts','artifacts','metrics'):
        value = d.get(key, [])
        if not isinstance(value,list) or any(not isinstance(item,dict) for item in value):
            raise StoreError('invalid_descriptor', f'{key}必须是对象数组。')
    for c in d.get('counts',[]):
        value=c.get('value')
        if any(not isinstance(c.get(k),str) or not c[k].strip() for k in ('unit','scope')):raise StoreError('invalid_count','计数需要unit与scope。')
        if value is not None and (isinstance(value,bool) or not isinstance(value,int) or value<0):raise StoreError('invalid_count','计数必须为非负整数或null；未知不能填写0。')
    artifacts=d.get('artifacts',[]); ids=[identifier(a.get('id')) for a in artifacts]
    if len(artifacts) > 512:raise StoreError('too_many_artifacts','单包最多512个产物。',413)
    if len(ids)!=len(set(ids)):raise StoreError('duplicate_artifact','产物ID重复。')
    for a in artifacts:
        # Lexical validation here; actual root confinement is checked on read.
        relative_parts(a.get('path'))
        media = a.get('media_type','application/octet-stream')
        if not isinstance(media,str) or len(media)>256 or not MEDIA_TYPE.fullmatch(media):
            raise StoreError('invalid_media_type','产物媒体类型必须是合法ASCII MIME类型。')
    metric_ids=[]
    for m in d.get('metrics',[]):
        metric_ids.append(identifier(m.get('id')))
        v=m.get('value')
        try: finite = type(v) in (int,float) and math.isfinite(v)
        except OverflowError: finite = False
        if v is not None and not finite:raise StoreError('invalid_metric','指标值必须有限数值或null。')
        source=m.get('source',{})
        if (not isinstance(source,dict) or source.get('artifact_id') not in ids
                or not isinstance(source.get('locator'),str) or not source['locator'].strip()):raise StoreError('missing_metric_source','指标必须指向随包产物及其中字段。')
        comparison=m.get('comparison',{})
        if not isinstance(comparison,dict) or set(comparison)!=set(COMPARISON_KEYS):raise StoreError('invalid_comparison','比较口径需明确metric/unit/direction/cohort/protocol/budget/aggregation/reference。')
        if any(v is not None and not isinstance(v,str) for v in comparison.values()):raise StoreError('invalid_comparison','比较口径字段必须为字符串或未知null。')
        if comparison.get('direction') not in {'min','max',None}:raise StoreError('invalid_comparison','指标方向仅min/max或未知null。')
    if len(metric_ids)!=len(set(metric_ids)):raise StoreError('duplicate_metric','指标ID重复。')
    if 'routing' in d and (not isinstance(d['routing'],dict)
            or not isinstance(d.get('provenance'),dict)):
        raise StoreError('invalid_descriptor','routing与provenance必须是对象。')
    try:canonical(d) # also rejects non-JSON values and NaN in auxiliary fields
    except (TypeError,ValueError,OverflowError,RecursionError) as exc:
        raise StoreError('invalid_descriptor','实验描述包含无效JSON值。') from exc

class Store:
    def __init__(self, path):
        self.path=Path(path).resolve(); self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
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
        root=Path(package).resolve()
        try:d=parse_json(read_package_file(root,'experiment.json',MAX_DESCRIPTOR_BYTES,'descriptor_too_large'),'invalid_descriptor')
        except OSError as e:raise StoreError('invalid_descriptor','无法读取experiment.json。') from e
        validate(d)
        # Read all selected data before the transaction. A rejected file leaves no partial import.
        blobs=[];total_bytes=0
        for a in d.get('artifacts',[]):
            b=read_artifact(root,a);total_bytes+=len(b)
            if total_bytes>MAX_PACKAGE_BYTES:raise StoreError('package_too_large','单包产物总量上限128MiB。',413)
            blobs.append((a,b))
        fingerprint=sha(canonical({'descriptor':d,'artifacts':{a['id']:sha(b) for a,b in blobs}}).encode())
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous=db.execute('SELECT descriptor FROM experiments WHERE id=? ORDER BY revision DESC LIMIT 1',(d['id'],)).fetchone()
            if previous:
                old_descriptor=json.loads(previous['descriptor'])
                def route_identity(value):
                    routing=value.get('routing')
                    if not routing:return None
                    return (routing.get('source_format','vrptw-frozen-v1'),value.get('provenance',{}).get('input_sha256'))
                if route_identity(old_descriptor)!=route_identity(d):
                    raise StoreError('experiment_identity_mismatch','此实验ID已属于其他路线格式或输入集合。',409)
            old=db.execute('SELECT revision FROM experiments WHERE id=? AND fingerprint=?',(d['id'],fingerprint)).fetchone()
            if old:return {'id':d['id'],'revision':old['revision'],'fingerprint':fingerprint,'reused':True}
            rev=db.execute('SELECT COALESCE(MAX(revision),0)+1 FROM experiments WHERE id=?',(d['id'],)).fetchone()[0]
            db.execute('INSERT INTO experiments VALUES(?,?,?,?,?)',(d['id'],rev,fingerprint,now(),canonical(d)))
            for a,b in blobs:
                db.execute('INSERT INTO artifacts VALUES(?,?,?,?,?,?,?)',(d['id'],rev,a['id'],PurePosixPath(a['path']).name,a.get('media_type','application/octet-stream'),sha(b),b))
        return {'id':d['id'],'revision':rev,'fingerprint':fingerprint,'reused':False}
    def get(self,id,revision=None):
        identifier(id);revision_number(revision)
        with self.connect() as db:
            row=db.execute('SELECT * FROM experiments WHERE id=? AND (? IS NULL OR revision=?) ORDER BY revision DESC LIMIT 1',(id,revision,revision)).fetchone()
            if not row:raise StoreError('not_found','没有这个实验或版本。',404)
            d=json.loads(row['descriptor']); refs=db.execute('SELECT id,filename,media_type,sha256,length(content) AS bytes FROM artifacts WHERE experiment_id=? AND revision=?',(id,row['revision'])).fetchall()
        d['artifacts']=[dict(r) for r in refs]
        return {**d,'revision':row['revision'],'fingerprint':row['fingerprint'],'imported_at':row['imported_at']}
    def list(self):
        # One consistent SQLite snapshot avoids an N+1 query and revision races.
        with self.connect() as db:
            rows=db.execute('''SELECT e.* FROM experiments e JOIN
                (SELECT id,MAX(revision) AS revision FROM experiments GROUP BY id) latest
                ON e.id=latest.id AND e.revision=latest.revision ORDER BY e.id''').fetchall()
        return [{**{k:v for k,v in json.loads(row['descriptor']).items() if k not in {'metrics','artifacts'}},
                 'revision':row['revision'],'fingerprint':row['fingerprint'],'imported_at':row['imported_at']}
                for row in rows]
    def artifact(self,id,artifact_id,revision=None):
        identifier(artifact_id); record=self.get(id,revision)
        with self.connect() as db:
            row=db.execute('SELECT * FROM artifacts WHERE experiment_id=? AND revision=? AND id=?',(id,record['revision'],artifact_id)).fetchone()
        if not row:raise StoreError('not_found','没有这个产物。',404)
        data=bytes(row['content'])
        if sha(data)!=row['sha256']:raise StoreError('corrupt_artifact','数据库内产物哈希不一致，停止下载。',409)
        return {'filename':row['filename'],'media_type':row['media_type'],'sha256':row['sha256'],'bytes':len(data),'revision':record['revision']},data
    def compare(self,items):
        if not isinstance(items,list) or not 2<=len(items)<=128:raise StoreError('comparison_needs_items','请提供2到128个指标。')
        records=[]
        for item in items:
            if not isinstance(item,dict) or not {'experiment_id','metric_id'}<=set(item):raise StoreError('invalid_request','每项比较需要experiment_id与metric_id。')
            identifier(item['metric_id'])
            d=self.get(item['experiment_id'],item.get('revision'))
            if d['status']!='completed':raise StoreError('unfinished_experiment','运行中、失败或未知状态不作为完整结果比较。',409)
            m=next((m for m in d.get('metrics',[]) if m['id']==item['metric_id']),None)
            if not m:raise StoreError('not_found','指标未收录。',404)
            if m['value'] is None or any(not v for v in m['comparison'].values()):raise StoreError('unknown_metric','指标或比较口径未知，不能按0比较。',409)
            records.append({'experiment_id':d['id'],'revision':d['revision'],**m})
        comparison=records[0]['comparison'];different=sorted({k for r in records[1:] for k in COMPARISON_KEYS if r['comparison'][k]!=comparison[k]})
        if different:raise StoreError('incomparable_metrics','口径不可比：'+', '.join(different),409)
        return {'comparison':comparison,'items':records,'differences_from_first':[r['value']-records[0]['value'] for r in records], 'interpretation':'差值=该项−首项；只做同口径描述性比较，不做显著性推断。'}
