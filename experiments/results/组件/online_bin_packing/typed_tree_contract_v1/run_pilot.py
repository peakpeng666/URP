"""At most4 optional local calls/12 fixed-vector observations; no implicit execution."""
import argparse,hashlib,json,os,pathlib,re,resource,sys,time
sys.dont_write_bytecode=True
ROOT=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'src'))
from guard import verify,bounded_json,Budget

def save(path,obj):
 with pathlib.Path(path).open('x') as f:json.dump(obj,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def authorize(path,expected):
 d=bounded_json(path,10000)
 if d.get('authorized')is not True or d.get('scope')!='typed_tree_contract4_once' or d.get('freeze_sha256')!=expected or not re.fullmatch('[A-Za-z0-9_-]{1,64}',d.get('run_id','')):raise ValueError('matching one-use diagnostic authorization required')
 return d

def execute(plan,expected,approval):
 out=ROOT/'runs'/approval['run_id'];out.mkdir(parents=True,exist_ok=False)
 uses=ROOT/'.authorization_uses';uses.mkdir(exist_ok=True);save(uses/(approval['run_id']+'.json'),{'scope':approval['scope'],'freeze_sha256':expected,'output':str(out.relative_to(ROOT))})
 resource.setrlimit(resource.RLIMIT_AS,(536870912,4294967296));resource.setrlimit(resource.RLIMIT_CPU,(1000,1000))
 budget=Budget(plan);events=None;errors=[];dispatch=[];grammar_hash=None
 slots=bounded_json(ROOT/'transport_preparation.json')['slots'];cases=bounded_json(ROOT/'data/manual_cases.json')['cases']
 rows=[dict(slot,status='not_run',reason='not_reached',generation_evidence=None) for slot in slots]
 ledger=[{'slot_id':s['id'],'case_id':c['id'],'status':'not_run','reason':'not_reached','observation':None} for s in slots for c in cases]
 def emit(kind,value):events.write(json.dumps({'event':kind,'payload':value},allow_nan=False)+'\n');events.flush();os.fsync(events.fileno())
 try:
  verify(expected,full=True)
  from measurement import admit,check,identity,strict_json
  from typed_tree import compile_tree
  from transport_check import decode
  from runtime import request
  sys.path.insert(0,str(ROOT/'transport'))
  from backend import run_once
  transport=bounded_json(ROOT/'transport_protocol.json')
  target=bounded_json(ROOT/'data/fixed_target.json');target_p=admit((ROOT/'data/fixed_target.json').read_bytes())[0]
  seed_ids={identity(admit((ROOT.parent/'math_dag_evolution_v1/seeds'/name).read_bytes())[0]) for name in ['ff.json','bf.json']}
  events=(out/'events.jsonl').open('x');save(out/'initial_ledger.json',{'requests':rows,'ledger':ledger,'freeze_sha256':expected})
  for i,(slot,row) in enumerate(zip(slots,rows)):
   verify(expected);budget.reserve('model');row.update(status='pre_dispatch',reason=None)
   emit('model_start',{'slot_id':slot['id'],'index':i})
   entry={'kind':'model','slot_id':slot['id'],'launch_state':'entered_backend','post_requests_sent':0};dispatch.append(entry);row['request_dispatched']=True
   directory=out/'generation'/slot['id']
   slot_start=time.monotonic()
   result=run_once(i,(ROOT/slot['request_file']).read_bytes(),directory)
   observed_slot_wall=time.monotonic()-slot_start
   result['driver_observed_run_once_wall_seconds']=observed_slot_wall
   entry.update(launch_state='returned',post_requests_sent=result.get('post_requests_sent',0),execution=result);row['generation_evidence']=str(directory.relative_to(out))
   if observed_slot_wall>120:raise ValueError('observed full request lifecycle exceeded120 seconds')
   if 'json schema conversion was incomplete' in (directory/'server_stderr.log').read_text(errors='replace').lower():raise ValueError('incomplete schema conversion')
   raw=(directory/'response_body.json').read_bytes() if (directory/'response_body.json').exists() else b''
   outcome=decode(slot,raw,result,slot,transport);metadata=outcome.get('metadata');row['metadata']=metadata
   if metadata:
    gh=metadata['grammar_sha256']
    if grammar_hash is not None and gh!=grammar_hash:raise ValueError('same-schema native grammar changed')
    grammar_hash=gh
    with (directory/'effective_grammar.gbnf').open('xb') as gf:gf.write(strict_json(raw)['generation_settings']['grammar'].encode('utf-8'))
   save(directory/'decoded.json',{k:v for k,v in outcome.items() if k!='content'})
   if outcome['status']!='completed_valid_transport':
    if outcome['status'] not in {'model_limit_stop','model_format_failure','post_send_timeout'}:raise ValueError('unknown generation status')
    row.update(status='generation_failed',reason=outcome['status'])
   else:
    content=outcome['content']
    if (directory/'content.txt').read_bytes()!=content:raise ValueError('original content binding')
    try:
     p,obj=compile_tree(content)
     content=json.dumps(obj,separators=(',',':'),allow_nan=False).encode()
     p,obj=admit(content)
     (directory/'compiled_dag.json').write_bytes(content)
    except ValueError as exc:
     row.update(status='tree_or_dag_rejected',reason=type(exc).__name__+': '+str(exc))
     emit('model_terminal',row)
     raise ValueError('typed contract violation; stop without replacement') from exc
    else:
     row.update(status='dag_admitted',reason=None,graph_identity=identity(p),representation_distinct_from_seeds=identity(p) not in seed_ids,representation_matches_example=identity(p)==identity(target_p),fixed_target_matches=(obj==target if i==0 else None))
   emit('model_terminal',row)
   if row['status']!='dag_admitted':
    for lr in ledger[i*3:(i+1)*3]:lr['reason']=row['status']
    continue
   for j,case in enumerate(cases):
    lr=ledger[i*3+j];verify(expected);budget.reserve('score');mark=budget.score_mark();lr.update(status='pre_dispatch',reason=None)
    emit('score_start',{'slot_id':slot['id'],'case_id':case['id']})
    request_data={'mode':'evaluate','program_json':content.decode(),'item':case['item'],'bins':case['bins']};sd=out/'scores'/('%02d'%(i*3+j));sd.mkdir(parents=True,exist_ok=False);save(sd/'request.json',request_data)
    entry={'kind':'score','slot_id':slot['id'],'case_id':case['id'],'launch_state':'entered_worker'};dispatch.append(entry);lr['request_dispatched']=True
    try:
     obs=request(request_data);entry.update(launch_state='returned',pid=obs.get('pid'),reaped=obs.get('reaped'),worker_cpu_seconds=obs.get('worker_cpu_seconds'),cpu_evidence_complete=obs.get('cpu_evidence_complete'));lr['observation']=str((sd/'observation.json').relative_to(out))
     save(sd/'observation.json',obs);checked=check(content,case,obs);lr.update(status=checked['status'],checked=checked)
     if i==0 and row['fixed_target_matches'] and checked['status']=='completed_finite' and checked['scores']!=case['fixed_target_scores']:raise ValueError('known fixed target numerical mismatch')
     save(sd/'checked.json',checked);emit('score_terminal',lr)
    finally:budget.score_charge(mark)
 except Exception as exc:
  errors.append(type(exc).__name__+': '+str(exc))
 finally:
  for row in rows:
   if row['status']=='pre_dispatch':row.update(status='infrastructure_failure',reason=errors[-1] if errors else 'unterminated')
   elif row['status']=='not_run':row['reason']='stopped_before_slot'
  for lr in ledger:
   if lr['status']=='pre_dispatch':lr.update(status='infrastructure_failure',reason=errors[-1] if errors else 'unterminated')
   elif lr['reason']=='not_reached':lr['reason']='stopped_before_case'
  if events is not None:
   try:events.close()
   except Exception as exc:errors.append('event_close: '+str(exc))
  try:verify(expected,full=True)
  except Exception as exc:errors.append('final_integrity: '+str(exc))
  costs=budget.terminal()
  if not costs['within_charged_budget']:errors.append('observed budget exceeded')
  for i,row in enumerate(rows):
   case_rows=ledger[3*i:3*i+3];row['all3_finite']=all(x['status']=='completed_finite' for x in case_rows);row['observed_behavior_differs_from_both_seeds']=any(x.get('checked',{}).get('differs_from_ff_and_bf')is True for x in case_rows)
   row['interface_gate_met']=row['status']=='dag_admitted' and row['all3_finite'] and not errors
  report={'state':'completed' if not errors else 'incomplete','freeze_sha256':expected,'requests':rows,'ledger':ledger,'dispatches':dispatch,'errors':errors,'costs':costs,'formal_posts_observed':sum(x.get('post_requests_sent',0) for x in dispatch),'score_dispatches':sum(x['kind']=='score' for x in dispatch),'unknown_launch_states':sum(x['launch_state'] in {'entered_backend','entered_worker'} for x in dispatch),'effective_grammar_sha256':grammar_hash,'all_interface_gates_met':all(x['interface_gate_met'] for x in rows),'fixed_transcription_is_generation_quality_evidence':False,'scope':'Separate4-request typed-tree interface diagnostic on3 handwritten vectors; no historical panel/packing quality/algorithm-discovery claim.','timing_boundary':'Through final integrity; report write and console follow. Outer launcher must retain full lifecycle wall.'}
  try:save(out/'report.json',report)
  except Exception as exc:report['errors'].append('report_persistence: '+str(exc));report['state']='incomplete'
  print(json.dumps({'state':report['state'],'output':str(out),'errors':report['errors'],'posts':report['formal_posts_observed'],'scores':report['score_dispatches'],'costs':costs}),flush=True)
  return report

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--freeze-sha256',required=True);p.add_argument('--execute-approved',action='store_true');p.add_argument('--approval');a=p.parse_args();verify(a.freeze_sha256)
 if not a.execute_approved:print(json.dumps({'state':'verified_only','model_calls':0,'score_calls':0}));return
 if not a.approval:raise ValueError('one-use approval required')
 result=execute(bounded_json(ROOT/'protocol.json'),a.freeze_sha256,authorize(a.approval,a.freeze_sha256))
 if result['state']!='completed':raise SystemExit(1)
if __name__=='__main__':main()
