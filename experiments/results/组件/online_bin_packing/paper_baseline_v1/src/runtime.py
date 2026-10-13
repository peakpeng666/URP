"""Bounded trusted handwritten-baseline workers; no research/plugin execution."""
import hashlib,json,os,pathlib,resource,selectors,signal,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
AS=2*1024**3;CPU=20;WALL=30;CLEANUP=1;OUTPUT=400000
ENV={'PATH':os.path.dirname(sys.executable)+':/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0','LANG':'C.UTF-8'}
def child_limits():
 resource.setrlimit(resource.RLIMIT_AS,(AS,AS));resource.setrlimit(resource.RLIMIT_CPU,(CPU,CPU));resource.setrlimit(resource.RLIMIT_FSIZE,(0,0));resource.setrlimit(resource.RLIMIT_NOFILE,(32,32));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
def limits():return {name:list(resource.getrlimit(getattr(resource,name))) for name in ['RLIMIT_AS','RLIMIT_CPU','RLIMIT_FSIZE','RLIMIT_NOFILE']}
def require_limits():
 expected={'RLIMIT_AS':[AS,AS],'RLIMIT_CPU':[CPU,CPU],'RLIMIT_FSIZE':[0,0],'RLIMIT_NOFILE':[32,32]}
 if limits()!=expected:raise RuntimeError('effective worker limits mismatch')
def worker():
 require_limits()
 from baselines import pack
 raw=sys.stdin.buffer.read(100001)
 if len(raw)>100000:raise ValueError('input bound')
 d=json.loads(raw)
 if set(d)!= {'items','capacity','method'}:raise ValueError('request shape')
 start=time.monotonic();cpu=time.process_time();out=pack(**d)
 out.update({'solver_cpu_seconds':time.process_time()-cpu,'solver_wall_seconds':time.monotonic()-start,'pid':os.getpid(),'effective_limits':limits()})
 payload=json.dumps(out,separators=(',',':'),allow_nan=False).encode()
 if len(payload)>OUTPUT:raise ValueError('output bound')
 sys.stdout.buffer.write(payload);sys.stdout.buffer.flush()

def request(items,capacity,method,command=None,wall=WALL):
 start=time.monotonic();before=resource.getrusage(resource.RUSAGE_CHILDREN);p=None;data=bytearray();termination=None;error=None;reaped=False;usage=None;sel=None
 try:
  p=subprocess.Popen(command or [sys.executable,'-B',str(ROOT/'src/runtime.py'),'--worker'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=ENV,start_new_session=True,preexec_fn=child_limits)
  payload=json.dumps({'items':items,'capacity':capacity,'method':method},separators=(',',':')).encode()
  if len(payload)>100000:raise ValueError('host input bound')
  # <=100k input; worker reads stdin before computation, bounded write under outer deadline via selector.
  os.set_blocking(p.stdin.fileno(),False);os.set_blocking(p.stdout.fileno(),False)
  sel=selectors.DefaultSelector();sel.register(p.stdin,selectors.EVENT_WRITE);sel.register(p.stdout,selectors.EVENT_READ);offset=0
  while sel.get_map():
   remaining=start+wall-time.monotonic()
   if remaining<=0:termination='wall_timeout';break
   for key,mask in sel.select(min(remaining,.05)):
    if key.fileobj is p.stdin:
     n=os.write(p.stdin.fileno(),payload[offset:]);offset+=n
     if offset==len(payload):sel.unregister(p.stdin);p.stdin.close()
    else:
     chunk=os.read(p.stdout.fileno(),min(65536,OUTPUT+1-len(data)))
     if not chunk:sel.unregister(p.stdout);p.stdout.close()
     else:data.extend(chunk)
     if len(data)>OUTPUT:termination='output_limit';break
   if termination:break
  sel.close()
  if termination is None:
   while time.monotonic()<start+wall:
    pid,status,ru=os.wait4(p.pid,os.WNOHANG)
    if pid:
     p.returncode=os.waitstatus_to_exitcode(status);usage=ru;reaped=True;break
    time.sleep(.005)
   if not reaped:termination='wall_timeout_after_eof'
 except Exception as exc:error=type(exc).__name__+': '+str(exc)
 finally:
  cleanup_start=time.monotonic();cleanup_errors=[]
  if sel is not None:
   try:sel.close()
   except Exception as exc:cleanup_errors.append('selector_close: '+str(exc))
  if p is not None and not reaped:
   try:os.killpg(p.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   except Exception as exc:cleanup_errors.append('killpg: '+str(exc))
   try:
    while time.monotonic()-cleanup_start<CLEANUP:
     pid,status,ru=os.wait4(p.pid,os.WNOHANG)
     if pid:
      p.returncode=os.waitstatus_to_exitcode(status);usage=ru;reaped=True;break
     time.sleep(.005)
   except Exception as exc:cleanup_errors.append('wait4: '+str(exc))
   if not reaped:cleanup_errors.append('cleanup_timeout_or_unknown_reaping')
  for f in ([] if p is None else [p.stdin,p.stdout]):
   try:
    if f is not None and not f.closed:f.close()
   except Exception as exc:cleanup_errors.append('pipe_close: '+str(exc))
  if cleanup_errors:error=(error or '')+'; '+'; '.join(cleanup_errors)
  cleanup=time.monotonic()-cleanup_start
 after=resource.getrusage(resource.RUSAGE_CHILDREN)
 observation={'pid':None if p is None else p.pid,'returncode':None if p is None else p.returncode,'termination':termination,'error':error,'reaped':reaped,'wall_seconds':time.monotonic()-start,'cleanup_seconds':cleanup,'worker_cpu_seconds':(usage.ru_utime+usage.ru_stime) if usage is not None else after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,'cpu_evidence_complete':usage is not None,'worker_peak_rss_kib':None if usage is None else usage.ru_maxrss,'raw_output_sha256':hashlib.sha256(data).hexdigest(),'raw_output_bytes':len(data)}
 if p is not None and p.returncode==0 and termination is None and error is None:
  try:
   observation['result']=json.loads(data)
   if type(observation['result']) is not dict:raise ValueError('worker response shape')
  except Exception as exc:observation['error']='decode: '+str(exc)
 else:observation['output_preview']=data[:2000].decode(errors='replace')
 return observation
if __name__=='__main__':
 if sys.argv[1:]==['--worker']:worker()
 else:raise SystemExit('Internal worker only')
