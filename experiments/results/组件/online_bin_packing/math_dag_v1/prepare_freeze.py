"""Static-only freeze creation; no NumPy, formula or interpreter imports."""
import ast,base64,dataclasses,fractions,hashlib,importlib.metadata,io,json,math,os,pathlib,platform,re,resource,selectors,signal,subprocess,sys,sysconfig,time,traceback,unittest,warnings
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from integrity import row,sha,import_inventory

def main():
 dist=importlib.metadata.distribution('numpy')
 if dist.version!='2.3.5':raise ValueError('NumPy metadata version')
 base=pathlib.Path(dist.locate_file('')).resolve();runtime={};inventories={}
 for root in [base/'numpy',base/'numpy.libs',base/'numpy-2.3.5.dist-info']:
  files=sorted(p for p in root.rglob('*') if p.is_file());inventories[str(root)]=sorted(str(p.relative_to(root)) for p in files)
  for p in files:runtime[str(p)]=row(p)
 # Full standard-library tree except independently inventoried site-packages;
 # this covers lazy unittest/NumPy-testing imports without importing NumPy.
 stdlib=pathlib.Path(sysconfig.get_path('stdlib')).resolve()
 stdpaths=[]
 for child in sorted(stdlib.iterdir()):
  if child.name=='site-packages':continue
  if child.is_file():stdpaths.append(child)
  elif child.is_dir():stdpaths.extend(p for p in child.rglob('*') if p.is_file())
 for p in stdpaths:runtime[str(p)]=row(p)
 stdlib_inventory=sorted(str(p.relative_to(stdlib)) for p in stdpaths)
 for mod in list(sys.modules.values()):
  file=getattr(mod,'__file__',None)
  if file:
   p=pathlib.Path(file).resolve()
   if p.is_file() and not p.is_relative_to(ROOT):runtime[str(p)]=row(p)
 p=pathlib.Path(sysconfig.get_config_var('LIBDIR'))/sysconfig.get_config_var('LDLIBRARY')
 if p.is_file():runtime[str(p.resolve())]=row(p)
 files={}
 for p in sorted(ROOT.rglob('*')):
  rel=p.relative_to(ROOT)
  if not p.is_file() or rel.parts[0] in {'logs','results'} or '__pycache__' in rel.parts or p.name=='preparation_freeze.json':continue
  if p.suffix=='.py':ast.parse(p.read_text(),filename=str(p))
  if p.suffix=='.json':json.loads(p.read_bytes())
  files[str(rel)]=row(p)
 refs={}
 for p in [ROOT.parent/'published_eoh_formula_v1/src/formula.py',ROOT.parent/'published_eoh_formula_v1/static_preparation_freeze.json',ROOT.parent/'paper_baseline_v1/src/checker.py',ROOT.parent/'paper_baseline_v1/preparation_freeze.json']:
  refs[str(p.resolve())]=row(p)
 roots=[ROOT,ROOT.parent/'published_eoh_formula_v1',ROOT.parent/'paper_baseline_v1']
 if 'numpy' in sys.modules or 'interpreter' in sys.modules or 'formula' in sys.modules:raise RuntimeError('unexpected numerical import')
 freeze={'identity':'urp-math-dag-v1-handwritten-preparation','scope':'Fixed interpreter and handwritten tests only; no generated candidates/evolution','files':files,'runtime_files':runtime,'runtime_roots':inventories,'stdlib_root':str(stdlib),'stdlib_inventory':stdlib_inventory,'references':refs,'importable_roots':{str(r):import_inventory(r) for r in roots},'interpreter':{'executable':sys.executable,'resolved':str(pathlib.Path(sys.executable).resolve()),'prefix':sys.prefix,'base_prefix':sys.base_prefix,'exec_prefix':sys.exec_prefix,'base_exec_prefix':sys.base_exec_prefix},'interpreter_sha256':sha(sys.executable),'numpy_version':dist.version,'numpy_root':str(base/'numpy'),'platform':platform.platform(),'validation':{'ast_json_parse':'passed','numpy_imported':False,'formula_calls':0,'candidate_calls':0}}
 with (ROOT/'preparation_freeze.json').open('x') as f:json.dump(freeze,f,indent=2);f.write('\n')
 print(json.dumps({'sha256':sha(ROOT/'preparation_freeze.json'),'files':len(files),'runtime_files':len(runtime),'references':len(refs),'numpy_imported':False}))
if __name__=='__main__':main()
