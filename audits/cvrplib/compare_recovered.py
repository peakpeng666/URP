"""Compare recovered immutable code/manifest against independently fetched source audit."""
import argparse,sys,json,hashlib,importlib.util
from pathlib import Path
from independent_data_audit import parse,edge,sha
ap=argparse.ArgumentParser();ap.add_argument('--recovered',type=Path,required=True);ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);a=ap.parse_args();sys.dont_write_bytecode=True
sys.path.insert(0,str(a.recovered/'files/src/research/src'))
from urp_research.cvrplib import io,audit
ind=json.loads((a.root/'audits/cvrplib/independent_data_audit.json').read_text());rec=json.loads((a.recovered/'files/src/research/configs/cvrplib_cases.json').read_text());lookup={c['case_id']:c for c in ind['cases']};errors=[];checks=[]
assert set(lookup)=={c['case_id'] for c in rec['cases']}
for c in rec['cases']:
 n=c['case_id'];i=lookup[n];diff=[]
 for key,own in [('dimension','dimension'),('n_customers','customers'),('capacity','capacity'),('instance_sha256','instance_sha256'),('demand_lower_bound_routes','demand_capacity_route_lower_bound')]:
  if c[key]!=i[own]:diff.append(key)
 for key,own in [('sha256','reference_sha256'),('cost','recomputed_cost'),('routes','reference_routes')]:
  if c['reference'][key]!=i[own]:diff.append('reference.'+key)
 if c['contract']['vehicle_limit']!=i['vehicle_limit']:diff.append('vehicle_limit')
 p=a.root/c['instance_path'];h,coords,demands,depot=parse(p);parsed=io.parse_vrp(p.read_text());ids=[depot]+sorted(set(coords)-{depot})
 if parsed['original_node_ids']!=ids or parsed['demands']!=[demands[x] for x in ids] or parsed['coordinates']!=[[float(v) for v in coords[x]] for x in ids]:diff.append('parser')
 matrix=io.matrix(parsed['coordinates']);cells=0
 for row,x in enumerate(ids):
  for col,y in enumerate(ids):
   if matrix[row][col]!=edge(coords[x],coords[y]):diff.append(f'matrix[{row},{col}]')
   cells+=1
 ref=a.root/c['reference']['path'];routes,cost=io.parse_sol(ref.read_text());problem=audit.independent_input.parse_vrp(p.read_text(),i['vehicle_limit'] or i['customers']);v=audit.validator.validate_solution(problem,routes,cost)
 if not v['valid'] or v['cost']!=i['recomputed_cost'] or v['loads']!=i['route_loads']:diff.append('recovered_checker')
 checks.append({'case_id':n,'mismatches':diff,'directed_matrix_cells':cells,'recovered_checker_valid':v['valid']});errors.extend(n+': '+d for d in diff)
if sorted(map(sorted,rec['duplicate_groups']))!=sorted(map(sorted,ind['summary']['duplicate_base_groups'])):errors.append('duplicate_groups')
oldsmall=sorted(x['case_id'] for x in rec['cases'] if x['historical_small16'])
if oldsmall!=sorted(ind['summary']['historical_small16']):errors.append('small16')
extras=[]
for p in (a.recovered/'files/data/benchmarks/CVRPLIB/reference_solutions').glob('*.sol'):
 match=sha(p)==sha(a.root/'data/benchmarks/CVRPLIB/reference_solutions'/p.name);extras.append({'file':p.name,'sha256':sha(p),'match':match})
 if not match:errors.append('additional_reference:'+p.name)
report={'case_count':len(checks),'mismatches':errors,'directed_matrix_cells':sum(c['directed_matrix_cells'] for c in checks),'checks':checks,'additional_reference_checks':extras,'fingerprint_note':'Recovered includes D4/translation/uniform-scaling invariance; independent audit uses exact coordinate-demand bases. Hash strings intentionally differ but full dataset duplicate partition matches. Scaling-equivalence is a leakage-screen heuristic, not identical rounded objective claim.'}
(a.root/'audits/cvrplib/recovered_comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('checks','additional_reference_checks')},indent=2));assert not errors
