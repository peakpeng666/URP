import hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
def digest(path):
 h=hashlib.sha256()
 with pathlib.Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def verify(path,expected):
 with pathlib.Path(path).open('rb') as f:raw=f.read(1500001)
 if len(raw)>1500000 or hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('freeze digest mismatch')
 d=json.loads(raw)
 for attr,key in [('executable','python_executable'),('prefix','python_prefix'),('base_prefix','python_base_prefix'),('exec_prefix','python_exec_prefix'),('base_exec_prefix','python_base_exec_prefix')]:
  if getattr(sys,attr)!=d[key]:raise ValueError('interpreter identity '+key)
 if digest(sys.executable)!=d['python_executable_sha256']:raise ValueError('interpreter hash')
 for root,expected_paths in d['runtime_roots'].items():
  r=pathlib.Path(root);actual=sorted(str(p.relative_to(r)) for p in r.rglob('*') if p.is_file())
  if actual!=expected_paths:raise ValueError('runtime inventory')
 for root,expected_paths in d.get('package_inventories',{}).items():
  r=pathlib.Path(root);actual=sorted(str(p.relative_to(r)) for p in r.rglob('*') if p.is_file() and p.suffix in {'.py','.pyc','.so','.pyd'})
  if actual!=expected_paths:raise ValueError('importable package inventory')
 for row in d['files']:
  p=ROOT/row['path']
  if p.stat().st_size!=row['bytes'] or digest(p)!=row['sha256']:raise ValueError('source mismatch '+row['path'])
 for path,row in {**d['runtime_files'],**d['references']}.items():
  p=pathlib.Path(path)
  if p.stat().st_size!=row['bytes'] or digest(p)!=row['sha256']:raise ValueError('reference/runtime mismatch '+path)
 return d
