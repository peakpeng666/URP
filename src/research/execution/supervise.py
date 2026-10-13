"""One-pass subprocess supervisor; external complete-process accounting via wait4."""
import sys,os,json,time,hashlib,resource,signal,subprocess,ctypes
from pathlib import Path
from datetime import datetime,timezone
P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,value):
    with (P/name).open('x') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def child_limit():resource.setrlimit(resource.RLIMIT_CPU,(4,5))
def live_cpu(pid):
    try:
        raw=Path(f'/proc/{pid}/stat').read_text();f=raw[raw.rfind(')')+2:].split()
        return (int(f[11])+int(f[12]))/os.sysconf('SC_CLK_TCK')
    except (FileNotFoundError,ProcessLookupError):return 0

def enable_subreaper():
    """One-shot Linux CLI only: process-wide subreaper setting, not restored."""
    if not sys.platform.startswith('linux'):
        raise RuntimeError('This supervisor requires Linux wait4 and child-subreaper support')
    libc=ctypes.CDLL(None,use_errno=True)
    if libc.prctl(36,1,0,0,0)!=0:  # PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(),'Cannot enable child subreaper')

def empty_exit_record(proc):
    """Conservative state available before ownership checks or cleanup syscalls."""
    return {'pid':proc.pid,'returncode':proc.returncode,'wait4_raw_status':None,
            'user_cpu_s':0.,'system_cpu_s':0.,'total_cpu_s':0.,'max_rss_kib':0,
            'watchdog_killed':False,'kill_reason':None,'reaped':False,
            'process_group_reaped':False,'usage_complete':False,
            'cleanup_sigterm_sent':False,'cleanup_sigkill_sent':False,
            'cleanup_wall_s':0.,'cleanup_error':None,'adopted_descendants':[],
            'supervisor_error':None,'minor_faults':0,'major_faults':0,
            'voluntary_context_switches':0,'involuntary_context_switches':0,
            'rss_accounting':'maximum collected wait4 peak; not simultaneous tree RSS',
            'live_cpu_accounting':'leader only; descendant usage added after collection'}


def wait_for_worker(proc,limit_reason,*,termination_grace_s=.1,cleanup_timeout_s=2.):
    """Linux one-shot CLI: reap non-escaping members of one private process group.

    enable_subreaper changes the entire calling process and is not restored.
    Call it before Popen(start_new_session=True); no other thread/signal handler
    may reap these children. This is not a long-lived-host embedding interface.
    """
    record=empty_exit_record(proc)
    proc.supervisor_exit_record=record
    collected=[];group_owned=False;complete=False
    failure=None;failure_tb=None;cleanup_failure=None;cleanup_phase=None

    def send_owned(sig):
        # WNOWAIT pins an owned group member across the signal. If none remain,
        # do not signal a group ID that might since have been reused.
        try:
            os.waitid(os.P_PGID,proc.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT)
        except ChildProcessError:return False
        try:os.killpg(proc.pid,sig);return True
        except ProcessLookupError:return False

    def drain(deadline):
        while True:
            # Check even when every wait4 succeeds; ready descendants cannot
            # indefinitely defer SIGKILL escalation or the cleanup deadline.
            if time.monotonic()>=deadline:return False
            try:pid,status,usage=os.wait4(-proc.pid,os.WNOHANG)
            except ChildProcessError:return True
            if pid:
                collected.append((pid,status,usage))
                if pid==proc.pid:proc.returncode=os.waitstatus_to_exitcode(status)
            else:time.sleep(.01)

    try:
        if os.getpgid(proc.pid)!=proc.pid or os.getsid(proc.pid)!=proc.pid:
            raise ValueError('Worker must have its own session and process group')
        group_owned=True
        while True:
            ready=os.waitid(os.P_PID,proc.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT)
            if ready is not None:break
            reason=limit_reason()
            if reason:
                record['watchdog_killed']=True;record['kill_reason']=reason;break
            time.sleep(.01)
    except BaseException as exc:
        failure=exc;failure_tb=exc.__traceback__
        record['supervisor_error']={'type':type(exc).__name__,'message':str(exc)}
    finally:
        cleanup_started=None
        try:
            cleanup_phase='cleanup_start'
            cleanup_started=time.perf_counter()
            if group_owned:
                cleanup_phase='SIGTERM'
                record['cleanup_sigterm_sent']=send_owned(signal.SIGTERM)
                cleanup_phase='TERM_drain'
                complete=drain(time.monotonic()+termination_grace_s)
                if not complete:
                    cleanup_phase='SIGKILL'
                    record['cleanup_sigkill_sent']=send_owned(signal.SIGKILL)
                    cleanup_phase='KILL_drain'
                    complete=drain(time.monotonic()+cleanup_timeout_s)
            else:
                record['cleanup_error']={'type':'OwnershipNotVerified','phase':'validation',
                                         'message':'No process-group signal sent'}
        except BaseException as exc:
            cleanup_failure=exc
            record['cleanup_error']={'type':type(exc).__name__,'message':str(exc),
                                     'phase':cleanup_phase}
        finally:
            # Preserve conservative state and the original chain even if
            # metadata publication itself is interrupted.
            try:
                leader=next((entry for entry in collected if entry[0]==proc.pid),None)
                usages=[entry[2] for entry in collected]
                record.update(returncode=proc.returncode,
                    wait4_raw_status=leader[1] if leader else None,
                    user_cpu_s=sum(u.ru_utime for u in usages),
                    system_cpu_s=sum(u.ru_stime for u in usages),
                    total_cpu_s=sum(u.ru_utime+u.ru_stime for u in usages),
                    max_rss_kib=max((u.ru_maxrss for u in usages),default=0),
                    reaped=leader is not None,process_group_reaped=complete and leader is not None,
                    usage_complete=complete and leader is not None,
                    cleanup_wall_s=time.perf_counter()-cleanup_started if cleanup_started is not None else 0.,
                    adopted_descendants=[{'pid':pid,'returncode':os.waitstatus_to_exitcode(status),
                        'wait4_raw_status':status,'user_cpu_s':usage.ru_utime,
                        'system_cpu_s':usage.ru_stime,'max_rss_kib':usage.ru_maxrss}
                        for pid,status,usage in collected if pid!=proc.pid],
                    minor_faults=sum(u.ru_minflt for u in usages),
                    major_faults=sum(u.ru_majflt for u in usages),
                    voluntary_context_switches=sum(u.ru_nvcsw for u in usages),
                    involuntary_context_switches=sum(u.ru_nivcsw for u in usages))
            except BaseException as exc:
                if cleanup_failure is not None and cleanup_failure is not exc:
                    exc.__cause__=cleanup_failure
                cleanup_failure=exc
                record['cleanup_error']={'type':type(exc).__name__,'message':str(exc),
                                         'phase':'record_update'}
                leader=next((entry for entry in collected if entry[0]==proc.pid),None)
                record.update(returncode=proc.returncode,reaped=leader is not None,
                    wait4_raw_status=leader[1] if leader else None,
                    process_group_reaped=False,usage_complete=False)
    if group_owned and not record['process_group_reaped'] and cleanup_failure is None:
        cleanup_failure=TimeoutError('Worker process-group cleanup incomplete')
        record['cleanup_error']={'type':type(cleanup_failure).__name__,
                                 'message':str(cleanup_failure),'phase':cleanup_phase}
    if failure is not None:
        if cleanup_failure is not None:raise failure.with_traceback(failure_tb) from cleanup_failure
        raise failure.with_traceback(failure_tb)
    if cleanup_failure is not None:raise cleanup_failure
    return record

def main():
    freeze=json.loads((P/'freeze.json').read_text())
    for name,digest in freeze['sha256'].items():assert sha(P/name)==digest,name
    assert not (P/'run_started.json').exists(),'Refuse second benchmark run'
    enable_subreaper()
    write('run_started.json',{'at_utc':datetime.now(timezone.utc).isoformat(),'freeze_sha256':sha(P/'freeze.json')})
    requests=json.loads((P/'requests.json').read_text())
    start=time.perf_counter(); startcpu=time.process_time();records=[];spent=0;stop_reason=None
    for req in requests:
        if stop_reason is not None:
            records.append({**req,'launched':False,'reason':stop_reason});continue
        if spent+time.process_time()-startcpu>53 or time.perf_counter()-start>112:
            stop_reason='global_budget_reserve_exhausted'
            records.append({**req,'launched':False,'reason':stop_reason});continue
        base=P/'raw'/req['run_id']; w=time.perf_counter()
        with Path(str(base)+'.stdout').open('x') as out,Path(str(base)+'.stderr').open('x') as err:
            proc=subprocess.Popen([sys.executable,'-B',str(P/'worker.py'),json.dumps(req)],stdout=out,stderr=err,
                                  preexec_fn=child_limit,cwd=P,start_new_session=True)
            initial_record=empty_exit_record(proc)
            proc.supervisor_exit_record=initial_record
            wait_failure=None;wait_failure_tb=None;result_failure=None
            try:
                def limit_reason():
                    observed=time.perf_counter()
                    if observed-w>6:return 'child_wall_limit'
                    # Live accounting observes the leader, not strict tree CPU.
                    if observed-start>118 or spent+live_cpu(proc.pid)+time.process_time()-startcpu>58:
                        return 'global_resource_limit'
                    return None
                wait_for_worker(proc,limit_reason)
            except BaseException as exc:
                wait_failure=exc;wait_failure_tb=exc.__traceback__
            finally:
                wall=time.perf_counter()-w
                lifecycle=getattr(proc,'supervisor_exit_record',initial_record)
                rec={**req,'launched':True,**lifecycle,
                     'observed_process_wall_s':wall,'completed_at_utc':datetime.now(timezone.utc).isoformat()}
                if wait_failure is not None and rec['supervisor_error'] is None:
                    rec['supervisor_error']={'type':type(wait_failure).__name__,'message':str(wait_failure)}
                spent+=rec['total_cpu_s']
                if rec['kill_reason']=='global_resource_limit':stop_reason=rec['kill_reason']
                result_path=Path(str(base)+'.result.json')
                rec['result_exists']=result_path.exists()
                if result_path.exists():
                    try:
                        result=json.loads(result_path.read_text());rec['result_sha256']=sha(result_path)
                        rec['startup_serialization_exit_and_unattributed_cpu_s']=rec['total_cpu_s']-result['internal_before_serialization_cpu_s']
                        rec['startup_serialization_exit_and_reap_wall_s']=wall-result['internal_before_serialization_wall_s']
                    except Exception as exc:
                        result_failure=exc
                        rec['result_read_error']={'type':type(exc).__name__,'message':str(exc)}
                write('raw/'+req['run_id']+'.resource.json',rec);records.append(rec)
            if wait_failure is not None:raise wait_failure.with_traceback(wait_failure_tb)
            if result_failure is not None:
                raise RuntimeError('Worker result could not be read; exit record preserved') from result_failure
        print(req['run_id'],rec['returncode'],round(rec['total_cpu_s'],4),round(wall,4),'reaped',flush=True)
    write('process_resources.json',records)
    write('run_resources.json',{'children_cpu_s':spent,'supervisor_internal_cpu_s':time.process_time()-startcpu,
        'observed_batch_wall_s':time.perf_counter()-start,'all18_launched':all(x['launched'] for x in records),
        'all_launched_children_reaped':all(x.get('reaped') for x in records if x['launched']),
        'all_launched_process_groups_reaped':all(x.get('process_group_reaped') for x in records if x['launched']),
        'launched_pids':[x['pid'] for x in records if x['launched']],
        'child_peak_rss_kib_max':max([x.get('max_rss_kib',0) for x in records]),'stop_reason':stop_reason,
        'no_retries':True,'requested_runs':len(requests)})
    paths=sorted([p for p in (P/'raw').iterdir() if p.is_file()]+[P/'process_resources.json',P/'run_resources.json',P/'run_started.json'])
    write('output_seal.json',{'sealed_at_utc':datetime.now(timezone.utc).isoformat(),'reference_files_opened':0,
        'sha256':{str(p.relative_to(P)):sha(p) for p in paths}})
    print('All raw outputs sealed before reference scoring.',flush=True)

if __name__=='__main__':main()
