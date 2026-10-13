"""Standard JSON-schema boundary checks only; no model/interpreter execution."""
import copy,hashlib,importlib.metadata,json,pathlib,resource,time
from jsonschema import Draft202012Validator
P=pathlib.Path(__file__).resolve().parents[1]
start=time.monotonic();cpu=time.process_time();schema=json.loads((P/'generation_schema.json').read_text());Draft202012Validator.check_schema(schema);v=Draft202012Validator(schema);base=json.loads((P/'data/fixed_target.json').read_text());cases=[]
def add(name,obj,want):cases.append((name,copy.deepcopy(obj),want))
add('fixed_target',base,True)
for k in [0,1,63,64,65]:
 d=copy.deepcopy(base);d['description']='x'*k;add('description_'+str(k),d,1<=k<=64)
for k in [0,1,2,3,4]:
 d=copy.deepcopy(base);d['constants']=[{'type':'f64','value':1.0}]*k;add('constants_'+str(k),d,k<=3)
for k in [0,1,4,5]:
 d=copy.deepcopy(base);d['nodes']=[['mul','bins','c0']]*k;d['return_node']=0;add('nodes_'+str(k),d,1<=k<=4)
for x in [0,3,4,-1,True,'0']:
 d=copy.deepcopy(base);d['return_node']=x;add('return_'+repr(x),d,type(x)is int and 0<=x<=3)
for x in ['item','bins','c0','c2','c3',0,3,4,-1,True,'x']:
 d=copy.deepcopy(base);d['nodes'][0][1]=x;add('operand_'+repr(x),d,(type(x)is str and x in ['item','bins','c0','c2'])or(type(x)is int and 0<=x<=3))
for n in [1,2,3,4,5]:
 d=copy.deepcopy(base);d['nodes'][0]=(['sub','bins','item','c0','c1'])[:n];add('sub_arity_'+str(n),d,n==3)
for key in base:
 d=copy.deepcopy(base);del d[key];add('missing_'+key,d,False)
d=copy.deepcopy(base);d['extra']=None;add('extra',d,False)
rows=[]
for name,obj,want in cases:
 observed=v.is_valid(obj);raw=json.dumps(obj,separators=(',',':'),allow_nan=False).encode();rows.append({'id':name,'expected':want,'observed':observed,'sha256':hashlib.sha256(raw).hexdigest()})
 if observed!=want:raise ValueError(name)
report={'status':'passed','schema_sha256':hashlib.sha256((P/'generation_schema.json').read_bytes()).hexdigest(),'validator':'jsonschema','version':importlib.metadata.version('jsonschema'),'draft':'2020-12','cases':rows,'case_count':len(rows),'scope':'Syntactic schema boundaries only. Backward-reference existence and scalar/vector typing remain enforced by unchanged DAG validator; some schema-positive test objects deliberately fail that later gate.','cpu_seconds':time.process_time()-cpu,'wall_seconds':time.monotonic()-start,'model_calls':0,'numeric_worker_calls':0}
with (P/'offline/schema_validation_01.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in report.items() if k!='cases'}))
