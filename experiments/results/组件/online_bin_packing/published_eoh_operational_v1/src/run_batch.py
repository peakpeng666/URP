"""Exactly one explicitly approved frozen 30-slot trusted fixed formula batch."""
import argparse,datetime,hashlib,json,os,pathlib,re,resource,sys,time
from integrity import ROOT,verify
from runtime import request,AS
from checker import check_assignment,aggregate_records

def save(path,value):
 tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');os.replace(tmp,path)
def execute(slots,instances,out,integrity_check,executor=request,clock=time.monotonic,cpuclock=time.process_time,budget_cpu=300,budget_wall=600):
 start=clock();owncpu=cpuclock();worker_cpu=0.;ledger=[dict(s) for s in slots];stop=None;validated=[];attempts=0;io_errors=[];events=None
 try:
  save(out/'ledger_initial.json',{'rows':ledger});events=(out/'events.jsonl').open('x')
 except Exception as exc:io_errors.append('initial persistence: '+str(exc));stop='persistence_failure'
 def event(row):
  try:
   if events is None:raise OSError('event journal unavailable')
   events.write(json.dumps(row,allow_nan=False)+'\n');events.flush();return True
  except Exception as exc:io_errors.append('event persistence: '+str(exc));return False
 for row in ledger:
  if stop:row['status']='not_run_'+stop;continue
  try:integrity_check()
  except Exception as exc:
   stop='integrity_failure';row.update(status='not_run_integrity_failure',error=str(exc));continue
  if worker_cpu+(cpuclock()-owncpu)+20>budget_cpu or clock()-start+31>budget_wall:
   stop='budget_reservation';row['status']='not_run_budget_reservation';continue
  ins=instances[row['instance_id']];row['status']='dispatch_intent';row['attempt_index']=attempts
  if not event({'event':'start','meaning':'dispatch intent, not launch proof','slot_id':row['id'],'attempt_index':row['attempt_index'],'elapsed_wall':clock()-start}):
   stop='persistence_failure';row['status']='not_run_persistence_failure';continue
  row['dispatch_attempted']=True;row['status']='request_started';attempts+=1
  observation=None
  try:
   observation=executor(ins['items'],row['capacity'],row['method'])
   # Preserve minimal returned execution evidence before persistence/classification.
   row['execution']={k:observation.get(k) for k in ['pid','returncode','termination','error','reaped','wall_seconds','cleanup_seconds','worker_cpu_seconds','worker_peak_rss_kib','cpu_evidence_complete','raw_output_sha256']}
   worker_cpu+=observation['worker_cpu_seconds']
   save(out/'observations'/f"{row['index']:02d}.json",observation)
   if observation['returncode']!=0 or observation['termination'] or observation['error'] or not observation['reaped'] or not observation['cpu_evidence_complete']:raise RuntimeError('worker transport/resource failure')
   r=observation['result']
   if r.get('method')!='EOH_formula_reimplementation' or r.get('pid')!=observation['pid'] or r.get('warnings',{}).get('complete') is not True:raise RuntimeError('worker method/PID/warnings mismatch')
   row['warning_count']=len(r['warnings']['events'])
   checked=check_assignment(ins['items'],row['capacity'],r['assignment'],r['used_bins'],r['residuals'])
   if r['effective_limits']!={'RLIMIT_AS':[AS,AS],'RLIMIT_CPU':[20,20],'RLIMIT_FSIZE':[0,0],'RLIMIT_NOFILE':[32,32]}:raise RuntimeError('worker effective limits mismatch')
   if len(r['feasible_counts'])!=row['n'] or r['n_bin_feasibility_checks']!=row['n']**2:raise RuntimeError('work-count schema')
   row.update(status='completed_valid',used_bins=checked['used_bins'],L1=checked['L1'],diagnostic_lower_bound=checked['diagnostic_lower_bound'],per_instance_excess=checked['per_instance_excess'],observation=f"observations/{row['index']:02d}.json")
   validated.append(dict(row))
  except Exception as exc:
   row.update(status='failed',error=type(exc).__name__+': '+str(exc));stop='failure'
  if not event({'event':'terminal','slot_id':row['id'],'status':row['status'],'execution':row.get('execution'),'error':row.get('error')}):stop='persistence_failure'
  try:save(out/'ledger_checkpoint.json',{'rows':ledger})
  except Exception as exc:io_errors.append('checkpoint persistence: '+str(exc));stop='persistence_failure'
  if worker_cpu+(cpuclock()-owncpu)>budget_cpu or clock()-start>budget_wall:stop='observed_budget_exceeded'
 if events is not None:
  try:events.close()
  except Exception as exc:io_errors.append('event close: '+str(exc));stop='persistence_failure'
 try:integrity_check()
 except Exception as exc:stop='integrity_failure';integrity_error=str(exc)
 else:integrity_error=None
 groups=[]
 if len(validated)==len(slots) and len(slots)==30 and stop is None:groups=aggregate_records(validated)
 wall=clock()-start;supercpu=cpuclock()-owncpu
 if worker_cpu+supercpu>budget_cpu or wall>budget_wall:
  stop='observed_budget_exceeded';groups=[]
 dispatched=[r for r in ledger if r.get('dispatch_attempted')]
 evidence_complete=all(r.get('execution',{}).get('cpu_evidence_complete') is True for r in dispatched)
 execution_counts={'dispatch_attempts':len(dispatched),'returned_observations':sum('execution' in r for r in dispatched),'observed_worker_pids':sum(r.get('execution',{}).get('pid') is not None for r in dispatched),'requests_without_returned_execution_evidence':sum('execution' not in r for r in dispatched),'observed_workers_not_confirmed_reaped':sum(r.get('execution',{}).get('pid') is not None and r.get('execution',{}).get('reaped') is not True for r in dispatched),'worker_cpu_evidence_complete':evidence_complete}
 summary={'rows':ledger,'execution_counts':execution_counts,'requests_dispatched':attempts,'completed_valid':len(validated),'stop_reason':stop,'integrity_error':integrity_error,'persistence_errors':io_errors,'groups':groups,'certified_complete':len(validated)==30 and stop is None,'cost':{'worker_cpu_evidence_complete':evidence_complete,'worker_cpu_sum_is_lower_bound_if_incomplete':not evidence_complete,'worker_cpu_seconds':worker_cpu,'supervisor_cpu_seconds':supercpu,'accounted_cpu_seconds':worker_cpu+supercpu,'wall_seconds':wall,'cpu_overshoot_seconds':max(0,worker_cpu+supercpu-budget_cpu),'wall_overshoot_seconds':max(0,wall-budget_wall),'supervisor_peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},'metric':'Published formula reimplementation on historicaldata/correctedcapacities; no author-byteexecution parity, EoH evolution or algorithm innovation claim'}
 try:save(out/'report.json',summary)
 except Exception as exc:
  io_errors.append('report persistence: '+str(exc));summary['stop_reason']='persistence_failure';summary['certified_complete']=False;summary['groups']=[]
 # Charge the first publication before the final bounded accounting snapshot.
 finalize_budget(summary,worker_cpu+cpuclock()-owncpu,clock()-start,budget_cpu,budget_wall)
 summary['accounting_note']='Measured through initial report publication; final bounded JSON snapshot/console publication is outside this last measurement and not claimed mathematically zero.'
 try:save(out/'report.json',summary)
 except Exception as exc:
  io_errors.append('final report persistence: '+str(exc));summary['stop_reason']='persistence_failure';summary['certified_complete']=False;summary['groups']=[]
 return summary

def finalize_budget(report,total_cpu,wall,budget_cpu,budget_wall):
 report['measured_through_initial_publication']={'accounted_cpu_seconds':total_cpu,'wall_seconds':wall,'cpu_overshoot_seconds':max(0,total_cpu-budget_cpu),'wall_overshoot_seconds':max(0,wall-budget_wall)}
 if total_cpu>budget_cpu or wall>budget_wall:
  report['stop_reason']='observed_budget_exceeded';report['certified_complete']=False;report['groups']=[]

def validate_approval(raw,expected):
 if len(raw)>10000:raise ValueError('approval bound')
 approval=json.loads(raw)
 if approval.get('freeze_sha256')!=expected or approval.get('scope')!='p3_eoh_formula_reimplementation_30_v1' or approval.get('max_requests')!=30 or approval.get('authorized') is not True:raise ValueError('approval mismatch')
 if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',approval.get('run_id','')):raise ValueError('run_id')
 return approval

def claim_approval(raw,approval,out,marker_dir):
 marker_dir.mkdir(parents=True,exist_ok=True)
 marker=marker_dir/(approval['run_id']+'.json')
 with marker.open('x') as f:json.dump({'approval_sha256':hashlib.sha256(raw).hexdigest(),'freeze_sha256':approval['freeze_sha256'],'output':str(out),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},f)
 return marker

def main():
 a=argparse.ArgumentParser();a.add_argument('--freeze',required=True);a.add_argument('--freeze-sha256',required=True);a.add_argument('--approval',required=True);a.add_argument('--output',required=True);args=a.parse_args()
 resource.setrlimit(resource.RLIMIT_AS,(AS,AS));resource.setrlimit(resource.RLIMIT_CPU,(300,300))
 fullstart=time.monotonic();fullcpu=time.process_time();freeze=verify(args.freeze,args.freeze_sha256)
 preparation=json.loads((ROOT/'preparation_costs.json').read_text())
 cpu_budget=300-preparation['charged_cpu_seconds'];wall_budget=600-preparation['charged_wall_seconds']
 if cpu_budget<20 or wall_budget<31:raise ValueError('insufficientremainingcombinedbudget')
 approval_raw=pathlib.Path(args.approval).read_bytes()
 approval=validate_approval(approval_raw,args.freeze_sha256)
 out=pathlib.Path(args.output);out.mkdir(parents=True,exist_ok=False);(out/'observations').mkdir()
 # Exclusive marker is bound to approval bytes; no reruns with same approval.
 claim_approval(approval_raw,approval,out,ROOT/'.authorization_uses')
 slots=json.loads((ROOT/'prepared_plan.json').read_text())['slots'];data=json.loads((ROOT.parent/'paper_baseline_v1/data/historical_numeric.json').read_text())['instances']
 if len(slots)!=30 or len({s['id'] for s in slots})!=30 or len(data)!=15:raise ValueError('population shape')
 report=execute(slots,{x['id']:x for x in data},out,lambda:verify(args.freeze,args.freeze_sha256),budget_cpu=cpu_budget-(time.process_time()-fullcpu),budget_wall=wall_budget-(time.monotonic()-fullstart))
 report['preparation_charge']=preparation
 report['whole_cost']={'supervisor_cpu_seconds':time.process_time()-fullcpu,'wall_seconds':time.monotonic()-fullstart,'effective_supervisor_limits':{'RLIMIT_AS':list(resource.getrlimit(resource.RLIMIT_AS)),'RLIMIT_CPU':list(resource.getrlimit(resource.RLIMIT_CPU))}}
 try:save(out/'report.json',report)
 except Exception as exc:report['persistence_errors'].append('whole report: '+str(exc));report['stop_reason']='persistence_failure';report['certified_complete']=False;report['groups']=[]
 finalize_budget(report,report['cost']['worker_cpu_seconds']+time.process_time()-fullcpu,time.monotonic()-fullstart,cpu_budget,wall_budget)
 try:save(out/'report.json',report)
 except Exception as exc:
  report['persistence_errors'].append('terminal snapshot: '+str(exc));report['stop_reason']='persistence_failure';report['certified_complete']=False;report['groups']=[]
 if report['persistence_errors']:print(json.dumps({'terminal_report_fallback':report},allow_nan=False),flush=True)
 print(json.dumps({k:report[k] for k in ['requests_dispatched','completed_valid','stop_reason','cost','whole_cost']},indent=2))
if __name__=='__main__':main()
