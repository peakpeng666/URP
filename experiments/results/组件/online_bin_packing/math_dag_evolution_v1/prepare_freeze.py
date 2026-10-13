"""Hash/AST preparation only. Never loads weights or executes a study candidate."""
import argparse,ast,hashlib,json,pathlib,sys,time
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from guard import sha

def main():
 a=argparse.ArgumentParser();a.add_argument('--stage',choices=['prevalidation','final'],required=True);args=a.parse_args();start=time.monotonic();cpu=time.process_time()
 output=ROOT/('prevalidation_snapshot.json' if args.stage=='prevalidation' else 'final_freeze.json')
 if output.exists():raise FileExistsError('snapshot already exists; preserve rather than overwrite')
 files={}
 for p in sorted(ROOT.rglob('*')):
  rel=p.relative_to(ROOT)
  if not p.is_file() or rel.parts[0] in {'runs','.authorization_uses'} or '__pycache__' in rel.parts or p.name in {'final_freeze.json','prevalidation_snapshot.json'}:continue
  if args.stage=='prevalidation' and (rel.parts[0]=='logs' or str(rel)=='preparation_costs.json'):continue
  if p.suffix=='.py':ast.parse(p.read_text(),filename=str(p))
  if p.suffix=='.json':json.loads(p.read_bytes())
  files[str(rel)]=sha(p)
 assets={};symlinks={}
 f=ROOT/'interface_smoke_v2/freeze.json';old=json.loads(f.read_bytes())
 if sha(f)!='635487393091b3734e714e4305aadd01ca0acdd76ec2774b34185961550c5ba3':raise ValueError('accepted smoke identity')
 for rel,want in old['asset_sha256'].items():
  p=(f.parent/rel).absolute()
  if sha(p)!=want:raise ValueError('shared asset mismatch')
  assets[str(p)]=want
  if p.is_symlink():symlinks[str(p)]=str(p.readlink())
 math=ROOT.parent/'math_dag_v1';mf=math/'preparation_freeze.json'
 if sha(mf)!='6d451c5febf0930a4f044bf0cfae9968c72846bbb3f211767a8772e326b45c12':raise ValueError('math evaluator identity')
 md=json.loads(mf.read_bytes());assets[str(mf)]=sha(mf)
 for rel,row in md['files'].items():assets[str(math/rel)]=row['sha256']
 for path,row in {**md['runtime_files'],**md['references']}.items():assets[path]=row['sha256']
 for path,want in assets.items():
  if sha(path)!=want:raise ValueError('dependency changed')
 importable=sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and p.suffix in {'.py','.pyc','.so','.pyd'} and p.relative_to(ROOT).parts[0] not in {'runs','.authorization_uses'})
 if args.stage=='final':
  pre=ROOT/'prevalidation_snapshot.json';pd=json.loads(pre.read_bytes())
  for rel,want in pd['files'].items():
   if sha(ROOT/rel)!=want:raise ValueError('source changed since reviewed tests: '+rel)
  files['prevalidation_snapshot.json']=sha(pre)
 d={'identity':'p3-math-dag-two-generation-22-'+args.stage,'scope':'Matching explicit one-batch approval required; source freeze itself does not authorize model/score calls','files':files,'assets':assets,'symlinks':symlinks,'importable_files':importable,'python_executable':sys.executable,'python_executable_sha256':sha(sys.executable),'math_evaluator_freeze':sha(mf),'schema_sha256':sha(ROOT/'generation_schema_v2.json'),'protocol_sha256':sha(ROOT/'protocol.json'),'case_panel_sha256':sha(ROOT/'data/panel.json'),'model_requests_max':22,'score_requests_max':120,'ledger_rows':208,'preparation_known_costs':json.loads((ROOT/'preparation_costs.json').read_bytes()),'snapshot_hash_cpu_seconds':time.process_time()-cpu,'snapshot_hash_wall_seconds':time.monotonic()-start}
 with output.open('x') as fp:json.dump(d,fp,indent=2,allow_nan=False);fp.write('\n')
 print(json.dumps({'path':str(output),'sha256':sha(output),'files':len(files),'assets':len(assets),'model_calls':0,'score_calls':0,'hash_cpu_seconds':d['snapshot_hash_cpu_seconds'],'hash_wall_seconds':d['snapshot_hash_wall_seconds']}))
if __name__=='__main__':main()
