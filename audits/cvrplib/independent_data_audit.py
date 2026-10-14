"""Standalone stdlib independent audit; does not import runner, solver, or its checker."""
from pathlib import Path
from fractions import Fraction as F
from collections import Counter,defaultdict
from math import isqrt
import hashlib,json,re,shutil,argparse,statistics

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def parse(p):
 h={};coords={};demands={};depots=[];section=None
 for raw in p.read_text().splitlines():
  s=raw.strip()
  if not s or s=='EOF':continue
  if s in ('NODE_COORD_SECTION','DEMAND_SECTION','DEPOT_SECTION'):section=s;continue
  if section is None:
   k,v=s.split(':',1);h[k.strip()]=v.strip()
  elif section=='NODE_COORD_SECTION':
   a,x,y=s.split();a=int(a);assert a not in coords;coords[a]=(F(x),F(y))
  elif section=='DEMAND_SECTION':
   a,d=s.split();a=int(a);assert a not in demands;demands[a]=int(d)
  elif section=='DEPOT_SECTION':
   for a in s.split():
    if int(a)!=-1:depots.append(int(a))
 assert h['TYPE']=='CVRP' and h['EDGE_WEIGHT_TYPE']=='EUC_2D'
 assert len(coords)==int(h['DIMENSION']) and set(coords)==set(demands)
 assert len(depots)==1 and depots[0] in coords and demands[depots[0]]==0
 assert all(d>=0 for d in demands.values()) and int(h['CAPACITY'])>0
 return h,coords,demands,depots[0]
def edge(a,b):
 # Exact rational nearest-integer Euclidean edge length. No binary floats/banker's round.
 q=sum((x-y)**2 for x,y in zip(a,b));n=isqrt(q.numerator//q.denominator)
 return n+int(4*q.numerator >= q.denominator*(2*n+1)**2)
def audit(root,freeze):
 base=root/'data/benchmarks/CVRPLIB';manifest=json.loads((base/'SOURCE_MANIFEST.json').read_text());frozen={x['instance_id']:x['K'] for x in json.loads(freeze.read_text())}
 hashes=[]
 for f in manifest['files']:
  p=root/f['path'];assert sha(p)==f['sha256'] and p.stat().st_size==f['bytes'];hashes.append({'path':f['path'],'sha256':sha(p),'bytes':p.stat().st_size,'matches':True})
 additional=json.loads((base/'reference_solutions/ADDITIONAL_SIX_SOURCE.json').read_text())
 for f in additional['files']:
  p=base/'reference_solutions'/f['file'];assert sha(p)==f['sha256'] and p.stat().st_size==f['size']
 cases=[];groups=defaultdict(list)
 for p in sorted((base/'instances').glob('*.vrp')):
  h,c,d,depot=parse(p);name=p.stem;ref=base/'reference_solutions'/f'{name}.sol';assert ref.exists()
  # CVRPLIB SOL IDs use zero-based original node ID, not positional renumbering.
  assert depot==1 and set(c)==set(range(1,len(c)+1))
  routes=[];claimed=None
  for s in ref.read_text().splitlines():
   if s.startswith('Route'):routes.append([int(v)+1 for v in s.split(':',1)[1].split()])
   elif s.lower().startswith('cost'):claimed=F(s.split()[1])
   elif s.strip():raise ValueError(f'Unrecognized SOL line: {s}')
  seen=Counter(a for r in routes for a in r);expected=set(c)-{depot}
  errors=[]
  if set(seen)!=expected or any(v!=1 for v in seen.values()):errors.append('coverage')
  if any(not r for r in routes):errors.append('empty_route')
  loads=[sum(d.get(a,0) for a in r) for r in routes]
  if any(l>int(h['CAPACITY']) for l in loads):errors.append('capacity')
  cost=sum(edge(c[a],c[b]) for r in routes for a,b in zip([depot]+r,r+[depot])) if set(seen)<=set(c) else None
  if cost!=claimed:errors.append('cost')
  named_k=int(name.rsplit('-k',1)[1]);lower_bound=(sum(d.values())+int(h['CAPACITY'])-1)//int(h['CAPACITY'])
  if not name.startswith('X-'):assert lower_bound==named_k and len(routes)==named_k
  limit=None if name.startswith('X-') else frozen.get(name,named_k);contract='historical_small16_at_most_Kref' if name in frozen else ('standard_X_unlimited_zero_fixed_cost' if name.startswith('X-') else 'ABEFP_rounded_fixed_K_equivalent_at_most_K_by_demand_lower_bound')
  if limit and len(routes)>limit:errors.append('fleet')
  # Base identity intentionally excludes capacity/fleet/name; captures coordinates, demand and depot role, ignores node labels/order.
  norm={'depot':[str(v) for v in c[depot]]+[d[depot]],'customers':sorted([[str(v) for v in c[a]]+[d[a]] for a in expected])}
  fp=hashlib.sha256(json.dumps(norm,sort_keys=True,separators=(',',':')).encode()).hexdigest();groups[fp].append(name)
  cases.append(dict(case_id=name,dimension=len(c),customers=len(c)-1,depot_id=depot,node_ids=sorted(c),capacity=int(h['CAPACITY']),total_demand=sum(d.values()),instance_sha256=sha(p),reference_sha256=sha(ref),reference_routes=len(routes),reference_cost=int(claimed),recomputed_cost=cost,route_loads=loads,base_fingerprint=fp,base_reference_valid=not errors,errors=errors,fleet_contract=contract,vehicle_limit=limit,demand_capacity_route_lower_bound=lower_bound,contract_source='https://optimization-online.org/wp-content/uploads/2014/10/4597.pdf pp.2-4 (nonX); section3.3.2 pp.15-16 (X)',contract_validated=(not errors) and (limit is not None or name.startswith('X-')),gap_status='validated_reference_under_declared_contract_not_independent_optimality_proof' if not errors and (limit is not None or name.startswith('X-')) else 'ineligible',empirical_descriptors=dict(coordinate_bounds={'x_min':float(min(x[0] for x in c.values())),'x_max':float(max(x[0] for x in c.values())),'y_min':float(min(x[1] for x in c.values())),'y_max':float(max(x[1] for x in c.values()))},customer_demand_min=min(d[a] for a in expected),customer_demand_max=max(d[a] for a in expected),customer_demand_mean=statistics.mean(d[a] for a in expected),customer_demand_population_stddev=statistics.pstdev(d[a] for a in expected),distinct_customer_locations=len({c[a] for a in expected})),reference_optimality_status='not_independently_proven; historical source labels retained separately',comment=h.get('COMMENT')))
 return dict(schema='independent_cvrplib_source_audit_v1',pinned_commit='f110f039854f7314e36632ce7d3ee977cd0de0fc',historical_manifest_sha256=sha(base/'SOURCE_MANIFEST.json'),original_files=hashes,cases=cases,summary=dict(cases=len(cases),customers_min=min(x['customers'] for x in cases),customers_max=max(x['customers'] for x in cases),unique_coordinate_demand_bases=len(groups),duplicate_base_groups=[v for v in groups.values() if len(v)>1],reference_base_valid=sum(x['base_reference_valid'] for x in cases),contract_validated=sum(x['contract_validated'] for x in cases),historical_small16=list(frozen)))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);ap.add_argument('--freeze',type=Path,default=Path(__file__).with_name('historical_small16_TASKS.json'));ap.add_argument('--output',type=Path,default=Path(__file__).with_name('independent_data_audit.json'));a=ap.parse_args();report=audit(a.root,a.freeze);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['summary'],indent=2));assert len(report['original_files'])==100 and report['summary']['reference_base_valid']==53
