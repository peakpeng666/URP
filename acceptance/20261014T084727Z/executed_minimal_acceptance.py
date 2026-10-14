from pathlib import Path
import sys,json,datetime,itertools,platform,importlib.metadata,subprocess
ROOT=Path('/workspace/shared/urp_readiness'); OUT=ROOT/'deliver/acceptance/20261014T084727Z'
sys.path.insert(0,str(ROOT/'deliver/src/research/src'))
from urp_research.cvrplib.runner import run_payload,summarize
from urp_research.cvrplib.audit import validator
from urp_research.cvrplib.io import sha
fixture={'coordinates':[[0,0],[3,1],[0,3],[5,1],[2,5],[6,6]],'demands':[0,1,1,1,1,1],'capacity':3,'K':2}
opt=min(c['cost'] for perm in itertools.permutations(range(1,6)) for cut in range(1,5) if (c:=validator.validate_solution(fixture,[[0,*perm[:cut],0],[0,*perm[cut:],0]]))['valid'])
rows=[]
for budget in (1,5):
 for algorithm in ('savings','T','TRS','TSR','pyvrp'):
  r=run_payload({**fixture,'algorithm':algorithm,'seed':0,'budget_seconds':budget})
  (OUT/f'fixture-{algorithm}-{budget}.json').write_text(json.dumps(r,indent=2))
  rows.append(r); assert r['feasible'] and r['cost']>=opt,r
  print('fixture',algorithm,budget,r['status'],r['cost'],flush=True)
commands=[]
for case,algorithm,budget in [('P-n19-k2',a,1) for a in ('savings','T','TRS','TSR')]+[('A-n32-k5','pyvrp',1),('X-n101-k25','pyvrp',5)]:
 dest=OUT/f'smoke-{case}-{algorithm}'
 base=[sys.executable,str(ROOT/'deliver/src/research/scripts/cvrplib.py')]
 cmd=base+['run-one','--instance',str(ROOT/f'deliver/data/benchmarks/CVRPLIB/instances/{case}.vrp'),'--algorithm',algorithm,'--seed','0','--budget',str(budget),'--output',str(dest),'--run-registry',str(OUT/'registry')]
 result=subprocess.run(cmd,text=True,capture_output=True);commands.append({'argv':cmd,'exitcode':result.returncode,'stdout':result.stdout,'stderr':result.stderr});print(result.stdout,flush=True);assert result.returncode==0,result
 cmd=base+['score','--repo',str(ROOT/'deliver'),'--result',str(dest/'result.json'),'--output',str(dest/'evaluation.json')]
 result=subprocess.run(cmd,text=True,capture_output=True);commands.append({'argv':cmd,'exitcode':result.returncode,'stdout':result.stdout,'stderr':result.stderr});assert result.returncode==0,result
(OUT/'minimal-smoke-commands.json').write_text(json.dumps(commands,indent=2))
(OUT/'minimal-acceptance-summary.json').write_text(json.dumps({'run_id':OUT.name,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'fixture_oracle':opt,'fixture_calls':10,'fixture_summary':summarize(rows,10),'official_calls':7,'official_cases':['P-n19-k2','A-n32-k5','X-n101-k25'],'formal_batch_calls':0,'paid_calls':0,'python':sys.version,'platform':platform.platform(),'dependencies':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()},'source_hashes':{str(p.relative_to(ROOT/'deliver')):sha(p) for p in sorted((ROOT/'deliver/src/research/src/urp_research/cvrplib').rglob('*.py'))}},indent=2))
