"""Actual unchanged Budget object with exact current protocol; no model/worker."""
import copy,io,json,pathlib,sys,time,unittest
P=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(P/'src'))
from guard import Budget
PLAN=json.loads((P/'protocol.json').read_text());OLD=json.loads((P.parent/'math_dag_interface_v2/protocol.json').read_text())
class Tests(unittest.TestCase):
 def test_real_clock_model_score_terminal(self):
  b=Budget(PLAN);b.reserve('model');b.reserve('score');mark=b.score_mark();b.score_charge(mark);r=b.terminal();self.assertTrue(r['within_charged_budget']);self.assertGreaterEqual(r['charged_cpu_seconds'],24.103);self.assertGreaterEqual(r['charged_active_wall_seconds'],24.171)
 def test_original_key_bug_reproduced_without_dispatch(self):
  with self.assertRaisesRegex(KeyError,'wall_seconds'):Budget(OLD).reserve('model')
 def test_model_cpu_stop(self):
  v=[0.];b=Budget(PLAN,clock=lambda:0.,own=lambda:v[0],children=lambda:0.);v[0]=975-24.103-40-245+.01
  with self.assertRaisesRegex(RuntimeError,'CPU'):b.reserve('model')
 def test_model_wall_stop(self):
  v=[0.];b=Budget(PLAN,clock=lambda:v[0],own=lambda:0.,children=lambda:0.);v[0]=732-24.171-40-131+.01
  with self.assertRaisesRegex(RuntimeError,'wall'):b.reserve('model')
 def test_score_stage_stop(self):
  b=Budget(PLAN);b.score_cpu=179.
  with self.assertRaisesRegex(RuntimeError,'score stage'):b.reserve('score')
 def test_terminal_overrun(self):
  v=[0.];b=Budget(PLAN,clock=lambda:0.,own=lambda:v[0],children=lambda:0.);v[0]=976.;self.assertFalse(b.terminal()['within_charged_budget'])
 def test_limits_unchanged_only_failure_debited(self):
  a=PLAN['aggregate_budgets'];o=OLD['aggregate_budgets'];self.assertEqual(a['whole_study_observed_cpu_seconds'],o['whole_study_observed_cpu_seconds']);self.assertEqual(a['whole_study_active_wall_seconds'],o['whole_study_active_wall_seconds']);self.assertAlmostEqual(975-a['preparation_debit']['cpu_seconds'],950.897);self.assertAlmostEqual(732-a['preparation_debit']['active_wall_seconds'],707.829)
if __name__=='__main__':
 start=time.monotonic();cpu=time.process_time();s=io.StringIO();r=unittest.TextTestRunner(stream=s,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));text=s.getvalue();print(text)
 report={'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'all_passed':r.wasSuccessful(),'uses_actual_Budget':True,'model_calls':0,'score_worker_calls':0,'cpu_seconds':time.process_time()-cpu,'wall_seconds':time.monotonic()-start,'protocol_file':'protocol.json'}
 with (P/'offline/actual_budget_tests_01.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
 if not r.wasSuccessful():raise SystemExit(1)
