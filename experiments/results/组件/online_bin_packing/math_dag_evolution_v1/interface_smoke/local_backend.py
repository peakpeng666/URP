"""Import-safe local single-slot transport. Single fixed-data interface smoke; no fitness or candidate design calls.
No tools execute from model output. No inference occurs on import.
"""
import datetime,hashlib,json,os,resource,signal,threading,time,urllib.request,urllib.error
from pathlib import Path

def collect_http_response(r, body_path):
 """Read-only transport capture; supplied response may be an offline test fixture."""
 metadata={'status':r.status if hasattr(r,'status') else r.code,'headers':list(r.headers.items()),'body_bytes':0}
 try:
  lengths=r.headers.get_all('Content-Length',[])
  expected=None
  if len(lengths)!=1 or not lengths[0].isascii() or not lengths[0].isdigit():
   metadata['error']='missing_or_invalid_content_length'
  else:expected=int(lengths[0])
  with body_path.open('xb') as saved:
   while True:
    chunk=r.read1(min(65536,1048577-metadata['body_bytes']))
    if not chunk:break
    saved.write(chunk);saved.flush();metadata['body_bytes']+=len(chunk)
    if metadata['body_bytes']>1048576:
     metadata['error']='response_too_large';break
  if expected is not None and metadata['body_bytes']!=expected:
   metadata['error']='content_length_mismatch'
  if expected is not None:metadata['declared_content_length']=expected
 except BaseException as e:
  metadata.update(error=repr(e),error_type=type(e).__name__,access_denied=isinstance(e,PermissionError) or isinstance(getattr(e,'reason',None),PermissionError))
 return metadata

def run_once(slot_index, request_bytes, output_directory):
 H=Path(__file__).resolve().parent;B=H
 D=Path(output_directory).resolve()
 if not D.is_relative_to(H/'runs'):raise ValueError('output_outside_formal_runs')
 D.mkdir(parents=True,exist_ok=False)
 plan=json.loads((H/'protocol.json').read_text());proposal={'command':plan['command'],'endpoint':plan['endpoint'],'limits':plan['limits']}
 cmd=proposal['command'];request=request_bytes
 model=plan['model']
 def sha(p):
  h=hashlib.sha256()
  with p.open('rb') as f:
   for c in iter(lambda:f.read(4*1024**2),b''):h.update(c)
  return h.hexdigest()
 def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
 mem={s.split(':')[0]:int(s.split()[1])*1024 for s in Path('/proc/meminfo').read_text().splitlines()}
 if mem['MemAvailable']<5*1024**3:raise RuntimeError('less_than_5GiB_available_no_launch')
 environment={'PATH':'/usr/bin:/bin','HOME':str(D),'LANG':'C.UTF-8','OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2','HF_HUB_OFFLINE':'1','DO_NOT_TRACK':'1'}
 (D/'request.json').write_bytes(request)
 freeze={'frozen_utc':utc(),'purpose':'nonscored_fixed_dag_schema_smoke','command':cmd,'environment':environment,'endpoint':proposal['endpoint'],'request_sha256':sha(D/'request.json'),'model':model,'asset_verification':'owned by batch preflight and postflight; no per-slot full-weight rehash','limits':proposal['limits'],'memory_before':mem,'context':'new server process and fresh KV; OS page cache may be warm','slot_index':slot_index}
 (D/'run_freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
 out=(D/'server_stdout.log').open('xb');err=(D/'server_stderr.log').open('xb');started=utc();start=time.monotonic();deadline=start+120
 pid=os.fork()
 if pid==0:
  try:
   os.setsid();os.chdir(D)
   for res,limit in [(resource.RLIMIT_AS,4*1024**3),(resource.RLIMIT_CPU,240),(resource.RLIMIT_CORE,0),(resource.RLIMIT_FSIZE,1048576)]:resource.setrlimit(res,(limit,limit))
   null=os.open('/dev/null',os.O_RDONLY);os.dup2(null,0);os.dup2(out.fileno(),1);os.dup2(err.fileno(),2);os.execve(cmd[0],cmd,environment)
  except BaseException as exc:os.write(2,repr(exc).encode());os._exit(127)
 out.close();err.close()
 class NoRedirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,*args,**kwargs):return None
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
 peak=0;samples=0;termination=None;ready_at=None;post_started=None;post_finished=None;post_thread=None;response={};health=[];signals=[];reaped=None
 
 def capture_response(r):
  response.update(collect_http_response(r,D/'response_body.json'))
 def post_once():
  nonlocal post_finished
  try:
   req=urllib.request.Request(proposal['endpoint'],data=request,headers={'Content-Type':'application/json'},method='POST')
   with opener.open(req,timeout=max(.1,deadline-time.monotonic())) as r:capture_response(r)
  except urllib.error.HTTPError as e:
   try:capture_response(e)
   except BaseException as inner:response['body_read_error']=repr(inner)
   response.update(error='http_error',error_type=type(e).__name__)
  except BaseException as e:response.update(error=repr(e),error_type=type(e).__name__,access_denied=isinstance(e,PermissionError) or isinstance(getattr(e,'reason',None),PermissionError))
  post_finished=time.monotonic()

 next_health=start
 try:
  while reaped is None:
   done,status,usage=os.wait4(pid,os.WNOHANG)
   if done:reaped=(status,usage);break
   now=time.monotonic()
   try:
    for line in Path(f'/proc/{pid}/status').read_text().splitlines():
     if line.startswith('VmRSS:'):peak=max(peak,int(line.split()[1])*1024);samples+=1
   except FileNotFoundError:pass
   if termination is None and (now>=deadline or peak>4*1024**3):
    termination='whole_lifetime_timeout' if now>=deadline else 'sampled_rss_limit';os.killpg(pid,signal.SIGKILL);signals.append({'signal':'SIGKILL','seconds':now-start,'reason':termination})
   if termination is None and ready_at is None and now>=next_health:
    try:
     with opener.open('http://127.0.0.1:18091/health',timeout=.2) as r:
      body=r.read(4096);health.append({'seconds':now-start,'status':r.status,'body':body.decode('utf-8','replace')})
      if r.status==200 and json.loads(body)=={'status':'ok'} and 'listening on http://127.0.0.1:18091' in (D/'server_stderr.log').read_text():ready_at=time.monotonic()
    except (OSError,ValueError,urllib.error.URLError) as e:
     health.append({'seconds':now-start,'error':str(e)[:300]})
     if isinstance(e,PermissionError) or isinstance(getattr(e,'reason',None),PermissionError):raise PermissionError('loopback_access_denied_stop')
    next_health=time.monotonic()+.1
   if termination is None and ready_at is not None and post_thread is None:
    post_started=time.monotonic();post_thread=threading.Thread(target=post_once,daemon=True);post_thread.start()
   if termination is None and post_finished is not None:
    termination='single_request_finished_shutdown';os.killpg(pid,signal.SIGTERM);signals.append({'signal':'SIGTERM','seconds':time.monotonic()-start,'reason':termination})
   # If graceful shutdown stalls, ensure the full lifetime remains bounded.
   if termination is not None and signals and signals[-1]['signal']=='SIGTERM' and (now-signals[-1]['seconds']-start>=2 or now>=deadline):
    os.killpg(pid,signal.SIGKILL);signals.append({'signal':'SIGKILL','seconds':now-start,'reason':'shutdown_cleanup_deadline'})
   time.sleep(.05)
 except BaseException as exc:
  termination='supervisor_exception:'+type(exc).__name__
  try:os.killpg(pid,signal.SIGKILL)
  except ProcessLookupError:pass
  if reaped is None:
   _,status,usage=os.wait4(pid,0);reaped=(status,usage)
  signals.append({'signal':'SIGKILL','seconds':time.monotonic()-start,'reason':termination})
 wall=time.monotonic()-start;status,usage=reaped
 if post_thread is not None:post_thread.join(timeout=.2)
 http_thread_finished=post_thread is None or not post_thread.is_alive()
 (D/'response_metadata.json').write_text(json.dumps(response,indent=2)+'\n');(D/'health_readiness.json').write_text(json.dumps(health,indent=2)+'\n')
 metadata={};bodypath=D/'response_body.json'
 if bodypath.exists() and http_thread_finished:
  try:
   data=json.loads(bodypath.read_bytes());content=data.get('content') if type(data)is dict else None
   if type(content)is str:(D/'content.txt').write_bytes(content.encode('utf-8'))
  except (ValueError,TypeError):pass
 process_status='completed' if post_finished is not None and response.get('status')==200 and not response.get('error') and os.waitstatus_to_exitcode(status)==0 else 'http_error'
 if termination=='whole_lifetime_timeout':process_status='startup_timeout' if post_thread is None else 'timeout'
 elif termination=='sampled_rss_limit':process_status='resource_limit'
 elif ready_at is None or os.waitstatus_to_exitcode(status)!=0:process_status='server_error'
 elif (termination or '').startswith('supervisor_exception'):process_status='supervisor_error'
 elif response.get('access_denied'):process_status='access_denied'
 if not http_thread_finished:process_status='incomplete_transport'
 report={'slot_index':slot_index,'process_status':process_status,'http_post_thread_finished':http_thread_finished,'started_utc':started,'finished_utc':utc(),'whole_process_lifetime_wall_seconds':wall,'startup_to_health_ready_seconds':ready_at-start if ready_at else None,'request_wall_seconds':post_finished-post_started if post_finished and post_started else None,'post_requests_sent':int(post_thread is not None),'server_exit_code':os.waitstatus_to_exitcode(status),'termination':termination,'cleanup':{'direct_child_reaped':True,'signals':signals,'server_process_group_was_targeted':bool(signals)},'child_user_cpu_seconds':usage.ru_utime,'child_system_cpu_seconds':usage.ru_stime,'child_ru_maxrss_bytes':usage.ru_maxrss*1024,'sampled_rss_peak_bytes':peak,'rss_samples':samples,'limits_semantics':'RLIMIT_AS hard virtual address space; RSS threshold sampled, not hard RSS isolation; parent HTTP client memory is outside child AS limit','http_status':response.get('status'),'raw_response_sha256':sha(bodypath) if bodypath.exists() and http_thread_finished else None,'content_sha256':sha(D/'content.txt') if (D/'content.txt').exists() else None,'asset_hash_validation':'batch_pre_and_post_only','freeze_sha256':sha(D/'run_freeze.json')}
 (D/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 return report
