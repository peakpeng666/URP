import copy,hashlib,json,pathlib,sys,tempfile,unittest
from unittest.mock import patch
import io,os
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from runtime import request,AS
from run_batch import execute,validate_approval,claim_approval,finalize_budget
from integrity import verify,digest
class Clock:
 def __init__(self):self.t=0.
 def __call__(self):return self.t
class Operational(unittest.TestCase):
 def make(self):
  slots=[{'id':f'manual{i}','index':i,'instance_id':'micro','items_sha256':'manual','n':3,'capacity':10,'method':'FF','status':'not_run_pending_authorization'} for i in range(3)]
  return slots,{'micro':{'items':[4,8,1]}}
 def fake(self,*args):
  return {'pid':123,'returncode':0,'termination':None,'error':None,'reaped':True,'worker_cpu_seconds':1.,'cpu_evidence_complete':True,'result':{'assignment':[0,1,0],'used_bins':2,'residuals':[5,2,10],'feasible_counts':[3,2,3],'n_bin_feasibility_checks':9,'effective_limits':{'RLIMIT_AS':[AS,AS],'RLIMIT_CPU':[20,20],'RLIMIT_FSIZE':[0,0],'RLIMIT_NOFILE':[32,32]}}}
 def runfake(self,executor=None,check=lambda:None,**kwargs):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'observations').mkdir();slots,ins=self.make()
   return execute(slots,ins,p,check,executor=executor or self.fake,**kwargs)
 def test_manual_worker(self):
  o=request([4,8,1],10,'BF');self.assertIsNone(o['error']);self.assertEqual(o['returncode'],0);self.assertTrue(o['reaped']);self.assertTrue(o['cpu_evidence_complete']);self.assertGreater(o['worker_peak_rss_kib'],0);self.assertEqual(o['result']['assignment'],[0,1,1]);self.assertEqual(o['result']['effective_limits']['RLIMIT_AS'],[AS,AS])
 def test_timeout_cleanup(self):
  o=request([],10,'FF',command=[sys.executable,'-c','import time;time.sleep(2)'],wall=.1);self.assertEqual(o['termination'],'wall_timeout');self.assertTrue(o['reaped'])
 def test_eof_live_cleanup(self):
  o=request([],10,'FF',command=[sys.executable,'-c','import os,time;os.close(1);os.close(2);time.sleep(2)'],wall=.1);self.assertEqual(o['termination'],'wall_timeout_after_eof');self.assertTrue(o['reaped'])
 def test_output_cleanup(self):
  o=request([],10,'FF',command=[sys.executable,'-c','import os,time;os.write(1,b"x"*500000);time.sleep(2)']);self.assertEqual(o['termination'],'output_limit');self.assertTrue(o['reaped'])
 def test_cleanup_kill_error_keeps_evidence(self):
  with patch('runtime.os.killpg',side_effect=OSError('injected kill error')):
   o=request([],10,'FF',command=[sys.executable,'-c','import time;time.sleep(.02)'],wall=.001)
  self.assertTrue(o['reaped']);self.assertIn('injected kill error',o['error']);self.assertTrue(o['cpu_evidence_complete'])
 def test_cleanup_wait_error_keeps_unknown(self):
  original=os.wait4
  with patch('runtime.os.wait4',side_effect=OSError('injected wait error')):
   o=request([],10,'FF',command=[sys.executable,'-c','pass'],wall=.001)
  # Explicit test-fixture cleanup after the injected accounting failure.
  original(o['pid'],0)
  self.assertFalse(o['reaped']);self.assertFalse(o['cpu_evidence_complete']);self.assertIn('injected wait error',o['error'])
 def test_fake_success(self):self.assertEqual(self.runfake()['completed_valid'],3)
 def test_unknown_executor_evidence(self):
  def ex(*args):raise OSError('no returned observation')
  o=self.runfake(executor=ex);self.assertEqual(o['execution_counts']['requests_without_returned_execution_evidence'],1);self.assertFalse(o['cost']['worker_cpu_evidence_complete'])
 def test_cpu_reservation_mid(self):
  o=self.runfake(budget_cpu=20.5);self.assertEqual(o['requests_dispatched'],1);self.assertEqual(o['rows'][1]['status'],'not_run_budget_reservation')
 def test_wall_reservation_mid(self):
  clock=Clock()
  def ex(*args):clock.t+=2;return self.fake(*args)
  o=self.runfake(executor=ex,clock=clock,budget_wall=32);self.assertEqual(o['requests_dispatched'],1)
 def test_integrity_predispatch(self):
  def no():raise ValueError('changed')
  o=self.runfake(check=no);self.assertEqual(o['requests_dispatched'],0);self.assertEqual(o['stop_reason'],'integrity_failure');self.assertEqual(o['execution_counts']['requests_without_returned_execution_evidence'],0);self.assertTrue(o['cost']['worker_cpu_evidence_complete'])
 def test_invalid_assignment_stops(self):
  def ex(*args):o=self.fake(*args);o['result']['assignment']=[0,0,0];return o
  o=self.runfake(executor=ex);self.assertEqual(o['requests_dispatched'],1);self.assertEqual(o['rows'][0]['status'],'failed');self.assertEqual(o['rows'][1]['status'],'not_run_failure')
 def test_nonzero_cannot_pass(self):
  def ex(*args):o=self.fake(*args);o['returncode']=1;return o
  self.assertEqual(self.runfake(executor=ex)['completed_valid'],0)
 def test_observation_persistence_failure_preserves(self):
  import run_batch
  real=run_batch.save
  def fail(path,value):
   if path.parent.name=='observations':raise OSError('injected observation failure')
   return real(path,value)
  with patch('run_batch.save',side_effect=fail):o=self.runfake()
  self.assertEqual(o['requests_dispatched'],1);self.assertEqual(o['rows'][0]['execution']['pid'],123);self.assertEqual(o['rows'][1]['status'],'not_run_failure')
 def test_start_event_failure_no_dispatch(self):
  class Bad(io.StringIO):
   def write(self,value):raise OSError('injected journal failure')
  real=pathlib.Path.open
  def op(path,*a,**k):
   if path.name=='events.jsonl':return Bad()
   return real(path,*a,**k)
  with patch.object(pathlib.Path,'open',op):o=self.runfake()
  self.assertEqual(o['requests_dispatched'],0);self.assertEqual(o['stop_reason'],'persistence_failure')
 def test_checkpoint_failure_preserves(self):
  import run_batch
  real=run_batch.save
  def fail(path,value):
   if path.name=='ledger_checkpoint.json':raise OSError('injected checkpoint failure')
   return real(path,value)
  with patch('run_batch.save',side_effect=fail):o=self.runfake()
  self.assertEqual(o['requests_dispatched'],1);self.assertEqual(o['stop_reason'],'persistence_failure');self.assertEqual(o['rows'][0]['execution']['pid'],123)
 def test_final_integrity_overhead(self):
  c=Clock();calls=[0]
  def check():
   calls[0]+=1
   if calls[0]==4:c.t+=700
  o=self.runfake(check=check,clock=c);self.assertEqual(o['requests_dispatched'],3);self.assertEqual(o['stop_reason'],'observed_budget_exceeded');self.assertFalse(o['certified_complete'])
 def test_final_cpu_overhead(self):
  c=Clock();calls=[0]
  def check():
   calls[0]+=1
   if calls[0]==4:c.t+=400
  o=self.runfake(check=check,cpuclock=c);self.assertEqual(o['stop_reason'],'observed_budget_exceeded')
 def test_whole_stage_invalidates(self):
  o={'stop_reason':None,'certified_complete':True,'groups':[1]};finalize_budget(o,301,601,300,600);self.assertFalse(o['certified_complete']);self.assertEqual(o['groups'],[])
 def test_authorization_exact(self):
  a={'freeze_sha256':'a'*64,'scope':'p3_eoh_2024_data_corrected_ff_bf_v1','max_requests':60,'authorized':True,'run_id':'manual_test'}
  self.assertEqual(validate_approval(json.dumps(a).encode(),'a'*64),a)
  for k,v in [('authorized',False),('freeze_sha256','b'*64),('scope','other'),('max_requests',61)]:
   b=dict(a);b[k]=v
   with self.assertRaises(ValueError):validate_approval(json.dumps(b).encode(),'a'*64)
 def test_single_use(self):
  a={'freeze_sha256':'a'*64,'scope':'p3_eoh_2024_data_corrected_ff_bf_v1','max_requests':60,'authorized':True,'run_id':'manual_test'}
  raw=json.dumps(a).encode()
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);claim_approval(raw,a,p,p/'uses')
   with self.assertRaises(FileExistsError):claim_approval(raw,a,p,p/'uses')
 def test_manifest_replacement(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'freeze.json';p.write_text(json.dumps({'files':[],'python_executable_sha256':digest(sys.executable)}));h=digest(p);verify(p,h)
   p.write_text(json.dumps({'files':[],'python_executable_sha256':digest(sys.executable),'replacement':True}))
   with self.assertRaises(ValueError):verify(p,h)
if __name__=='__main__':unittest.main()
