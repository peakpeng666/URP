"""Saved small handwritten transport/resource checks, never benchmark instances."""
import json,pathlib,resource,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from runtime import AS,request
from checker import check_assignment

def main():
 out=pathlib.Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
 resource.setrlimit(resource.RLIMIT_AS,(AS,AS));resource.setrlimit(resource.RLIMIT_CPU,(300,300))
 start=time.monotonic();cpu=time.process_time();observations=[]
 cases=[([],10,'FF'),([10,10],10,'BF'),([4,8,1],10,'FF'),([4,8,1],10,'BF'),([6,5,4,5],10,'FF'),([6,5,4,5],10,'BF')]
 for i,(items,cap,method) in enumerate(cases):
  obs=request(items,cap,method);obs['input']={'items':items,'capacity':cap,'method':method}
  if obs['returncode']!=0 or obs['error'] or obs['termination'] or not obs['reaped']:raise RuntimeError('handwritten transport')
  r=obs['result'];obs['check']=check_assignment(items,cap,r['assignment'],r['used_bins'],r['residuals']);observations.append(obs)
  (out/f'observation_{i:02d}.json').write_text(json.dumps(obs,indent=2)+'\n')
 cleanup=[]
 for name,code,wall in [('timeout','import time;time.sleep(2)',.1),('eof','import os,time;os.close(1);os.close(2);time.sleep(2)',.1),('output','import os,time;os.write(1,b"x"*500000);time.sleep(2)',30)]:
  obs=request([],10,'FF',command=[sys.executable,'-c',code],wall=wall);obs['handwritten_fault']=name
  (out/f'cleanup_{name}.json').write_text(json.dumps(obs,indent=2)+'\n')
  if not obs['reaped'] or not obs['cpu_evidence_complete']:raise RuntimeError('cleanup evidence')
  cleanup.append(obs)
 summary={'status':'passed','manual_success_workers':len(observations),'manual_fault_workers':len(cleanup),'benchmark_instances_solved':0,'worker_cpu_seconds':sum(o['worker_cpu_seconds'] for o in observations+cleanup),'supervisor_cpu_seconds':time.process_time()-cpu,'wall_seconds':time.monotonic()-start,'peak_worker_rss_kib':max(o['worker_peak_rss_kib'] for o in observations+cleanup),'supervisor_peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'effective_supervisor_limits':{'RLIMIT_AS':list(resource.getrlimit(resource.RLIMIT_AS)),'RLIMIT_CPU':list(resource.getrlimit(resource.RLIMIT_CPU))},'distinct_worker_pids':len({o['pid'] for o in observations+cleanup}),'caveat':'Additional earlier unit-test workers are recorded in unit logs; this is the saved nine-worker validation only.'}
 (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
