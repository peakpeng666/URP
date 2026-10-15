"""Compare fixed-order Split with exhaustive partition enumeration."""
import importlib.util
import itertools
import json
import math
from pathlib import Path
import random
from decimal import Decimal
from validate import distance,check
source=Path(__file__).resolve().parents[1]/'src/research/src/urp_research/cvrplib/population_baselines.py'
spec=importlib.util.spec_from_file_location('candidate_population',source)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
rng=random.Random(822)
count=0
for n in range(1,9):
 for trial in range(30):
  coords=[(Decimal(rng.randrange(40)),Decimal(rng.randrange(40))) for _ in range(n+1)]
  demands=[0]+[rng.randrange(1,7) for _ in range(n)]
  cap=rng.randrange(6,16); order=list(range(1,n+1));rng.shuffle(order)
  d=[[distance(a,b) for b in coords] for a in coords]
  for K in range(1,n+1):
   expected=math.inf
   for mask in range(1<<(n-1)):
    cut=[0]+[i for i in range(1,n) if mask & (1<<(i-1))]+[n]
    if len(cut)-1>K:continue
    routes=[[0,*order[a:b],0] for a,b in zip(cut,cut[1:])]
    if any(sum(demands[j] for j in route)>cap for route in routes):continue
    cost=sum(d[a][b] for route in routes for a,b in zip(route,route[1:]))
    expected=min(expected,cost)
   actual,routes=mod.split(order,d,demands,cap,K)
   assert actual==expected,(n,trial,K,actual,expected)
   if math.isfinite(actual):
    assert check({'coordinates':coords,'demands':demands,'capacity':cap},routes,actual,K)['valid']
   count+=1
print(json.dumps({'fixed_order_cases':count,'brute_force_comparison_passed':True}))
