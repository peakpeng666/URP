"""Minimal outer accounting wrapper; does not create an approval."""
import argparse,json,pathlib,resource,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parent

def main():
 p=argparse.ArgumentParser();p.add_argument('--freeze-sha256',required=True);p.add_argument('--approval',required=True);a=p.parse_args()
 approval=json.loads(pathlib.Path(a.approval).read_text());run=approval['run_id']
 if not run or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in run):raise ValueError('run_id')
 start=time.monotonic();own=time.process_time();before=resource.getrusage(resource.RUSAGE_CHILDREN)
 cmd=[sys.executable,str(ROOT/'run_pilot.py'),'--freeze-sha256',a.freeze_sha256,'--execute-approved','--approval',str(pathlib.Path(a.approval).resolve())]
 # Existing backend owns cleanup. No timeout which could orphan its server.
 result=subprocess.run(cmd,env=dict(__import__('os').environ,PYTHONDONTWRITEBYTECODE='1'))
 after=resource.getrusage(resource.RUSAGE_CHILDREN);cpu=time.process_time()-own+after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime;wall=time.monotonic()-start
 debit=json.loads((ROOT/'protocol.json').read_text())['aggregate_budgets']['preparation_debit']
 report={'returncode':result.returncode,'outer_cpu_seconds':cpu,'outer_wall_seconds':wall,'charged_cpu_seconds':cpu+debit['cpu_seconds'],'charged_active_wall_seconds':wall+debit['active_wall_seconds'],'within_budget':cpu+debit['cpu_seconds']<=1200 and wall+debit['active_wall_seconds']<=900,'boundary':'Includes driver import, verification, model/worker cleanup and driver terminal report; excludes this small outer accounting write.'}
 out=ROOT/'runs'/run/'outer_accounting.json'
 if out.parent.exists():
  with out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps(report),flush=True)
 if result.returncode or not report['within_budget']:raise SystemExit(1)
if __name__=='__main__':main()
