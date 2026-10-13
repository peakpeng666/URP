"""Full child-process timing for the explicitly capped independent audit."""
import pathlib,subprocess,resource,time,json,os,sys
A=pathlib.Path(__file__).resolve().parent
before=resource.getrusage(resource.RUSAGE_CHILDREN);wall=time.monotonic()
env=dict(os.environ,OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1')
with (A/'FINAL_MACHINE_CHECKS.log').open('x') as log:r=subprocess.run([sys.executable,str(A/'verify_final_results.py')],stdout=log,stderr=subprocess.STDOUT,env=env)
after=resource.getrusage(resource.RUSAGE_CHILDREN)
out={'exit_code':r.returncode,'cpu_user_seconds':after.ru_utime-before.ru_utime,'cpu_system_seconds':after.ru_stime-before.ru_stime,'cpu_total_seconds':after.ru_utime-before.ru_utime+after.ru_stime-before.ru_stime,'wall_seconds':time.monotonic()-wall,'child_hard_cpu_limit_seconds':60,'single_thread_environment':{k:env[k] for k in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS']},'counts_complete_child_process_and_its_children':True}
(A/'FINAL_AUDIT_PROCESS_RESOURCE.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));sys.exit(r.returncode)
