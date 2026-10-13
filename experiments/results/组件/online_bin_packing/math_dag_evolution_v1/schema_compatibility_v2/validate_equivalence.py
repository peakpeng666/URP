"""Data-only schema checks plus fixed official converter --help; no model/POST."""
import copy,hashlib,importlib.metadata,json,pathlib,sys,time,resource
ROOT=pathlib.Path(__file__).resolve().parents[1];HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'math_dag_v1/src'))
from runtime import request
from jsonschema import Draft202012Validator

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):
 with p.open('x') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def main():
 started=time.monotonic();cpu=time.process_time();before=resource.getrusage(resource.RUSAGE_CHILDREN)
 old_path=ROOT/'generation_schema.json';old_raw=old_path.read_bytes()
 if hashlib.sha256(old_raw).hexdigest()!='ca619cda38735478cebfb93c6e46471464a4ed48e370a7ebff32b857d9bf41b7':raise ValueError('original schema identity')
 old=json.loads(old_raw);new=copy.deepcopy(old)
 paths=[]
 for i,branch in enumerate(new['properties']['nodes']['items']['anyOf']):
  if branch.get('items') is not False or branch['minItems']!=branch['maxItems'] or branch['maxItems']!=len(branch['prefixItems']):raise ValueError('tuple proof precondition')
  del branch['items'];paths.append('/properties/nodes/items/anyOf/'+str(i)+'/items')
 if len(paths)!=8:raise ValueError('eight exact deletions')
 new_path=ROOT/'generation_schema_v2.json'
 with new_path.open('x') as f:json.dump(new,f,indent=2);f.write('\n')
 Draft202012Validator.check_schema(old);Draft202012Validator.check_schema(new)
 a=Draft202012Validator(old);b=Draft202012Validator(new)
 base=json.loads((ROOT/'interface_smoke/target.json').read_bytes());cases=[]
 def add(label,obj):cases.append((label,copy.deepcopy(obj)))
 add('known_target',base)
 for i,branch in enumerate(old['properties']['nodes']['items']['anyOf']):
  op=branch['prefixItems'][0]['const'];k=len(branch['prefixItems']);node=[op]+['bins']*(k-1)
  for length in range(0,7):
   d=copy.deepcopy(base);d['nodes']=[(node+['bins']*7)[:length]];add(op+'_length_'+str(length),d)
  for operand in ['item','bins','c0','c15','c16','__class__',0,63,64,-1,0.0,True,None,{},[]]:
   d=copy.deepcopy(base);d['nodes']=[node[:]];d['nodes'][0][1]=operand;add(op+'_operand_'+repr(operand),d)
  d=copy.deepcopy(base);d['nodes']=[node];d['nodes'][0][0]='unknown';add(op+'_bad_op',d)
 for count in [0,1,64,65]:
  d=copy.deepcopy(base);d['nodes']=[base['nodes'][0] for _ in range(count)];add('nodes_'+str(count),d)
 for count in [0,1,16,17]:
  d=copy.deepcopy(base);d['constants']=[base['constants'][0] for _ in range(count)];add('constants_'+str(count),d)
 for text in ['', 'a','a'*160,'a'*161,'é'*160,'line\nbreak']:
  d=copy.deepcopy(base);d['description']=text;add('description_'+repr(text[:12])+'_'+str(len(text)),d)
 for typ in ['i32','f64','other']:
  for value in [-1001,-1000,0,1000,1001,0.5,True,None,'0']:
   d=copy.deepcopy(base);d['constants']=[{'type':typ,'value':value}];add('constant_'+typ+'_'+repr(value),d)
 for value in [0,63,64,-1,0.0,True,None,'0']:
  d=copy.deepcopy(base);d['return_node']=value;add('return_'+repr(value),d)
 for key in list(base):
  d=copy.deepcopy(base);del d[key];add('missing_'+key,d)
 d=copy.deepcopy(base);d['extra']=1;add('extra_key',d)
 for obj in [None,False,0,[],{},'text']:add('root_'+repr(obj),obj)
 rows=[]
 for label,obj in cases:
  # Roundtrip only standard finite JSON values; not Python NaN/Infinity extensions.
  raw=json.dumps(obj,separators=(',',':'),allow_nan=False).encode();obj=json.loads(raw)
  x=a.is_valid(obj);y=b.is_valid(obj)
  rows.append({'id':label,'instance_sha256':hashlib.sha256(raw).hexdigest(),'old_valid':x,'v2_valid':y})
  if x!=y:raise ValueError('standard-schema mismatch: '+label)
 save(HERE/'standard_validation.json',{'validator':'jsonschema','version':importlib.metadata.version('jsonschema'),'draft':'2020-12','cases':rows,'cases_count':len(rows),'all_acceptance_equal':True,'proof':'All eight deleted items:false constraints only apply after a fixed prefix length k. minItems=maxItems=k means no such positions exist. All other schema clauses are byte-logically unchanged. Thus accepted standard JSON instances are unchanged for each tuple branch and the whole composition. Cases are boundary evidence, not an exhaustive enumeration.','scope':'Syntax-schema equivalence only; backreference/type/f64 bounds remain the unchanged DAG validator responsibility.'})
 runtime=ROOT.parents[1]/'direct_route_generation_local_v2/vendor/runtime/llama-b11387/llama-server'
 freeze_path=ROOT/'interface_smoke/freeze.json'
 if sha(freeze_path)!='bfe195ff3c8d9de97be0b0ca68aa0f06ad4db05d2011505391dad3e113776b77':raise ValueError('original smoke freeze')
 frozen=json.loads(freeze_path.read_bytes());runtime_assets={}
 for rel,want in frozen['asset_sha256'].items():
  if '/vendor/runtime/' in rel:
   path=(freeze_path.parent/rel).resolve()
   if sha(path)!=want:raise ValueError('official runtime asset changed')
   runtime_assets[str(path)]=want
 results=[]
 for name,path in [('old',old_path),('v2',new_path)]:
  command=[str(runtime),'--offline','--no-models-autoload','--no-agent','--no-webui','--host','127.0.0.1','--json-schema-file',str(path),'--help']
  obs=request({},command=command,wall=10)
  save(HERE/(name+'_converter_observation.json'),obs)
  import base64
  stdout=base64.b64decode(obs['raw_stdout_base64']);stderr=base64.b64decode(obs['raw_stderr_base64'])
  no_load=all(x not in stderr for x in [b'llama_model_loader:',b'load_tensors:',b'loading model',b'listening on http://'])
  if not obs['reaped'] or obs['termination'] is not None or not obs['cpu_evidence_complete'] or not no_load:raise ValueError('offline helper process boundary: '+name)
  if name=='old':ok=obs['returncode']!=0 and b'schema must be an object' in stderr
  else:ok=obs['returncode']==0 and b'--json-schema' in stdout and b'JSON schema conversion was incomplete' not in stderr
  results.append({'version':name,'command':command,'passed_expected_outcome':ok,'returncode':obs['returncode'],'no_model_path_supplied':True,'no_model_loading_or_listening_log':no_load,'worker_cpu_seconds':obs['worker_cpu_seconds'],'worker_wall_seconds':obs['wall_seconds'],'worker_peak_rss_kib':obs['worker_peak_rss_kib'],'stdout_sha256':obs['raw_output_sha256'],'stderr_sha256':obs['stderr_sha256']})
  if not ok:raise ValueError('offline converter unexpected result: '+name)
 if sha(old_path)!=hashlib.sha256(old_raw).hexdigest():raise ValueError('old schema changed')
 after=resource.getrusage(resource.RUSAGE_CHILDREN)
 report={'status':'passed','old_sha256':sha(old_path),'v2_sha256':sha(new_path),'deleted_paths':paths,'cases':len(rows),'converter_binary':str(runtime),'converter_binary_sha256':sha(runtime),'converter_results':results,'mode':'Same fixed official server argument parser converts schema before --help exits; no model argument, no weight load, no socket/POST/generation/scoring. This proves conversion acceptance, not exhaustive grammar behavior.','supervisor_cpu_seconds':time.process_time()-cpu,'children_cpu_seconds':after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,'wall_seconds':time.monotonic()-started,'runtime_asset_sha256':runtime_assets,'source_parser_path':'../source_evidence/json-schema.cpp.txt','source_arg_provenance':'Fixed official common/arg.cpp lines2288–2303 and1297–1303; installed official binary invokes converter in argument handler, then exits for usage before main model initialization.'}
 save(HERE/'report.json',report);print(json.dumps(report,indent=2))
if __name__=='__main__':main()
