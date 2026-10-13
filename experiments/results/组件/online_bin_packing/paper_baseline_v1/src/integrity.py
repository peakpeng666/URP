import hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
def digest(path):
 h=hashlib.sha256()
 with pathlib.Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def verify(path,expected):
 with pathlib.Path(path).open('rb') as f:raw=f.read(1000001)
 if len(raw)>1000000 or hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('freeze digest mismatch')
 d=json.loads(raw)
 for row in d['files']:
  p=ROOT/row['path']
  if p.is_symlink() or p.stat().st_size!=row['bytes'] or digest(p)!=row['sha256']:raise ValueError('frozen file mismatch: '+row['path'])
 for path,row in d.get('dependencies',{}).items():
  p=pathlib.Path(path)
  if p.stat().st_size!=row['bytes'] or digest(p)!=row['sha256']:raise ValueError('runtime dependency mismatch: '+path)
 if digest(sys.executable)!=d['python_executable_sha256']:raise ValueError('interpreter mismatch')
 return d
