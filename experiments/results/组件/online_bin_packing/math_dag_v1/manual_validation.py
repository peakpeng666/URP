"""One bounded, source-frozen handwritten validation; no model/candidate population."""
import argparse,hashlib,json,pathlib,resource,sys,time,traceback
ROOT=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'src'))
from integrity import verify,sha
from runtime import request,AS
# Trusted independent feasibility checker, never the policy/NumPy implementation.
sys.path.insert(0,str(ROOT.parent/'paper_baseline_v1/src'))
from checker import check_assignment
CPU_BUDGET=90;WALL_BUDGET=120

def save(path,obj):
 with path.open('x') as f:json.dump(obj,f,indent=2,allow_nan=False);f.write('\n')
def require(value,msg):
 if not value:raise ValueError(msg)
def strict_worker(observation,program_json=None):
 require(observation['returncode']==0 and observation['termination'] is None and observation['error'] is None and observation['reaped'] and observation['cpu_evidence_complete'],'clean completed transport required')
 p=observation['result'];require(type(p) is dict,'payload shape')
 if program_json is not None:
  require(p['program_sha256']==hashlib.sha256(program_json.encode()).hexdigest(),'program binding')
  require(p['canonical_program_sha256']==hashlib.sha256(json.dumps(json.loads(program_json),sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest(),'canonical binding')
  w=p['warnings'];require(type(w) is dict and type(w['complete']) is bool and type(w['events']) is list and len(w['events'])<=12000 and type(w['kinds']) is list and len(w['kinds'])<=32,'warning shape')
  for e in w['events']:require(type(e) is list and len(e)==3 and all(type(v) is int for v in e) and 0<=e[0]<256 and 0<=e[1]<64 and 0<=e[2]<len(w['kinds']),'warning event')
  for k in w['kinds']:require(set(k)=={'category','module','file','line','message'} and k['category']=='RuntimeWarning' and k['file']=='interpreter.py' and type(k['line']) is int and type(k['message']) is str and len(k['message'].encode())<=1024,'warning kind')
  require(type(p['work_units']) is int and 0<=p['work_units']<=5000000,'work units')
  counts=p['numeric_intermediates'];require(set(counts)=={'completed_nodes','nan_elements','positive_infinity_elements','negative_infinity_elements'} and all(type(v) is int and v>=0 for v in counts.values()),'numeric counts')
 return p

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--freeze-sha256',required=True);parser.add_argument('--output',required=True);parser.add_argument('--run-reviewed-handwritten',action='store_true',required=True);a=parser.parse_args()
 # Supervisor does not interpret candidate data. Its own budget and worker usage
 # are reported separately; aggregate ceiling is observed/reserved, not a cgroup.
 resource.setrlimit(resource.RLIMIT_AS,(AS,AS));resource.setrlimit(resource.RLIMIT_CPU,(91,91))
 start=time.monotonic();own=time.process_time();before=resource.getrusage(resource.RUSAGE_CHILDREN)
 rows=[];errors=[];out=pathlib.Path(a.output);out.mkdir(parents=True,exist_ok=False);events=None
 def snapshot():
  ru=resource.getrusage(resource.RUSAGE_CHILDREN);child=ru.ru_utime+ru.ru_stime-before.ru_utime-before.ru_stime
  recorded=sum(r.get('worker_cpu_seconds',0) for r in rows)
  return {'supervisor_cpu_seconds':time.process_time()-own,'children_rusage_cpu_seconds':child,'worker_recorded_cpu_seconds':recorded,'accounted_cpu_seconds':time.process_time()-own+max(child,recorded),'wall_seconds':time.monotonic()-start}
 def dispatch(label,req,check,command=None,wall=30):
  cost=snapshot()
  require(cost['accounted_cpu_seconds']+20<=CPU_BUDGET and cost['wall_seconds']+31<=WALL_BUDGET,'full-call budget reservation')
  row={'id':label,'request_sha256':hashlib.sha256(json.dumps(req,separators=(',',':'),allow_nan=False).encode()).hexdigest(),'status':'started','pid':None,'worker_cpu_seconds':0,'reaped':False,'request_dispatched':False};rows.append(row)
  obs=None
  try:
   events.write(json.dumps({'event':'start','index':len(rows)-1,'id':label})+'\n');events.flush()
   row['request_dispatched']=True
   obs=request(req,command=command,wall=wall)
   row.update({k:obs[k] for k in ['pid','worker_cpu_seconds','worker_peak_rss_kib','wall_seconds','cleanup_seconds','reaped','cpu_evidence_complete']})
   row['observation']='observations/'+label+'.json';save(out/row['observation'],obs)
   check(obs);row['status']='passed'
  except Exception as exc:
   row['status']='failed';row['error']=type(exc).__name__+': '+str(exc);raise
  finally:
   events.write(json.dumps({'event':'terminal','index':len(rows)-1,**row})+'\n');events.flush()
 try:
  freeze=verify(a.freeze_sha256)
  (out/'observations').mkdir();events=(out/'events.jsonl').open('x')
  unit=[sys.executable,'-I','-B',str(ROOT/'tests/run_unit_worker.py')]
  def unitcheck(obs):
   p=strict_worker(obs);r=p['result'];require(p['status']=='completed_finite' and p['error'] is None and r['successful'] is True and r['tests']==24 and r['failures']==r['errors']==0,'unit suite')
   e=r['formula_domain_evidence'];require(len(e)==100 and [x['item'] for x in e]==list(range(1,101)) and sum(x['length'] for x in e)==45050 and sum(x['denominator_inf_count'] for x in e)==9550 and all(x['warning_nodes']==[12] for x in e),'unit domain evidence')
  dispatch('unit_suite',{},unitcheck,unit)
  cases=json.loads((ROOT/'fixtures/evaluation_cases.json').read_bytes())['cases']
  for i,c in enumerate(cases):
   raw=(ROOT/'fixtures'/c['program']).read_text();req={'mode':'evaluate','program_json':raw,'item':c['item'],'bins':c['bins']}
   def check(obs,c=c,raw=raw):
    p=strict_worker(obs,raw);ex=c['expected'];failure='failure' in ex
    require(p['status']==('numeric_invalid' if failure else 'completed_finite'),'expected numeric status')
    require(p['warnings']['complete'] is True,'complete warning evidence')
    if 'warning_nodes' in ex:require([e[1] for e in p['warnings']['events']]==ex['warning_nodes'],'warning order')
    if failure:require(p['result'] is None and type(p['error']) is dict,'no success after numeric failure')
    else:
     r=p['result'];require(p['error'] is None and r['dtype']=='float64' and r['shape']==[len(c['bins'])] and type(r['scores']) is list and len(r['scores'])==len(c['bins']) and all(type(v) is float for v in r['scores']),'finite value shape')
     require(type(r['first_argmax']) is int and 0<=r['first_argmax']<len(c['bins']),'argmax shape')
     if 'argmax' in ex:require(r['first_argmax']==ex['argmax'],'source-derived argmax')
     if 'final_values' in ex:require(r['scores']==ex['final_values'],'handwritten values')
     require(type(r['node_trace']) is list and 1<=len(r['node_trace'])<=64,'bounded trace')
   dispatch('eval_%02d'%i,req,check)
  packing=[('empty','vector_cast',[],100),('stable_tie','vector_cast',[1,1,1],2),('exact_fill','vector_cast',[2,2,2],2),('formula_micro','published_eoh',[1,4,2,3,7,1],10),('formula_warning','published_eoh',[1,100,1,100],500)]
  for label,graph,items,cap in packing:
   raw=(ROOT/'fixtures/programs'/(graph+'.json')).read_text();req={'mode':'pack','program_json':raw,'items':items,'capacity':cap}
   def check(obs,raw=raw,items=items,cap=cap):
    p=strict_worker(obs,raw);require(p['status']=='packing_returned' and p['error'] is None and p['warnings']['complete'],'packing response')
    r=p['result'];check_assignment(items,cap,r['assignment'],r['used_bins'],r['residuals'])
    require(r['placements']==len(items) and len(r['feasible_counts'])==len(items),'placement shape')
    residual=[cap]*len(items)
    for v,bid,count in zip(items,r['assignment'],r['feasible_counts']):
     require(type(count) is int and count==sum(x>=v for x in residual),'feasible count');residual[bid]-=v
   dispatch('pack_'+label,req,check)
  good=(ROOT/'fixtures/programs/vector_cast.json').read_text()
  rejected=[('unknown_op',{'mode':'validate','program_json':good.replace('"div"','"import"')},'structural_rejected'),('bad_item',{'mode':'evaluate','program_json':good,'item':True,'bins':[1]},'input_rejected'),('too_many_placements',{'mode':'pack','program_json':good,'items':[1]*257,'capacity':1},'input_rejected')]
  for label,req,status in rejected:
   def check(obs,status=status):
    p=strict_worker(obs);require(p['status']==status and p['result'] is None and type(p['error']) is dict,'rejection status')
   dispatch('reject_'+label,req,check)
  obj=json.loads(good);obj['nodes']=[['div','bins','c0'] for _ in range(64)];obj['return_node']=0
  largest=json.dumps(obj,separators=(',',':'))
  def maxeval(obs):
   p=strict_worker(obs,largest);r=p['result'];require(p['status']=='completed_finite' and p['error'] is None and r['shape']==[10000] and r['dtype']=='float64' and r['scores'] is None and r['first_argmax']==0 and len(r['node_trace'])==64 and p['work_units']==640000 and p['warnings']['complete'],'max eval envelope')
  dispatch('maximum_vector',{'mode':'evaluate','program_json':largest,'item':1,'bins':[500]*10000},maxeval)
  def maxpack(obs):
   p=strict_worker(obs,largest);r=p['result'];require(p['status']=='packing_returned' and p['error'] is None and p['work_units']==4259840 and r['assignment']==list(range(256)) and p['warnings']['complete'],'max pack envelope');check_assignment([1]*256,500,r['assignment'],r['used_bins'],r['residuals'])
  dispatch('maximum_packing_work',{'mode':'pack','program_json':largest,'items':[1]*256,'capacity':500},maxpack)
  obj['constants']=[{'type':'f64','value':-1},{'type':'f64','value':1}];obj['nodes']=[['sqrt','c0'] for _ in range(63)]+[['div','bins','c1']];obj['return_node']=63
  diagnostics=json.dumps(obj,separators=(',',':'))
  def diagcheck(obs):
   p=strict_worker(obs,diagnostics);require(p['status']=='diagnostic_unresolved' and p['result'] is None and p['error']['type']=='DiagnosticLimit' and p['warnings']['complete'] is False and len(p['warnings']['events'])==12000 and p['warnings']['incomplete_reason']=='warning event bound' and p['work_units']==3169792,'default diagnostic cap')
  dispatch('maximum_warning_transport',{'mode':'pack','program_json':diagnostics,'items':[1]*256,'capacity':500},diagcheck)
  for mode in ['stdout_bound','stderr_bound','eof_hang','malformed','duplicate','nonfinite','nonzero']:
   def check(obs,mode=mode):
    require(obs['reaped'] and obs['cpu_evidence_complete'],'fault must reap')
    if mode=='stdout_bound':require(obs['termination']=='output_limit' and obs['raw_output_bytes']==400001,'stdout cap')
    elif mode=='stderr_bound':require(obs['termination']=='stderr_limit' and obs['stderr_bytes']==16385,'stderr cap')
    elif mode=='eof_hang':require(obs['termination'] in {'wall_timeout','wall_timeout_after_eof'},'EOF hanging worker timeout')
    elif mode=='nonzero':require(obs['returncode']==3 and 'result' not in obs,'nonzero cannot pass')
    else:require(type(obs['error']) is str and obs['error'].startswith('decode:'),'malformed transport rejected')
   dispatch('fault_'+mode,{},check,[sys.executable,'-I','-B',str(ROOT/'tests/transport_fault.py'),mode],.2 if mode=='eof_hang' else 30)
 except Exception as exc:errors.append(type(exc).__name__+': '+str(exc));traceback.print_exc()
 finally:
  if events is not None:
   try:events.close()
   except Exception as exc:errors.append('event close: '+str(exc))
  try:verify(a.freeze_sha256)
  except Exception as exc:errors.append('final_integrity: '+str(exc))
  cost=snapshot()
  if cost['accounted_cpu_seconds']>CPU_BUDGET or cost['wall_seconds']>WALL_BUDGET:errors.append('observed total budget exceeded')
  summary={'status':'passed' if not errors and all(r['status']=='passed' for r in rows) and len(rows)==38 else 'failed','freeze_sha256':a.freeze_sha256,'rows':rows,'errors':errors,'request_count':sum(r['request_dispatched'] for r in rows),'attempt_rows':len(rows),'distinct_pids':len({r['pid'] for r in rows if r['pid'] is not None}),'all_reaped':all(r['reaped'] for r in rows),'costs':cost,'supervisor_peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'limits':{'per_worker_cpu':20,'per_worker_wall':30,'cleanup':1,'address_space':AS,'stage_observed_cpu':90,'stage_observed_wall':120},'scope':'handwritten test programs only; no model generation/research population/benchmark calls','timing_boundary':'last measured before final summary persistence and console print; outer launch separately timed'}
  try:save(out/'summary.json',summary)
  except Exception as exc:summary['status']='failed';summary['errors'].append('summary persistence: '+str(exc))
  print(json.dumps(summary,allow_nan=False),flush=True)
  if summary['status']!='passed':raise SystemExit(1)
if __name__=='__main__':main()
