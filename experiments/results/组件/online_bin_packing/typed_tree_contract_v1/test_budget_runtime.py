"""Actual pilot Budget and actual reused cleanup, no inference."""
import importlib.util,json,pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from guard import Budget
PLAN=json.loads((ROOT/'protocol.json').read_text())
class BudgetTests(unittest.TestCase):
 def test_current_keys_real_clock(self):
  b=Budget(PLAN);b.reserve('model');b.reserve('score');m=b.score_mark();b.score_charge(m);r=b.terminal()
  self.assertTrue(r['within_charged_budget']);self.assertGreaterEqual(r['charged_cpu_seconds'],100);self.assertGreaterEqual(r['charged_active_wall_seconds'],100)
 def test_exact_cpu_boundary(self):
  v=[0.];b=Budget(PLAN,clock=lambda:0.,own=lambda:v[0],children=lambda:0.)
  v[0]=1200-100-245-40;b.reserve('model');v[0]+=.001
  with self.assertRaisesRegex(RuntimeError,'CPU'):b.reserve('model')
 def test_exact_wall_boundary(self):
  v=[0.];b=Budget(PLAN,clock=lambda:v[0],own=lambda:0.,children=lambda:0.)
  v[0]=900-100-131-40;b.reserve('model');v[0]+=.001
  with self.assertRaisesRegex(RuntimeError,'wall'):b.reserve('model')
 def test_score_stage_boundary(self):
  b=Budget(PLAN);b.score_cpu=220;b.score_wall=341;b.reserve('score');b.score_cpu+=.001
  with self.assertRaisesRegex(RuntimeError,'score stage'):b.reserve('score')
 def test_terminal_overrun(self):
  v=[0.];b=Budget(PLAN,clock=lambda:0.,own=lambda:v[0],children=lambda:0.);v[0]=1100.001
  self.assertFalse(b.terminal()['within_charged_budget'])
 def test_legacy_miskey_is_not_accepted(self):
  p=json.loads(json.dumps(PLAN));p['aggregate_budgets']['final_accounting_reserve']['active_wall_seconds']=p['aggregate_budgets']['final_accounting_reserve'].pop('wall_seconds')
  with self.assertRaises(KeyError):Budget(p).reserve('model')
 def test_cleanup_on_real_sleep_process(self):
  spec=importlib.util.spec_from_file_location('pilot_tokenizer',ROOT/'transport/tokenizer_runtime.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  r=m.request(['/usr/bin/sleep','5'],wall=.05)
  self.assertEqual(r['termination'],'wall_timeout');self.assertTrue(r['reaped']);self.assertTrue(r['cpu_evidence_complete']);self.assertLess(r['wall_seconds'],2)
 def test_backend_early_deadline_and_postcheck_source(self):
  # Static wiring check; not claimed to exercise inference process timeout.
  s=(ROOT/'transport/backend.py').read_text();self.assertIn('deadline=lifecycle_start+118',s);self.assertIn("report['run_once_lifecycle_wall_seconds']>120",s)
if __name__=='__main__':unittest.main(verbosity=2)
