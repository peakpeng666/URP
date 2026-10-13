"""Trusted-workspace integrity checks; not a filesystem/capability sandbox."""
import hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
def sha(path):
 h=hashlib.sha256()
 with pathlib.Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
def row(path):return {'bytes':pathlib.Path(path).stat().st_size,'sha256':sha(path)}
def import_inventory(root):
 return sorted(str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and p.suffix in {'.py','.pyc','.so','.pyd'})
def verify(expected):
 with (ROOT/'preparation_freeze.json').open('rb') as f:raw=f.read(2000001)
 if len(raw)>2000000 or hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('preparation digest')
 d=json.loads(raw)
 identity={'executable':sys.executable,'resolved':str(pathlib.Path(sys.executable).resolve()),'prefix':sys.prefix,'base_prefix':sys.base_prefix,'exec_prefix':sys.exec_prefix,'base_exec_prefix':sys.base_exec_prefix}
 if identity!=d['interpreter']:raise ValueError('actual interpreter path/prefix')
 if sha(sys.executable)!=d['interpreter_sha256']:raise ValueError('actual interpreter bytes')
 for rel,want in d['files'].items():
  if row(ROOT/rel)!=want:raise ValueError('source mismatch: '+rel)
 for path,want in {**d['runtime_files'],**d['references']}.items():
  if row(path)!=want:raise ValueError('dependency mismatch: '+path)
 for path,want in d['runtime_roots'].items():
  root=pathlib.Path(path);actual=sorted(str(p.relative_to(root)) for p in root.rglob('*') if p.is_file())
  if actual!=want:raise ValueError('runtime inventory: '+path)
 stdlib=pathlib.Path(d['stdlib_root']);paths=[]
 for child in sorted(stdlib.iterdir()):
  if child.name=='site-packages':continue
  if child.is_file():paths.append(child)
  elif child.is_dir():paths.extend(p for p in child.rglob('*') if p.is_file())
 if sorted(str(p.relative_to(stdlib)) for p in paths)!=d['stdlib_inventory']:raise ValueError('stdlib inventory')
 for path,want in d['importable_roots'].items():
  if import_inventory(pathlib.Path(path))!=want:raise ValueError('importable inventory: '+path)
 return d
