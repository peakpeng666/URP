"""Outer process accounting, does not inspect or change scientific decisions."""
import sys,pathlib,subprocess,resource,time,json,os
H=pathlib.Path(__file__).resolve().parent
stage=sys.argv[1];command=sys.argv[2:];assert stage in ['run','check','check_cached','analyze','report','render'] and command
before=resource.getrusage(resource.RUSAGE_CHILDREN);wall=time.monotonic();start=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
env=dict(os.environ,OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1')
with (H/f'{stage.upper()}.log').open('x') as log:
    result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,env=env)
after=resource.getrusage(resource.RUSAGE_CHILDREN)
record={'stage':stage,'started_utc':start,'command':command,'exit_code':result.returncode,'cpu_user_seconds':after.ru_utime-before.ru_utime,'cpu_system_seconds':after.ru_stime-before.ru_stime,'cpu_total_seconds':after.ru_utime-before.ru_utime+after.ru_stime-before.ru_stime,'wall_seconds':time.monotonic()-wall,'max_rss_kb':after.ru_maxrss,'counts_entire_child_process_and_its_children':True}
with (H/f'{stage.upper()}_PROCESS_RESOURCE.json').open('x') as f:json.dump(record,f,ensure_ascii=False,indent=2)
print(json.dumps(record,ensure_ascii=False));sys.exit(result.returncode)
