"""Cohort B native supervisor, separate from frozen cohort A.
Only sanitized problem enters child; evaluation references never sent.
"""
import json,time,subprocess,selectors,os,signal,tempfile,math,resource
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def validate(p,routes,cost):
 seen=[];actual=0
 if len(routes)>p['K']:return False
 for r in routes:
  if len(r)<3 or r[0]!=0 or r[-1]!=0 or 0 in r[1:-1]:return False
  if any(type(i)!=int or not 1<=i<len(p['demands']) for i in r[1:-1]):return False
  if sum(p['demands'][i] for i in r[1:-1])>p['capacity']:return False
  seen+=r[1:-1]
  for a,b in zip(r,r[1:]):
   x,y=p['coordinates'][a],p['coordinates'][b];actual+=math.floor(math.hypot(x[0]-y[0],x[1]-y[1])+0.5)
 return sorted(seen)==list(range(1,len(p['demands']))) and actual==cost

def vrp(p):
 lines=['NAME : sanitized','TYPE : CVRP',f'DIMENSION : {len(p["demands"])}','EDGE_WEIGHT_TYPE : EUC_2D',f'CAPACITY : {p["capacity"]}','NODE_COORD_SECTION']
 lines += [f'{i+1} {x} {y}' for i,(x,y) in enumerate(p['coordinates'])]
 lines+=['DEMAND_SECTION']+[f'{i+1} {x}' for i,x in enumerate(p['demands'])]+['DEPOT_SECTION','1','-1','EOF']
 return '\n'.join(lines)+'\n'

def run(algorithm,p,budget=5):
 if p['K'] != len(p['demands'])-1:raise ValueError('cohort B original vendors restricted to unrestricted contract')
 with tempfile.TemporaryDirectory(prefix='urp-vendor-') as temp:
  inputpath=Path(temp)/'input.vrp';inputpath.write_text(vrp(p))
  if algorithm=='ails':command=['java','-Xmx512m',f'-Durp.seed={p["seed"]}','-cp',str(ROOT/'ails/classes'),'Adapter.Main',str(inputpath),str(budget)]
  elif algorithm=='sisr':command=[str(ROOT/'sisr/build/sisr_adapter'),str(ROOT/'sisr/cvrp/config.json')]
  else:raise ValueError(algorithm)
  stderr=open(Path(temp)/'stderr','w+')
  usage_before=resource.getrusage(resource.RUSAGE_CHILDREN)
  validation_cpu=0.0
  start=time.monotonic_ns();deadline=start+int(budget*1e9)
  def setup():os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
  proc=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=stderr,start_new_session=True,preexec_fn=setup)
  if algorithm=='sisr':proc.stdin.write(json.dumps({'payload':p,'deadline_ns':deadline}).encode())
  proc.stdin.close();sel=selectors.DefaultSelector();sel.register(proc.stdout,selectors.EVENT_READ);buf=b'';events=[];last=None;invalid=[]
  while time.monotonic_ns()<deadline and sel.get_map():
   for key,_ in sel.select(max(0,min(.1,(deadline-time.monotonic_ns())/1e9))):
    chunk=os.read(key.fileobj.fileno(),65536)
    if not chunk:sel.unregister(key.fileobj);continue
    buf+=chunk
    while b'\n' in buf:
     line,buf=buf.split(b'\n',1);receipt=time.monotonic_ns()
     try:event=json.loads(line)
     except (ValueError,UnicodeDecodeError):continue
     event['receipt_ns']=receipt;event['before_deadline']=receipt<=deadline;events.append(event)
     if event.get('event')=='incumbent' and receipt<=deadline:
      validation_start=time.process_time()
      valid=validate(p,event['routes'],event['cost'])
      validation_cpu+=time.process_time()-validation_start
      if valid:
       if last is None or event['cost']<last['cost']:last=event
      else:invalid.append(event)
  cleanup_started_ns=time.monotonic_ns()
  forced=proc.poll() is None
  if forced:
   try:os.killpg(proc.pid,signal.SIGKILL)
   except ProcessLookupError:pass
  code=proc.wait();stderr.seek(0);err=stderr.read();stderr.close()
  usage_after=resource.getrusage(resource.RUSAGE_CHILDREN)
  termination=('deadline_kill' if cleanup_started_ns>=deadline else 'early_cleanup_kill') if forced and code==-signal.SIGKILL else ('normal_exit' if code==0 else 'native_error_exit')
  return {'cleanup_started_ns':cleanup_started_ns,'termination_status':termination,'validation_cpu_seconds':validation_cpu,'validation_timing_scope':'synchronous supervisor validation within shared elapsed budget; unlike cohortA postcheck','cpu_seconds':usage_after.ru_utime+usage_after.ru_stime-usage_before.ru_utime-usage_before.ru_stime,'algorithm':algorithm,'budget_seconds':budget,'seed':p['seed'],'start_ns':start,'deadline_ns':deadline,'wall_seconds':(time.monotonic_ns()-start)/1e9,'returncode':code,'killed_at_cutoff':forced,'incumbent':last,'invalid_outputs':invalid,'events':events,'stderr':err,'feasible_incumbent':bool(last and not invalid),'status':('VALID_WITH_NATIVE_ERROR' if termination=='native_error_exit' else 'VALID') if last and not invalid else ('INVALID_OUTPUT' if invalid else 'NO_INCUMBENT')}
