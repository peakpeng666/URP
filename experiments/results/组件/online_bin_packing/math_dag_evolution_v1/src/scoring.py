"""Thin trusted bridge to the unchanged, frozen mathematical-DAG worker."""
import hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];MATH=ROOT.parent/'math_dag_v1'
sys.path.insert(0,str(MATH/'src'))
from schema import validate_program
from runtime import request
sys.path.insert(0,str(ROOT.parent/'paper_baseline_v1/src'))
from checker import check_assignment

def check_observation(raw,case,obs):
 p=validate_program(raw)
 if obs.get('returncode')!=0 or obs.get('termination') is not None or obs.get('error') is not None or obs.get('reaped') is not True or obs.get('cpu_evidence_complete') is not True:raise ValueError('evaluator transport/infrastructure failure')
 body=obs.get('result')
 if type(body) is not dict or body.get('program_sha256')!=p.raw_sha256 or body.get('canonical_program_sha256')!=p.canonical_sha256 or body.get('phase')!='pack':raise ValueError('evaluator source/phase binding')
 status=body.get('status');w=body.get('warnings')
 if type(w) is not dict or type(w.get('events')) is not list or type(w.get('kinds')) is not list or len(w['events'])>12000 or len(w['kinds'])>32 or type(w.get('complete')) is not bool:raise ValueError('warning envelope')
 for event in w['events']:
  if type(event) is not list or len(event)!=3 or any(type(x) is not int for x in event) or not 0<=event[0]<len(case['items']) or not 0<=event[1]<len(p.nodes) or not 0<=event[2]<len(w['kinds']):raise ValueError('warning event binding')
 for kind in w['kinds']:
  if type(kind) is not dict or set(kind)!={'category','module','file','line','message'} or kind['category']!='RuntimeWarning' or kind['file']!='interpreter.py' or type(kind['line']) is not int or type(kind['message']) is not str or len(kind['message'].encode())>1024:raise ValueError('warning kind binding')
 if status in {'numeric_invalid','resource_unresolved','diagnostic_unresolved'}:
  if body.get('result') is not None or type(body.get('error')) is not dict:raise ValueError('failed evaluator envelope')
  return {'case_id':case['id'],'status':status,'error':body['error'],'complete_semantic_measurement':False}
 if status!='packing_returned' or body.get('error') is not None or w['complete'] is not True:raise ValueError('unexpected evaluator status')
 r=body.get('result')
 if type(r) is not dict:raise ValueError('packing response shape')
 checked=check_assignment(case['items'],case['capacity'],r['assignment'],r['used_bins'],r['residuals'])
 if r.get('placements')!=len(case['items']) or type(r.get('feasible_counts')) is not list or len(r['feasible_counts'])!=len(case['items']):raise ValueError('packing count shape')
 residual=[case['capacity']]*len(case['items'])
 for item,bid,count in zip(case['items'],r['assignment'],r['feasible_counts']):
  if type(count) is not int or count!=sum(x>=item for x in residual):raise ValueError('independent feasible count')
  residual[bid]-=item
 if type(body.get('work_units')) is not int or not 0<=body['work_units']<=5000000 or r.get('work_units')!=body['work_units']:raise ValueError('work units')
 return {'case_id':case['id'],'status':'completed_valid','used_bins':checked['used_bins'],'L1':checked['L1'],'assignment':r['assignment'],'residuals':r['residuals'],'work_units':body['work_units'],'warning_events':len(w['events']),'warning_trace_sha256':hashlib.sha256(json.dumps(w,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(),'complete_semantic_measurement':True,'scope':'Independent packing feasibility/counts; floating-score policy not independently replayed.'}

def run_score(raw,case,directory):
 directory=pathlib.Path(directory);directory.mkdir(parents=True,exist_ok=False)
 req={'mode':'pack','program_json':raw.decode('utf-8'),'items':case['items'],'capacity':case['capacity']}
 payload=json.dumps(req,separators=(',',':'),allow_nan=False).encode();(directory/'request.json').write_bytes(payload)
 obs=request(req)
 # Persist full bounded transport before interpreting success/failure. Caller
 # separately retains minimal returned PID/cost evidence if this write fails.
 try:
  (directory/'observation.json').write_text(json.dumps(obs,indent=2,allow_nan=False)+'\n')
  checked=check_observation(raw,case,obs)
  checked.update({'source_sha256':hashlib.sha256(raw).hexdigest(),'input_sha256':hashlib.sha256(json.dumps({'items':case['items'],'capacity':case['capacity']},separators=(',',':')).encode()).hexdigest()})
  (directory/'checked.json').write_text(json.dumps(checked,indent=2,allow_nan=False)+'\n')
  return checked,obs
 except Exception as exc:
  exc.observation=obs
  raise
