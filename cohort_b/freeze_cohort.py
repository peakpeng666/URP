from pathlib import Path
import json,hashlib,datetime
r=Path(__file__).resolve().parent
cases=json.loads((r.parent/'src/research/configs/cvrplib_cases.json').read_text())['cases'];selected=[c for c in cases if c['source_family']=='X' and c['contract']['vehicle_limit'] is None and c['contract']['id']=='standard-X-unlimited']
assert len(selected)==12
paths=[r/'run_vendor.py',r/'run_cohort.py',r/'PREDECLARATION.md',r/'sisr/cvrp/config.json',r/'sisr/build.sh',r/'ails/build.sh']+list((r/'sisr/adapted/src').glob('*'))+list((r/'ails/adapted/src').rglob('*.java'))+list((r/'sisr/adapted/lib').glob('*'))
obj={'schema':'urp-vendor-cohort-v1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'budget_seconds':5,'algorithms':['ails','sisr'],'seeds':list(range(5)),'case_ids':[c['case_id'] for c in selected],'schedule':[{'algorithm':a,'case_id':c['case_id'],'seed':s,'host_id':'cloud' if s==0 else 'local'} for s in range(5) for c in selected for a in ['ails','sisr']],'files':{str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()},'comparison':'Matched host allocation: seed0 cloud,1-4 local; separate temporal cohort, same12 unrestricted X only; no all53 ranking','technical_fix':'AILS varphi=min(40,n); unchanged for all X cases','reference_access':'none in worker; scoring after saved outputs'}
p=r/'COHORT_FREEZE.json'
if p.exists():raise SystemExit('freeze already exists')
p.write_text(json.dumps(obj,indent=2))
