"""Host-only admission/measurement checks; never evaluates a graph or imports NumPy."""
import hashlib,json,math,pathlib,struct,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
MATH=ROOT.parent/'math_dag_v1'
sys.path.insert(0,str(MATH/'src'))
from schema import validate_program,strict_json

def identity(program):
 constants=[(t,v if t=='i32' else float(v).hex()) for t,v in program.constants]
 return hashlib.sha256(json.dumps([constants,program.nodes,program.return_node],separators=(',',':')).encode()).hexdigest()

def admit(raw):
 p=validate_program(raw);obj=strict_json(raw)
 if len(p.nodes)>6 or len(p.constants)>8 or len(p.description)>64:raise ValueError('compact profile rejected')
 return p,obj

def check(raw,case,obs):
 p,obj=admit(raw)
 if obs.get('returncode')!=0 or obs.get('termination') is not None or obs.get('error') is not None or obs.get('reaped') is not True or obs.get('cpu_evidence_complete') is not True:raise ValueError('evaluator transport/infrastructure failure')
 body=obs.get('result');n=len(case['bins'])
 if type(body) is not dict or body.get('pid')!=obs.get('pid') or body.get('limits')!={'RLIMIT_AS':[2147483648,2147483648],'RLIMIT_CPU':[20,20],'RLIMIT_FSIZE':[0,0],'RLIMIT_NOFILE':[32,32]}:raise ValueError('worker identity/limits')
 if body.get('program_sha256')!=p.raw_sha256 or body.get('canonical_program_sha256')!=p.canonical_sha256 or body.get('phase')!='evaluate':raise ValueError('source/phase binding')
 w=body.get('warnings')
 if type(w) is not dict or set(w)!={'events','kinds','complete','incomplete_reason'} or type(w['complete']) is not bool or type(w['events']) is not list or type(w['kinds']) is not list or len(w['events'])>12000 or len(w['kinds'])>32:raise ValueError('warning envelope')
 for event in w['events']:
  if type(event) is not list or len(event)!=3 or any(type(x)is not int for x in event) or event[0]!=0 or not 0<=event[1]<len(p.nodes) or not 0<=event[2]<len(w['kinds']):raise ValueError('warning binding')
 for kind in w['kinds']:
  if type(kind)is not dict or set(kind)!={'category','module','file','line','message'} or kind['category']!='RuntimeWarning' or kind['file']!='interpreter.py' or type(kind['line'])is not int or type(kind['message'])is not str or len(kind['message'].encode())>1024:raise ValueError('warning kind')
 if (w['complete'] and w['incomplete_reason'] is not None) or (not w['complete'] and type(w['incomplete_reason'])is not str):raise ValueError('warning completeness')
 out={'case_id':case['id'],'program_sha256':p.raw_sha256,'graph_identity':identity(p),'warning_count':len(w['events']),'warning_trace_sha256':hashlib.sha256(json.dumps(w,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
 status=body.get('status')
 if status in {'numeric_invalid','resource_unresolved','diagnostic_unresolved'}:
  if body.get('result') is not None or type(body.get('error'))is not dict:raise ValueError('failed measurement shape')
  return dict(out,status=status,error=body['error'],complete_numeric_measurement=False)
 if status!='completed_finite' or body.get('error')is not None or w['complete']is not True:raise ValueError('unexpected evaluator stage/status')
 v=body.get('result')
 if type(v)is not dict or set(v)!={'dtype','shape','scores_sha256','scores','first_argmax','node_trace'} or v['dtype']!='float64' or v['shape']!=[n]:raise ValueError('score shape/dtype')
 scores=v['scores']
 if type(scores)is not list or len(scores)!=n or any(type(x)is not float or not math.isfinite(x) for x in scores):raise ValueError('score values')
 if v['scores_sha256']!=hashlib.sha256(struct.pack('='+str(n)+'d',*scores)).hexdigest():raise ValueError('score bytes hash')
 argmax=max(range(n),key=scores.__getitem__)
 if type(v['first_argmax'])is not int or v['first_argmax']!=argmax:raise ValueError('first tie/argmax')
 trace=v['node_trace']
 if type(trace)is not list or len(trace)!=len(p.nodes):raise ValueError('trace count')
 for tag,node in zip(p.types,trace):
  shape=[n] if tag.startswith('v') else [];dtype={'i32':'int32','f64':'float64','vi64':'int64','vf64':'float64','vb':'bool'}[tag]
  if type(node)is not dict or node.get('type')!=tag or node.get('dtype')!=dtype or node.get('shape')!=shape:raise ValueError('trace type/shape')
  if type(node.get('sha256'))is not str or len(node['sha256'])!=64 or any(c not in '0123456789abcdef' for c in node['sha256']):raise ValueError('trace hash')
  count=n if shape else 1
  if any(type(node.get(k))is not int or not 0<=node[k]<=count for k in ['nan_count','positive_infinity_count','negative_infinity_count']):raise ValueError('trace classification')
 if type(body.get('work_units'))is not int or body['work_units']!=len(p.nodes)*n:raise ValueError('work units')
 return dict(out,status='completed_finite',scores=scores,first_argmax=argmax,differs_from_ff_and_bf=argmax!=case['ff_index'] and argmax!=case['bf_index'],complete_numeric_measurement=True,scope='Host-checked finite scores and first argmax in3 handwritten vectors; no independent numerical policy replay or packing-quality claim.')
