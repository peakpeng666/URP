"""One prospective source/request snapshot; hashes assets without executing them."""
import ast,hashlib,json,pathlib,sys,time
ROOT=pathlib.Path(__file__).resolve().parent
OLD=ROOT.parent/'math_dag_evolution_v1'
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main():
 start=time.monotonic();cpu=time.process_time()
 expected='036c265d2ba88647a66460ab816609c217d6170de7eb0348f37b73523d3bab39'
 if sha(OLD/'final_freeze.json')!=expected:raise ValueError('preceding immutable study')
 old=json.loads((OLD/'final_freeze.json').read_text());assets=dict(old['assets'])
 # Bind reused seed and worker/source identities, in addition to exact old dependency assets.
 for rel,want in old['files'].items():
  if sha(OLD/rel)!=want:raise ValueError('old frozen file changed')
  assets[str(OLD/rel)]=want
 assets[str(OLD/'final_freeze.json')]=expected
 transport=json.loads((ROOT/'transport_freeze.json').read_text())
 for rel,want in transport['files'].items():
  if sha(ROOT/rel)!=want:raise ValueError('prepared transport changed: '+rel)
 for path,want in assets.items():
  if sha(path)!=want:raise ValueError('dependency asset changed: '+path)
 for p in ROOT.rglob('*.py'):ast.parse(p.read_text())
 files={str(p.relative_to(ROOT)):sha(p) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='final_freeze.json' and p.relative_to(ROOT).parts[0] not in {'runs','.authorization_uses'}}
 importable=sorted(k for k in files if pathlib.Path(k).suffix in {'.py','.pyc','.so','.pyd'})
 d={'identity':'p3_compact_dag_interface_v2_frozen','scope':'Prospective3-request diagnostic, no execution authority granted by this file.','files':files,'assets':assets,'symlinks':old['symlinks'],'importable_files':importable,'python_executable':old['python_executable'],'python_executable_sha256':old['python_executable_sha256'],'math_evaluator_freeze':old['math_evaluator_freeze'],'model_requests_max':3,'score_requests_max':9,'ledger_rows':9,'source_study_freeze_sha256':expected,'snapshot_hash_cpu_seconds':time.process_time()-cpu,'snapshot_hash_wall_seconds':time.monotonic()-start}
 with (ROOT/'final_freeze.json').open('x') as f:json.dump(d,f,indent=2);f.write('\n')
 print(json.dumps({'sha256':sha(ROOT/'final_freeze.json'),'files':len(files),'assets':len(assets),'snapshot_hash_cpu_seconds':d['snapshot_hash_cpu_seconds'],'snapshot_hash_wall_seconds':d['snapshot_hash_wall_seconds']}))
if __name__=='__main__':main()
