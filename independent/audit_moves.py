"""Deterministic synthetic operator checks, not benchmark experiment results."""
import importlib.util
import json
from pathlib import Path
import random
from decimal import Decimal
from validate import distance, check
source=Path(__file__).resolve().parents[1]/'src/research/src/urp_research/cvrplib/restored_vnd.py'
spec=importlib.util.spec_from_file_location('candidate_vnd',source)
vnd=importlib.util.module_from_spec(spec);spec.loader.exec_module(vnd)
rng=random.Random(731)
count=0
for trial in range(80):
 n=8; coords=[(Decimal(rng.randrange(40)),Decimal(rng.randrange(40))) for _ in range(n+1)]
 demands=[0]+[rng.randrange(1,5) for _ in range(n)]
 matrix=[[distance(a,b) for b in coords] for a in coords]
 nodes=list(range(1,n+1));rng.shuffle(nodes); routes=[nodes[:3],nodes[3:6],nodes[6:]]
 problem={'coordinates':coords,'demands':demands,'capacity':14}
 def objective(rs):return sum(matrix[a][b] for r in rs for a,b in zip([0]+r,r+[0]))
 before=objective(routes)
 for kind in ('two_opt','relocate','swap','two_opt_star'):
  for delta,move in vnd.moves(routes,demands,14,matrix,kind):
   candidate=vnd.apply_move(routes,move);after=objective(candidate)
   assert after-before==delta,(trial,move,delta,after-before)
   result=check(problem,[[0,*r,0] for r in candidate],after,n)
   assert result['valid'],result
   count+=1
print(json.dumps({'synthetic_cases':80,'checked_moves':count,'delta_and_feasibility_passed':True}))
