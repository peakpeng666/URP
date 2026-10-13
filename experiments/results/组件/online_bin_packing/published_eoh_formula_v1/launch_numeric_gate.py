"""One separately authorized fixed numerical gate, with bounded separate streams."""
import argparse,hashlib,json,os,pathlib,re,resource,selectors,signal,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parent
CAPS={'stdout':400000,'stderr':16384};AS=2147483648

def sha(path):
    h=hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def verify(expected):
    with (ROOT/'static_preparation_freeze.json').open('rb') as f:raw=f.read(1000001)
    if len(raw)>1000000 or hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('freeze mismatch')
    d=json.loads(raw)
    if sys.executable!=d['python_executable'] or str(pathlib.Path(sys.executable).resolve())!=d['python_executable_resolved'] or sys.prefix!=d['python_prefix'] or sys.base_prefix!=d['python_base_prefix'] or sys.exec_prefix!=d['python_exec_prefix'] or sys.base_exec_prefix!=d['python_base_exec_prefix']:raise ValueError('actual interpreter path/prefix mismatch')
    if sha(sys.executable)!=d['python_executable_sha256']:raise ValueError('actual interpreter mismatch')
    for row in d['files']:
        p=ROOT/row['path']
        if p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise ValueError('source mismatch')
    for root,expected_paths in d['runtime_roots'].items():
        r=pathlib.Path(root)
        actual=sorted(str(p.relative_to(r)) for p in r.rglob('*') if p.is_file())
        if actual!=expected_paths:raise ValueError('runtime inventory mismatch')
    for path,row in {**d['runtime_files'],**d['reference_files']}.items():
        p=pathlib.Path(path)
        if p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise ValueError('runtime mismatch')
    return d

def limits():
    for r,v in [(resource.RLIMIT_AS,AS),(resource.RLIMIT_CPU,20),(resource.RLIMIT_FSIZE,0),(resource.RLIMIT_NOFILE,32),(resource.RLIMIT_CORE,0)]:resource.setrlimit(r,(v,v))
def main():
    a=argparse.ArgumentParser();a.add_argument('--approval',required=True);a.add_argument('--freeze-sha256',required=True);a.add_argument('--output',required=True);args=a.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(AS,AS));resource.setrlimit(resource.RLIMIT_CPU,(30,30))
    started=time.monotonic();owncpu=time.process_time();verify(args.freeze_sha256)
    with pathlib.Path(args.approval).open('rb') as f:raw=f.read(10001)
    if len(raw)>10000:raise ValueError('approval bound')
    approval=json.loads(raw)
    if approval.get('scope')!='p3_formula_numeric_gate_only' or approval.get('authorized') is not True or approval.get('freeze_sha256')!=args.freeze_sha256 or not re.fullmatch('[A-Za-z0-9_-]{1,80}',approval.get('run_id','')):raise ValueError('approval mismatch')
    out=pathlib.Path(args.output);out.mkdir(parents=True,exist_ok=False)
    uses=ROOT/'.authorization_uses';uses.mkdir(exist_ok=True)
    with (uses/(approval['run_id']+'.json')).open('x') as f:json.dump({'approval_sha256':hashlib.sha256(raw).hexdigest(),'freeze_sha256':args.freeze_sha256},f)
    env={'PATH':os.path.dirname(sys.executable)+':/usr/bin:/bin','LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0'}
    env.update({k:'1' for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','BLIS_NUM_THREADS','VECLIB_MAXIMUM_THREADS']})
    p=None;sel=None;streams={k:bytearray() for k in CAPS};errors=[];usage=None;rc=None;termination=None;reaped=False;workerstart=None
    try:
        workerstart=time.monotonic()
        p=subprocess.Popen([sys.executable,'-I','-B',str(ROOT/'tests/numeric_gate.py')],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,start_new_session=True,preexec_fn=limits)
        sel=selectors.DefaultSelector()
        for name,pipe in [('stdout',p.stdout),('stderr',p.stderr)]:os.set_blocking(pipe.fileno(),False);sel.register(pipe,selectors.EVENT_READ,name)
        while sel.get_map():
            left=workerstart+30-time.monotonic()
            if left<=0:termination='wall_timeout';break
            for key,_ in sel.select(min(left,.05)):
                name=key.data;data=os.read(key.fileobj.fileno(),min(65536,CAPS[name]+1-len(streams[name])))
                if not data:sel.unregister(key.fileobj);key.fileobj.close()
                else:streams[name].extend(data)
                if len(streams[name])>CAPS[name]:termination=name+'_bound';break
            if termination:break
        if not termination:
            while time.monotonic()<workerstart+30:
                pid,status,usage=os.wait4(p.pid,os.WNOHANG)
                if pid:rc=os.waitstatus_to_exitcode(status);p.returncode=rc;reaped=True;break
                time.sleep(.005)
            if not reaped:termination='wall_timeout_after_eof'
    except Exception as exc:errors.append(type(exc).__name__+': '+str(exc))
    finally:
        cleanup_start=time.monotonic()
        if sel is not None:
            try:sel.close()
            except Exception as exc:errors.append('selector_close: '+str(exc))
        if p is not None and not reaped:
            try:os.killpg(p.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            except Exception as exc:errors.append('killpg: '+str(exc))
            try:
                while time.monotonic()-cleanup_start<1:
                    pid,status,u=os.wait4(p.pid,os.WNOHANG)
                    if pid:usage=u;rc=os.waitstatus_to_exitcode(status);p.returncode=rc;reaped=True;break
                    time.sleep(.005)
            except Exception as exc:errors.append('wait4: '+str(exc))
            if not reaped:errors.append('reaping_unconfirmed')
        if p is not None:
            for pipe in [p.stdout,p.stderr]:
                try:
                    if not pipe.closed:pipe.close()
                except Exception as exc:errors.append('pipe_close: '+str(exc))
        cleanup=time.monotonic()-cleanup_start
    for name,data in streams.items():
        try:(out/(name+'.bin')).write_bytes(data)
        except Exception as exc:errors.append('stream persistence '+name+': '+str(exc)[:2000])
    if streams['stderr']:errors.append('unexpected nonempty stderr; preserved separately')
    try:verify(args.freeze_sha256)
    except Exception as exc:errors.append('final_integrity: '+str(exc))
    decoded=None
    if rc==0 and not termination and not errors and reaped:
        try:
            decoded=json.loads(streams['stdout'])
            if decoded['result']['status']!='passed' or decoded['error'] is not None or not decoded['warnings']['complete']:raise ValueError('gate failed')
            if decoded['pid']!=p.pid or decoded['limits']!={'RLIMIT_AS':[AS,AS],'RLIMIT_CPU':[20,20],'RLIMIT_FSIZE':[0,0],'RLIMIT_NOFILE':[32,32]}:raise ValueError('gate PID/limits mismatch')
            r=decoded['result']
            if r['pair_count']!=45050 or r['denominator_infinite_pairs']!=9550 or r['expected_domain_warning_events']!=100 or r['domain_rejections']!=10 or len(r['item_summaries'])!=100 or len(r['layouts'])!=15:raise ValueError('gate result counts mismatch')
        except Exception as exc:errors.append('gate_response: '+str(exc))
    worker_cpu=None if usage is None or not reaped else usage.ru_utime+usage.ru_stime
    status={'status':'passed' if rc==0 and reaped and not termination and not errors else 'failed','pid':None if p is None else p.pid,'returncode':rc,'termination':termination,'errors':errors,'reaped':reaped,'worker_cpu_seconds':worker_cpu,'worker_cpu_evidence_complete':worker_cpu is not None,'worker_peak_rss_kib':None if usage is None or not reaped else usage.ru_maxrss,'supervisor_cpu_seconds':time.process_time()-owncpu,'wall_seconds':time.monotonic()-started,'cleanup_seconds':cleanup,'streams':{k:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for k,v in streams.items()},'scope':'One fixed handwritten numerical gate only; no benchmark packing or author-byte execution','accounting_note':'Final status write/console output follows this measurement point; all gate costs must be carried into any later stage aggregate.'}
    try:(out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    except Exception as exc:
        status['errors'].append('status persistence: '+str(exc)[:2000]);status['status']='failed'
        status['terminal_fallback']='stdout status; persisted artifacts may be incomplete'
    print(json.dumps(status,indent=2),flush=True)
    if status['status']!='passed':raise SystemExit(1)
if __name__=='__main__':main()
