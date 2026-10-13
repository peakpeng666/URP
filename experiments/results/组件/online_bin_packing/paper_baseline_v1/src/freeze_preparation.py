"""Bind the prepared data, trusted source, tests, provenance and runtime identity."""
import hashlib,importlib,json,pathlib,sys,sysconfig
from integrity import ROOT,digest

def main():
 for mod in ['run_batch','extract_data','extract_historical_data','unittest','pickletools']:
  importlib.import_module(mod)
 files=[]
 for dirname in ['src','tests','data','upstream','logs','results/preparation']:
  for p in sorted((ROOT/dirname).rglob('*')):
   if p.is_file() and '__pycache__' not in p.parts:
    if p.is_symlink():raise ValueError('unexpected source symlink')
    files.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)})
 for name in ['protocol.json','prepared_plan.json','README.md']:
  p=ROOT/name;files.append({'path':name,'bytes':p.stat().st_size,'sha256':digest(p)})
 deps={}
 for name,mod in list(sys.modules.items()):
  value=getattr(mod,'__file__',None)
  if value and pathlib.Path(value).is_file():
   p=pathlib.Path(value).resolve()
   if not p.is_relative_to(ROOT):deps[str(p)]={'bytes':p.stat().st_size,'sha256':digest(p)}
 lib=pathlib.Path(sysconfig.get_config_var('LIBDIR'))/sysconfig.get_config_var('LDLIBRARY')
 if lib.is_file():deps[str(lib.resolve())]={'bytes':lib.stat().st_size,'sha256':digest(lib)}
 freeze={'schema':'p3_eoh_ff_bf_preparation_v1','scope':'Preparation and handwritten tests reviewed separately from an external one-use60slot authorization','files':sorted(files,key=lambda x:x['path']),'dependencies':deps,'python_executable':sys.executable,'python_executable_sha256':digest(sys.executable),'runtime_note':'Standard-library-only handwritten implementation. Dependency file hashes supplement interpreter identity, not full OS/toolchain hermeticity.'}
 p=ROOT/'preparation_freeze.json'
 with p.open('x') as f:json.dump(freeze,f,indent=2);f.write('\n')
 print(json.dumps({'path':str(p),'sha256':digest(p),'file_count':len(files),'dependency_count':len(deps)},indent=2))
if __name__=='__main__':main()
