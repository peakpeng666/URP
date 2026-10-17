#!/usr/bin/env python3
"""Execute an explicitly frozen CVRPLIB plan serially; never promote smoke runs."""
import argparse,datetime,hashlib,importlib.metadata,json,os,platform,sys,time
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src/research/src'))
from urp_research.cvrplib.io import parse_vrp,contract_for,sha,digest
from urp_research.cvrplib.cli import reserve_run_key
from urp_research.cvrplib.runner import run_payload
from urp_research.cvrplib.evaluate import evaluate_saved
A=argparse.ArgumentParser();A.add_argument('--plan',type=Path,required=True);A.add_argument('--output',type=Path,required=True);A.add_argument('--resume',action='store_true');A.add_argument('--seeds',required=True);A.add_argument('--machine-id',required=True);A.add_argument('--assignment',required=True,type=Path);args=A.parse_args()
assignment=json.loads(args.assignment.read_text());owned_seeds=[int(x) for x in args.seeds.split(',')];assert assignment['machines'][args.machine_id]['seeds']==owned_seeds;assert assignment['canonical_plan_sha256']==sha(args.plan)
plan=json.loads(args.plan.read_text());assert plan['schema']=='urp-cvrplib-formal-plan-v1';assert plan['purpose']=='teacher_baseline';assert plan['frozen'] is True
M=R/'src/research/configs/cvrplib_cases.json';cases={c['case_id']:c for c in json.loads(M.read_text())['cases']}
assert plan['case_manifest_sha256']==sha(M)
source=R/'src/research/src/urp_research/cvrplib'
def source_hash():return digest({str(p.relative_to(source)):sha(p) for p in sorted(source.rglob('*.py'))})
assert plan['solver_source_sha256']==source_hash()
protocol=R/plan['protocol_path'];assert sha(protocol)==plan['protocol_sha256']
O=args.output;O.mkdir(parents=True,exist_ok=args.resume)
if args.resume:
 assert json.loads((O/'plan.json').read_text())==plan,'resume plan changed'
def save(path,obj):
 if args.resume and path.exists():return
 with path.open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
save(O/'plan.json',plan);save(O/'environment.json',{'python':sys.version,'platform':platform.platform(),'executable':sys.executable,'affinity':sorted(os.sched_getaffinity(0)),'packages':{x.metadata['Name']:x.version for x in importlib.metadata.distributions()},'cpuinfo':Path('/proc/cpuinfo').read_text(),'plan_sha256':sha(args.plan)})
# Preflight all inputs before any formal solve. Reference data stays out of worker payload.
for name in plan['case_ids']:
 c=cases[name];assert sha(R/c['instance_path'])==c['instance_sha256'];assert sha(R/c['reference']['path'])==c['reference']['sha256']
schedule=plan.get('schedule') or [{'case_id':name,'algorithm':alg,'seed':seed,'budget_seconds':plan['budget_seconds']} for name in plan['case_ids'] for seed in plan['seeds'] for alg in plan['algorithms']]
save(O/'schedule.json',schedule)
save(O/('assignment-'+args.machine_id+'.json'),assignment)
selected=sum(item['seed'] in owned_seeds for item in schedule)
for idx,item in enumerate(schedule):
 if (O/'STOP_AFTER_CURRENT').exists():
  save(O/('paused-'+args.machine_id+'-'+str(idx)+'.json'),{'reason':'stop file','next_index':idx,'machine_id':args.machine_id});sys.exit(0)
 if json.loads(args.assignment.read_text())!=assignment:
  save(O/('paused-ownership-'+args.machine_id+'-'+str(idx)+'.json'),{'reason':'ownership assignment changed','next_index':idx,'machine_id':args.machine_id});sys.exit(0)
 if item['seed'] not in owned_seeds:continue
 assert source_hash()==plan['solver_source_sha256'],'sources changed during formal run'
 c=cases[item['case_id']];p=parse_vrp((R/c['instance_path']).read_text());contract=contract_for(c,p)
 payload={k:p[k] for k in ('coordinates','demands','capacity')};payload.update(K=contract['K'],algorithm=item['algorithm'],seed=item['seed'],budget_seconds=item['budget_seconds'])
 out=O/f'{idx:05d}-{c["case_id"]}-{item["algorithm"]}-s{item["seed"]}';
 if args.resume and (out/'result.json').exists():
  prior=json.loads((out/'result.json').read_text());assert prior['plan_sha256']==sha(args.plan)
  if not (out/'evaluation.json').exists():save(out/'evaluation.json',evaluate_saved(R,M,out/'result.json'))
  continue
 if out.exists():raise RuntimeError('interrupted attempt without result; preserve and adjudicate before resume: '+str(out))
 out.mkdir()
 key=reserve_run_key(O/'run-registry',{'plan_sha256':sha(args.plan),'instance_sha256':c['instance_sha256'],'algorithm':item['algorithm'],'seed':item['seed'],'budget_seconds':item['budget_seconds'],'contract':contract,'solver_source_sha256':plan['solver_source_sha256']},out)
 result=run_payload(payload);result.update(purpose='formal_baseline',run_key=key,case_id=c['case_id'],contract=contract,instance_sha256=c['instance_sha256'],case_manifest_sha256=sha(M),protocol_sha256=plan['protocol_sha256'],plan_sha256=sha(args.plan),solver_source_sha256=plan['solver_source_sha256'],cohort=plan['cohort'],machine_id=args.machine_id,assignment_sha256=sha(args.assignment),execution_driver_sha256=sha(Path(__file__)))
 save(out/'result.json',result)
 evaluation=evaluate_saved(R,M,out/'result.json');save(out/'evaluation.json',evaluation)
 print(json.dumps({'index':idx+1,'planned':len(schedule),**item,'status':result['status'],'feasible':result['feasible'],'cost':result['cost'],'gap_percent':evaluation['gap_percent']}),flush=True)
save(O/('completed-'+args.machine_id+'.json'),{'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'planned':selected,'attempted':selected,'canonical_planned':len(schedule),'purpose':'formal_baseline','plan_sha256':sha(args.plan)})
