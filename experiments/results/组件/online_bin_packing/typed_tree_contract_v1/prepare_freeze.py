"""Prospective snapshot only; no execution authority or model call."""
import ast,hashlib,json,pathlib,sys,time
sys.dont_write_bytecode=True
ROOT=pathlib.Path(__file__).resolve().parent
OLD=ROOT.parent/'math_dag_interface_v2_1'
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main():
 start=time.monotonic();cpu=time.process_time()
 old=json.loads((OLD/'final_freeze.json').read_text());assets=dict(old['assets'])
 for path,want in assets.items():
  if sha(path)!=want:raise ValueError('shared dependency changed: '+path)
 for rel in ['transport/backend.py','transport/tokenizer_runtime.py','src/guard.py','src/measurement.py','src/transport_check.py','run_diagnostic.py']:
  assets[str(OLD/rel)]=sha(OLD/rel)
 for p in ROOT.rglob('*.py'):ast.parse(p.read_text())
 files={str(p.relative_to(ROOT)):sha(p) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='final_freeze.json' and p.relative_to(ROOT).parts[0] not in {'runs','.authorization_uses'}}
 d={'identity':'typed_tree_contract_pilot4_frozen','scope':'Four slots, twelve micro-vector observations maximum; no execution authority.', 'files':files,'assets':assets,'symlinks':old['symlinks'],'importable_files':sorted(k for k in files if pathlib.Path(k).suffix in {'.py','.pyc','.so','.pyd'}),'python_executable':old['python_executable'],'python_executable_sha256':old['python_executable_sha256'],'math_evaluator_freeze':old['math_evaluator_freeze'],'model_requests_max':4,'score_requests_max':12,'ledger_rows':12,'source_study_freeze_sha256':sha(OLD/'final_freeze.json'),'snapshot_hash_cpu_seconds':time.process_time()-cpu,'snapshot_hash_wall_seconds':time.monotonic()-start}
 with (ROOT/'final_freeze.json').open('x') as f:json.dump(d,f,indent=2);f.write('\n')
 print(json.dumps({'freeze_sha256':sha(ROOT/'final_freeze.json'),'files':len(files),'assets':len(assets),'snapshot_cpu':d['snapshot_hash_cpu_seconds'],'snapshot_wall':d['snapshot_hash_wall_seconds']}))
if __name__=='__main__':main()
