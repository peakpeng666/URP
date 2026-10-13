"""Shared forward CPU pool for report/render/package, including subprocesses."""
import os,sys,pathlib,json,resource,subprocess,time,signal,math
H=pathlib.Path(__file__).resolve().parent;stage=sys.argv[1];command=sys.argv[2:]
assert stage in ['report','report_r2','report_r3','report_r4','plot_fix','plot_fix_r2','plot_fix_r3','render','render_r2','render_r3','package'] and command
past=[json.loads(p.read_bytes()) for p in H.glob('ARTIFACT_*_RESOURCE.json')]
used=sum(x['accounted_cpu_seconds'] for x in past);allowance=20-used
assert allowance>1,('artifact CPU pool exhausted',used)
ticks=os.sysconf('SC_CLK_TCK');cpu0=time.process_time();usage0=resource.getrusage(resource.RUSAGE_CHILDREN);wall=time.monotonic()
def limit():resource.setrlimit(resource.RLIMIT_CPU,(int(math.ceil(allowance)),int(math.ceil(allowance))))
def tree_cpu(root):
    infos={}
    for p in pathlib.Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            a=(p/'stat').read_text().rsplit(')',1)[1].split();infos[int(p.name)]=(int(a[1]),sum(int(a[j]) for j in [11,12,13,14])/ticks)
        except (OSError,ValueError,IndexError):pass
    ids={root};changed=True
    while changed:
        new={pid for pid,(ppid,c) in infos.items() if ppid in ids};changed=bool(new-ids);ids|=new
    return sum(infos[pid][1] for pid in ids if pid in infos)
env=dict(os.environ,OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1')
killed=False
with (H/f'ARTIFACT_{stage.upper()}.log').open('x') as log:
    proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True,preexec_fn=limit)
    while proc.poll() is None:
        if tree_cpu(proc.pid)+(time.process_time()-cpu0)>=allowance-.35 or time.monotonic()-wall>120:
            os.killpg(proc.pid,signal.SIGKILL);killed=True;break
        time.sleep(.05)
    code=proc.wait()
after=resource.getrusage(resource.RUSAGE_CHILDREN);child=after.ru_utime+after.ru_stime-usage0.ru_utime-usage0.ru_stime;wrapper=time.process_time()-cpu0
r={'stage':stage,'command':command,'exit_code':code,'killed_by_pool_guard':killed,'shared_pool_limit_seconds':20,'previous_spend_seconds':used,'this_stage_allowance_seconds':allowance,'child_cpu_seconds':child,'wrapper_cpu_seconds':wrapper,'accounted_cpu_seconds':child+wrapper,'wall_seconds':time.monotonic()-wall,'single_thread_environment':True,'guard':'Descendant /proc CPU watchdog with0.35s margin plus inherited per-process RLIMIT_CPU; final RUSAGE_CHILDREN includes reaped descendants.'}
with (H/f'ARTIFACT_{stage.upper()}_RESOURCE.json').open('x') as f:json.dump(r,f,ensure_ascii=False,indent=2)
print(json.dumps(r,ensure_ascii=False));assert child+wrapper<=allowance,(child+wrapper,allowance);sys.exit(code)
