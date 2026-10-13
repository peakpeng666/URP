"""One-pass subprocess supervisor; external complete-process accounting via wait4."""
import sys,os,json,time,hashlib,resource,signal,subprocess
from pathlib import Path
from datetime import datetime,timezone
P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,value):
    with (P/name).open('x') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
freeze=json.loads((P/'freeze.json').read_text())
for name,digest in freeze['sha256'].items():assert sha(P/name)==digest,name
assert not (P/'run_started.json').exists(),'Refuse second benchmark run'
write('run_started.json',{'at_utc':datetime.now(timezone.utc).isoformat(),'freeze_sha256':sha(P/'freeze.json')})
requests=json.loads((P/'requests.json').read_text())
start=time.perf_counter(); startcpu=time.process_time();records=[];spent=0;stop_reason=None
def child_limit():resource.setrlimit(resource.RLIMIT_CPU,(4,5))
def live_cpu(pid):
    try:
        raw=Path(f'/proc/{pid}/stat').read_text();f=raw[raw.rfind(')')+2:].split()
        return (int(f[11])+int(f[12]))/os.sysconf('SC_CLK_TCK')
    except (FileNotFoundError,ProcessLookupError):return 0
for req in requests:
    if stop_reason is not None:
        records.append({**req,'launched':False,'reason':stop_reason});continue
    if spent+time.process_time()-startcpu>53 or time.perf_counter()-start>112:
        stop_reason='global_budget_reserve_exhausted'
        records.append({**req,'launched':False,'reason':stop_reason});continue
    base=P/'raw'/req['run_id']; w=time.perf_counter();killed=False;kill_reason=None
    with Path(str(base)+'.stdout').open('x') as out,Path(str(base)+'.stderr').open('x') as err:
        proc=subprocess.Popen([sys.executable,'-B',str(P/'worker.py'),json.dumps(req)],stdout=out,stderr=err,
                              preexec_fn=child_limit,cwd=P)
        while True:
            pid,status,usage=os.wait4(proc.pid,os.WNOHANG)
            if pid:break
            observed=time.perf_counter()
            if not killed and (observed-w>6 or observed-start>118 or spent+live_cpu(proc.pid)+time.process_time()-startcpu>58):
                kill_reason='child_wall_limit' if observed-w>6 else 'global_resource_limit'
                os.kill(proc.pid,signal.SIGKILL);killed=True
                if kill_reason=='global_resource_limit':stop_reason=kill_reason
            time.sleep(.01)
    wall=time.perf_counter()-w;returncode=os.waitstatus_to_exitcode(status);proc.returncode=returncode
    cpu=usage.ru_utime+usage.ru_stime;spent+=cpu
    rec={**req,'launched':True,'pid':proc.pid,'returncode':returncode,'wait4_raw_status':status,
         'user_cpu_s':usage.ru_utime,'system_cpu_s':usage.ru_stime,'total_cpu_s':cpu,
         'observed_process_wall_s':wall,'max_rss_kib':usage.ru_maxrss,'watchdog_killed':killed,
         'kill_reason':kill_reason,'reaped':True,'completed_at_utc':datetime.now(timezone.utc).isoformat(),
         'minor_faults':usage.ru_minflt,'major_faults':usage.ru_majflt,'voluntary_context_switches':usage.ru_nvcsw,
         'involuntary_context_switches':usage.ru_nivcsw}
    result_path=Path(str(base)+'.result.json')
    rec['result_exists']=result_path.exists()
    if result_path.exists():
        result=json.loads(result_path.read_text());rec['result_sha256']=sha(result_path)
        rec['startup_serialization_exit_and_unattributed_cpu_s']=cpu-result['internal_before_serialization_cpu_s']
        rec['startup_serialization_exit_and_reap_wall_s']=wall-result['internal_before_serialization_wall_s']
    write('raw/'+req['run_id']+'.resource.json',rec);records.append(rec)
    print(req['run_id'],returncode,round(cpu,4),round(wall,4),'reaped',flush=True)
write('process_resources.json',records)
write('run_resources.json',{'children_cpu_s':spent,'supervisor_internal_cpu_s':time.process_time()-startcpu,
    'observed_batch_wall_s':time.perf_counter()-start,'all18_launched':all(x['launched'] for x in records),
    'all_launched_children_reaped':all(x.get('reaped') for x in records if x['launched']),
    'launched_pids':[x['pid'] for x in records if x['launched']],
    'child_peak_rss_kib_max':max([x.get('max_rss_kib',0) for x in records]),'stop_reason':stop_reason,
    'no_retries':True,'requested_runs':len(requests)})
paths=sorted([p for p in (P/'raw').iterdir() if p.is_file()]+[P/'process_resources.json',P/'run_resources.json',P/'run_started.json'])
write('output_seal.json',{'sealed_at_utc':datetime.now(timezone.utc).isoformat(),'reference_files_opened':0,
    'sha256':{str(p.relative_to(P)):sha(p) for p in paths}})
print('All raw outputs sealed before reference scoring.',flush=True)
