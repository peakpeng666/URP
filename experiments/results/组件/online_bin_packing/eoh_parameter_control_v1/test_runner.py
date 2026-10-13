"""Fake-process control checks; no historical evaluations or workers launched."""
import json,pathlib,subprocess,tempfile,unittest
from unittest.mock import Mock,patch
import run_once as r

class Runner(unittest.TestCase):
    def limits(self):return json.loads(r.FREEZE.read_text())['limits']
    def test_real_budget_keys_and_boundaries(self):
        l=self.limits(); cpu=[0];wall=[0]
        b=r.Budget(l,lambda:cpu[0],lambda:wall[0]);self.assertTrue(b.can_dispatch())
        cpu[0]=l['total_cpu_seconds']-l['preparation_cpu_charge']-l['worker_cpu_seconds']-l['final_reserve_seconds']+0.01
        self.assertFalse(b.can_dispatch())
        cpu[0]=0;wall[0]=l['total_wall_seconds']
        self.assertFalse(b.can_dispatch())
    def test_no_approval_no_dispatch(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'approval.json';p.write_text('{}')
            with patch.object(r.subprocess,'Popen',side_effect=AssertionError('forbidden')) as spawn:
                with self.assertRaises(ValueError):r.main(p)
                spawn.assert_not_called()
    def test_missing_commit_cannot_test(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):r.test_gate(pathlib.Path(d)/'missing',(3,.8,.7),'x')
    def test_commit_exact_binding(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'commit.json';p.write_text(json.dumps({'params':[3,.8,.7],'design_complete':True,'freeze_sha256':'x'}))
            r.test_gate(p,(3,.8,.7),'x')
            with self.assertRaises(ValueError):r.test_gate(p,(2,.8,.7),'x')
            with self.assertRaises(ValueError):r.test_gate(p,(3,.8,.7),'y')
    def test_timeout_kills_group_and_reaps(self):
        p=Mock(pid=123);p.communicate.side_effect=[subprocess.TimeoutExpired('fake',10),(b'partial',b'')]
        with patch.object(r.os,'killpg') as kill:
            self.assertEqual(r.collect(p,10),(b'partial',b'',True))
            kill.assert_called_once_with(123,r.signal.SIGKILL)
            self.assertEqual(p.communicate.call_args_list[-1].kwargs,{'timeout':1})
    def test_budget_exhaustion_dispatches_nothing(self):
        b=Mock();b.can_dispatch.return_value=False
        with patch.object(r.subprocess,'Popen',side_effect=AssertionError('forbidden')) as spawn:
            self.assertEqual(r.dispatch('design',0,0,'unused',b,{}),{'status':'not_run_budget'})
            spawn.assert_not_called()
    def test_sources_match(self):r.verify()

if __name__=='__main__':unittest.main()
