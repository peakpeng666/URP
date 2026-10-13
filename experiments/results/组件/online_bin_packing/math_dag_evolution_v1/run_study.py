"""Fixed22-slot study. Default is read-only verification; no implicit execution."""
import argparse,hashlib,json,os,pathlib,re,resource,sys,time,traceback
sys.dont_write_bytecode=True
ROOT=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'src'))
from guard import verify,bounded_json,load_cases,Budget,sha

def write_new(path,obj):
 with pathlib.Path(path).open('x') as f:
  json.dump(obj,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())

def authorize(path,expected):
 d=bounded_json(path,10000)
 if d.get('authorized') is not True or d.get('scope')!='p3_math_dag_twogen_22_once' or d.get('freeze_sha256')!=expected or not re.fullmatch('[A-Za-z0-9_-]{1,64}',d.get('run_id','')):raise ValueError('explicit matching study approval required')
 return d

def execute(plan,expected,approval):
 out=ROOT/'runs'/approval['run_id'];out.mkdir(parents=True,exist_ok=False)
 uses=ROOT/'.authorization_uses';uses.mkdir(exist_ok=True)
 write_new(uses/(approval['run_id']+'.json'),{'freeze_sha256':expected,'scope':approval['scope'],'output':str(out.relative_to(ROOT))})
 resource.setrlimit(resource.RLIMIT_AS,(536870912,4294967296));resource.setrlimit(resource.RLIMIT_CPU,(6000,6000))
 budget=Budget(plan);events=(out/'events.jsonl').open('x');dispatch=[];errors=[];state=None;study=None
 def emit(event,payload):
  if event=='winner_commitment':
   write_new(out/'winner_commitment.json',payload)
  events.write(json.dumps({'event':event,'payload':payload},allow_nan=False)+'\n');events.flush();os.fsync(events.fileno())
 def generate(slot,prompt,index):
  verify(expected);budget.reserve('model')
  entry={'kind':'model','slot_id':slot['slot_id'],'adapter_index':index,'server_launch_state':'not_started','post_requests_sent':0};dispatch.append(entry)
  prepared_dir=out/'requests'/slot['slot_id'];raw,prepared=prepare_request(slot,prompt,prepared_dir,plan);entry['preparation']=prepared
  verify(expected);budget.reserve('model') # Tokenization cannot consume a late call's reservation.
  entry['server_launch_state']='entered_backend'
  directory=out/'generation'/slot['slot_id']
  try:
   result=run_once(index,raw,directory);entry['execution']=result;entry['server_launch_state']='returned';entry['post_requests_sent']=result['post_requests_sent']
   if result['cleanup'].get('direct_child_reaped') is not True or result.get('http_post_thread_finished') is not True:raise ValueError('incomplete model cleanup')
   raw_http=(directory/'response_body.json').read_bytes() if (directory/'response_body.json').exists() else b''
   if 'json schema conversion was incomplete' in (directory/'server_stderr.log').read_text(errors='replace').lower():raise ValueError('incomplete schema conversion')
   outcome=decode(slot,raw_http,result,prepared,plan)
   outcome['evidence']={'directory':str(directory.relative_to(out)),'preparation':prepared,'execution':result,'metadata':outcome.get('metadata')}
   write_new(directory/'decoded.json',{k:v for k,v in outcome.items() if k!='content'})
   return outcome
  except Exception as exc:
   entry['error']=type(exc).__name__+': '+str(exc)
   if 'execution' not in entry:entry['server_launch_state']='unknown_after_backend_entry'
   raise
 def score(record,case,index):
  verify(expected);budget.reserve('score');mark=budget.score_mark()
  entry={'kind':'score','source_id':record['source_id'],'case_id':case['id'],'adapter_index':index,'launch_state':'entered_adapter'};dispatch.append(entry)
  directory=out/'scores'/('%03d'%index)
  try:
   checked,obs=run_score(record['program_json'].encode(),case,directory)
   entry.update(launch_state='returned',pid=obs['pid'],reaped=obs['reaped'],worker_cpu_seconds=obs['worker_cpu_seconds'],cpu_evidence_complete=obs['cpu_evidence_complete'])
   return checked,{'directory':str(directory.relative_to(out)),'pid':obs['pid'],'worker_cpu_seconds':obs['worker_cpu_seconds'],'wall_seconds':obs['wall_seconds'],'cleanup_seconds':obs['cleanup_seconds'],'worker_peak_rss_kib':obs['worker_peak_rss_kib']}
  except Exception as exc:
   obs=getattr(exc,'observation',None)
   if obs is not None:entry.update(launch_state='returned_with_error',pid=obs['pid'],reaped=obs['reaped'],worker_cpu_seconds=obs['worker_cpu_seconds'],cpu_evidence_complete=obs['cpu_evidence_complete'])
   else:entry['launch_state']='unknown_after_adapter_entry'
   entry['error']=type(exc).__name__+': '+str(exc);raise
  finally:budget.score_charge(mark)
 def validation_loader():
  committed=bounded_json(out/'winner_commitment.json',100000)
  if study is None or study.selected_hash!=committed['sha256'] or study.selected!=committed['selected']:raise ValueError('durable winner commitment changed')
  verify(expected)
  return load_cases(ROOT/'data/validation.json','validation',plan['data']['validation_case_ids'])
 try:
  verify(expected,full=True)
  from pipeline import Study
  from generation import prepare_request,decode
  from backend import run_once
  from scoring import run_score
  design=load_cases(ROOT/'data/design.json','design',plan['data']['design_case_ids'])
  study=Study(plan,design,plan['data']['validation_case_ids'],generate,score,validation_loader,emit)
  write_new(out/'initial_ledger.json',{'requests':study.requests,'ledger':study.ledger,'freeze_sha256':expected})
  state=study.run()
 except Exception as exc:
  errors.append(type(exc).__name__+': '+str(exc));traceback.print_exc()
 finally:
  try:events.close()
  except Exception as exc:errors.append('event_close: '+str(exc))
  try:verify(expected,full=True)
  except Exception as exc:errors.append('final_integrity: '+str(exc))
  costs=budget.terminal()
  if not costs['within_charged_budget']:errors.append('observed charged budget exceeded')
  if state is None:state={'state':'incomplete','requests':[] if study is None else study.requests,'ledger':[] if study is None else study.ledger,'halt':'entrypoint failure'}
  if errors:state['state']='uncertified_incomplete'
  descriptive={'complete':False,'scope':'prelaunch or unclassified failure'}
  if study is not None:
   try:
    from summary import summarize
    descriptive=summarize(state,dispatch)
   except Exception as exc:errors.append('summary: '+str(exc));state['state']='uncertified_incomplete'
  result={'summary':descriptive,'freeze_sha256':expected,'state':state,'errors':errors,'dispatches':dispatch,'costs':costs,'formal_posts_observed':sum(x.get('post_requests_sent',0) for x in dispatch),'unknown_model_launch_states':sum(x.get('server_launch_state')=='unknown_after_backend_entry' for x in dispatch),'preparation_costs':bounded_json(ROOT/'preparation_costs.json'),'supervisor_peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'timing_boundary':'Measured through final integrity; final report persistence/console follows. Shared preparation debit is not a measured cost. Unmetered source/review work is disclosed separately.'}
  try:write_new(out/'report.json',result)
  except Exception as exc:result['errors'].append('report_persistence: '+str(exc));result['state']['state']='uncertified_incomplete'
  print(json.dumps({'output':str(out),'state':result['state']['state'],'formal_posts_observed':result['formal_posts_observed'],'errors':result['errors'],'costs':costs}),flush=True)
  return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--freeze-sha256',required=True);p.add_argument('--execute-approved',action='store_true');p.add_argument('--approval');a=p.parse_args()
 verify(a.freeze_sha256);plan=bounded_json(ROOT/'protocol.json')
 if not a.execute_approved:
  print(json.dumps({'status':'verified_sources_only','model_calls':0,'score_calls':0,'planned_model_calls_max':22}));return
 if not a.approval:raise ValueError('approval file required')
 approval=authorize(a.approval,a.freeze_sha256)
 result=execute(plan,a.freeze_sha256,approval)
 if result['state']['state']!='completed':raise SystemExit(1)
if __name__=='__main__':main()
