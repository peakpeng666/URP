"""Bounded trusted handwritten-baseline workers; no research/plugin execution."""
import base64,hashlib,json,math,os,pathlib,resource,selectors,signal,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
AS=2*1024**3;CPU=20;WALL=30;CLEANUP=1;OUTPUT=400000;STDERR=16384
ENV={'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','NUMEXPR_NUM_THREADS':'1','BLIS_NUM_THREADS':'1','VECLIB_MAXIMUM_THREADS':'1','PATH':os.path.dirname(sys.executable)+':/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0','LANG':'C.UTF-8'}
def child_limits():
 resource.setrlimit(resource.RLIMIT_AS,(AS,AS));resource.setrlimit(resource.RLIMIT_CPU,(CPU,CPU));resource.setrlimit(resource.RLIMIT_FSIZE,(0,0));resource.setrlimit(resource.RLIMIT_NOFILE,(32,32));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
def limits():return {name:list(resource.getrlimit(getattr(resource,name))) for name in ['RLIMIT_AS','RLIMIT_CPU','RLIMIT_FSIZE','RLIMIT_NOFILE']}
def require_limits():
 expected={'RLIMIT_AS':[AS,AS],'RLIMIT_CPU':[CPU,CPU],'RLIMIT_FSIZE':[0,0],'RLIMIT_NOFILE':[32,32]}
 if limits()!=expected:raise RuntimeError('effective worker limits mismatch')

def strict_json(raw):
 def finite_float(value):
  parsed=float(value)
  if not math.isfinite(parsed):raise ValueError('nonfinite response float')
  return parsed
 def reject_constant(value):raise ValueError('nonstandard JSON constant')
 def no_duplicates(pairs):
  out={}
  for k,v in pairs:
   if k in out:raise ValueError('duplicate JSON key')
   out[k]=v
  return out
 return json.loads(raw,parse_constant=reject_constant,parse_float=finite_float,object_pairs_hook=no_duplicates)

def request(items,capacity,method,command=None,wall=WALL):
 start=time.monotonic();before=resource.getrusage(resource.RUSAGE_CHILDREN);p=None;data=bytearray();stderr=bytearray();termination=None;error=None;reaped=False;usage=None;sel=None
 try:
  p=subprocess.Popen(command or [sys.executable,'-I','-B',str(ROOT/'src/worker.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=ENV,start_new_session=True,preexec_fn=child_limits)
  payload=json.dumps({'items':items,'capacity':capacity,'method':method},separators=(',',':')).encode()
  if len(payload)>100000:raise ValueError('host input bound')
  # <=100k input; worker reads stdin before computation, bounded write under outer deadline via selector.
  os.set_blocking(p.stdin.fileno(),False);os.set_blocking(p.stdout.fileno(),False);os.set_blocking(p.stderr.fileno(),False)
  sel=selectors.DefaultSelector();sel.register(p.stdin,selectors.EVENT_WRITE);sel.register(p.stdout,selectors.EVENT_READ);sel.register(p.stderr,selectors.EVENT_READ);offset=0
  while sel.get_map():
   remaining=start+wall-time.monotonic()
   if remaining<=0:termination='wall_timeout';break
   for key,mask in sel.select(min(remaining,.05)):
    if key.fileobj is p.stdin:
     n=os.write(p.stdin.fileno(),payload[offset:]);offset+=n
     if offset==len(payload):sel.unregister(p.stdin);p.stdin.close()
    else:
     buffer=data if key.fileobj is p.stdout else stderr;cap=OUTPUT if key.fileobj is p.stdout else STDERR
     chunk=os.read(key.fileobj.fileno(),min(65536,cap+1-len(buffer)))
     if not chunk:sel.unregister(key.fileobj);key.fileobj.close()
     else:buffer.extend(chunk)
     if len(buffer)>cap:termination='output_limit' if buffer is data else 'stderr_limit';break
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
  for f in ([] if p is None else [p.stdin,p.stdout,p.stderr]):
   try:
    if f is not None and not f.closed:f.close()
   except Exception as exc:cleanup_errors.append('pipe_close: '+str(exc))
  if cleanup_errors:error=(error or '')+'; '+'; '.join(cleanup_errors)
  cleanup=time.monotonic()-cleanup_start
 after=resource.getrusage(resource.RUSAGE_CHILDREN)
 observation={'pid':None if p is None else p.pid,'returncode':None if p is None else p.returncode,'termination':termination,'error':error,'reaped':reaped,'wall_seconds':time.monotonic()-start,'cleanup_seconds':cleanup,'worker_cpu_seconds':(usage.ru_utime+usage.ru_stime) if usage is not None else after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,'cpu_evidence_complete':usage is not None,'worker_peak_rss_kib':None if usage is None else usage.ru_maxrss,'raw_output_sha256':hashlib.sha256(data).hexdigest(),'raw_output_bytes':len(data),'stderr_bytes':len(stderr),'stderr_sha256':hashlib.sha256(stderr).hexdigest(),'stderr_text':stderr.decode(errors='replace'),'raw_stdout_base64':base64.b64encode(data).decode('ascii'),'raw_stderr_base64':base64.b64encode(stderr).decode('ascii')}
 if stderr:error=(error or '')+'; unexpected nonempty stderr';observation['error']=error
 if p is not None and p.returncode==0 and termination is None and error is None:
  try:
   observation['result']=strict_json(data)
   if type(observation['result']) is not dict:raise ValueError('worker response shape')
   if observation['result'].get('error') is not None or observation['result'].get('warnings',{}).get('complete') is not True:raise ValueError('worker error/incomplete warnings')
  except Exception as exc:observation['error']='decode: '+str(exc)
 else:observation['output_preview']=data[:2000].decode(errors='replace')
 return observation
