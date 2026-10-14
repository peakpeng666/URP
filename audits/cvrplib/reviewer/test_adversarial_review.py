"""Independent review probes; all synthetic, no formal benchmark optimization."""
import unittest, tempfile, json, time
from pathlib import Path
from urp_research.cvrplib.runner import run_payload
from urp_research.cvrplib.io import validate_payload
P={'coordinates':[[0,0],[3,4],[6,8]],'demands':[0,1,1],'capacity':2,'K':1,'algorithm':'TSR','seed':0,'budget_seconds':2}
class AdversarialReview(unittest.TestCase):
 def fault(self,body):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'probe.py';p.write_text('import sys,json,time,os\nr=json.load(sys.stdin)\n'+body)
   out=run_payload(P,worker_path=p)
  logs=Path(__file__).with_name('logs_fixture_v2');logs.mkdir(exist_ok=True)
  (logs/(self._testMethodName+'.json')).write_text(json.dumps(out,indent=2))
  return out
 def test_backdated_result_delivered_after_deadline_is_not_accepted(self):
  r=self.fault('stamp=time.monotonic_ns()\nprint("READY_FOR_DELAY",file=sys.stderr,flush=True)\ntime.sleep(3)\nprint(json.dumps({"event":"incumbent","emitted_ns":stamp,"cost":20,"routes":[[0,1,2,0]]}),flush=True)\n')
  self.assertFalse(r['feasible']);self.assertIsNone(r['cost']);self.assertLess(r['process_wall_seconds'],2.7);self.assertIn('READY_FOR_DELAY',r['raw_stderr'])
 def test_future_timestamp_is_rejected_even_if_received_in_time(self):
  r=self.fault('print(json.dumps({"event":"incumbent","emitted_ns":r["deadline_ns"]+1,"cost":20,"routes":[[0,1,2,0]]}),flush=True)\n')
  self.assertFalse(r['feasible']);self.assertEqual(len(r['late_events_rejected']),1)
 def test_partial_json_never_becomes_incumbent(self):
  r=self.fault('sys.stdout.write("{\\\"event\\\":\\\"incumbent\\\"");sys.stdout.flush()\n')
  self.assertFalse(r['feasible']);self.assertEqual(r['status'],'API_ERROR')
 def test_error_missing_error_type_is_recorded_not_supervisor_crash(self):
  r=self.fault('print(json.dumps({"event":"error","emitted_ns":time.monotonic_ns()}),flush=True)\n')
  self.assertFalse(r['feasible']);self.assertEqual(r['status'],'API_ERROR')
 def test_valid_checkpoint_then_crash_stays_failure(self):
  r=self.fault('print(json.dumps({"event":"incumbent","emitted_ns":time.monotonic_ns(),"cost":20,"routes":[[0,1,2,0]]}),flush=True)\nos._exit(7)\n')
  self.assertFalse(r['feasible']);self.assertEqual(r['status'],'CRASH');self.assertEqual(len(r['checkpoint_checks']),1)
 def test_self_sigkill_after_done_is_not_success(self):
  r=self.fault('print(json.dumps({"event":"incumbent","emitted_ns":time.monotonic_ns(),"cost":20,"routes":[[0,1,2,0]]}),flush=True)\nprint(json.dumps({"event":"done","emitted_ns":time.monotonic_ns()}),flush=True)\nos.kill(os.getpid(),9)\n')
  self.assertFalse(r['feasible']);self.assertEqual(r['status'],'RESOURCE_LIMIT')
 def test_late_event_does_not_hide_real_crash(self):
  r=self.fault('print(json.dumps({"event":"incumbent","emitted_ns":r["deadline_ns"]+1,"cost":20,"routes":[[0,1,2,0]]}),flush=True)\nos._exit(7)\n')
  self.assertFalse(r['feasible']);self.assertEqual(r['status'],'CRASH')
 def test_no_incumbent_done_is_not_mathematical_infeasibility(self):
  r=self.fault('print(json.dumps({"event":"done","emitted_ns":time.monotonic_ns()}),flush=True)\n')
  self.assertFalse(r['feasible']);self.assertEqual(r['status'],'NO_SOLUTION')
 def test_invalid_checkpoint_invalidates_run_under_strict_integrity_policy(self):
  r=self.fault('print(json.dumps({"event":"incumbent","emitted_ns":time.monotonic_ns(),"cost":20,"routes":[[0,1,2,0]]}),flush=True)\nprint(json.dumps({"event":"incumbent","emitted_ns":time.monotonic_ns(),"cost":10,"routes":[[0,1,0]]}),flush=True)\nprint(json.dumps({"event":"done","emitted_ns":time.monotonic_ns()}),flush=True)\n')
  self.assertFalse(r['feasible']);self.assertEqual(r['status'],'INVALID_SOLUTION');self.assertEqual(len(r['checkpoint_checks']),2)
 def test_reference_identifiers_and_manifests_cannot_enter_payload(self):
  for key,val in [('name','A-n32-k5'),('COMMENT','optimal 784'),('reference_path','x.sol'),('manifest',{}),('BKS',784)]:
   with self.subTest(key=key),self.assertRaises(ValueError):validate_payload({**P,key:val})

class SavedScoreReview(unittest.TestCase):
 def score(self, mutate):
  from urp_research.cvrplib.evaluate import evaluate_saved
  from urp_research.cvrplib.io import sha,digest,parse_vrp
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)
   vrp=root/'fixture.vrp';vrp.write_text('NAME : fixture\nTYPE : CVRP\nDIMENSION : 3\nEDGE_WEIGHT_TYPE : EUC_2D\nCAPACITY : 2\nNODE_COORD_SECTION\n1 0 0\n2 3 4\n3 6 8\nDEMAND_SECTION\n1 0\n2 1\n3 1\nDEPOT_SECTION\n1\n-1\nEOF\n')
   sol=root/'fixture.sol';sol.write_text('Route #1: 1 2\nCost 20\n')
   c={'case_id':'fixture','instance_path':'fixture.vrp','instance_sha256':sha(vrp),'source_family':'A','k_name_metadata':1,'contract':{'eligible':True,'id':'test-fixed-K','vehicle_limit':1},'reference':{'path':'fixture.sol','sha256':sha(sol),'label':'synthetic test oracle'}}
   m=root/'manifest.json';m.write_text(json.dumps({'cases':[c]}))
   prob=parse_vrp(vrp.read_text());p={k:prob[k] for k in ('coordinates','demands','capacity')};p.update(K=1,algorithm='TSR',seed=0,budget_seconds=1)
   event={'event':'incumbent','cost':20,'routes':[[0,1,2,0]],'emitted_ns':200,'received_ns':300}
   r={'case_id':'fixture','case_manifest_sha256':sha(m),'instance_sha256':sha(vrp),'payload_sha256':digest(p),'algorithm':'TSR','seed':0,'budget_seconds':1,'contract':{'id':'test-fixed-K','K':1,'fixed_cost':0},'start_monotonic_ns':100,'deadline_monotonic_ns':1000000100,'incumbent_emitted_ns':200,'incumbent_received_ns':300,'feasible':True,'status':'OK','routes':[[0,1,2,0]],'cost':20,'events':[event]}
   mutate(r);f=root/'result.json';f.write_text(json.dumps(r));return evaluate_saved(root,m,f)
 def test_valid_saved_evidence_is_eligible(self):self.assertTrue(self.score(lambda r:None)['eligible_for_gap'])
 def test_saved_late_result_cannot_gain_gap(self):
  with self.assertRaises(ValueError):self.score(lambda r:r.update(incumbent_received_ns=r['deadline_monotonic_ns']+1))
 def test_saved_wrong_instance_cannot_gain_gap(self):
  with self.assertRaises(ValueError):self.score(lambda r:r.update(instance_sha256='wrong'))
 def test_saved_wrong_payload_cannot_gain_gap(self):
  with self.assertRaises(ValueError):self.score(lambda r:r.update(payload_sha256='wrong'))
 def test_saved_no_event_cannot_gain_gap(self):
  with self.assertRaises(ValueError):self.score(lambda r:r.update(events=[]))

if __name__=='__main__':unittest.main()
