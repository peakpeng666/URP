import json
from pathlib import Path
import time
import unittest
from urp_cvrp.budget import BudgetExceeded
from urp_cvrp.generate import generate_instance
from urp_cvrp.checker import check_solution
from mature_pyvrp_v1.adapter import CPUIterationStop,prepare,solve
from scale_budget_v1.runtime import MarginBudget,run
from scale_budget_v1.experiment import summarize,evaluate

CONFIG=json.loads((Path(__file__).parent/'protocol.json').read_text())


class ScaleTests(unittest.TestCase):
    def test_margin_applied_once_and_same_trigger(self):
        cfg={**CONFIG,**CONFIG['profiles']['cpu025']}
        budget=MarginBudget(0.25,1.0,0.02)
        self.assertEqual(budget.cpu_seconds,0.25)
        budget.start_cpu=time.process_time()-0.229
        self.assertFalse(CPUIterationStop(budget,cfg)(0))
        budget.start_cpu=time.process_time()-0.231
        self.assertTrue(CPUIterationStop(budget,cfg)(0))
        with self.assertRaises(BudgetExceeded):budget.check()

    def test_interrupted_vnd_returns_complete_incumbent(self):
        instance=generate_instance(100,'uniform',2026100611)
        class CountBudget:
            def __init__(self):self.calls=0
            def check(self):
                self.calls+=1
                if self.calls>3000:raise BudgetExceeded('injected_checkpoint_stop')
        out=solve(instance,'multistart_vnd',11,CountBudget(),CONFIG)
        checked=check_solution(instance,out)
        self.assertTrue(checked.accepted,checked.errors)
        self.assertEqual(out['search']['termination'],'injected_checkpoint_stop')

    def test_interrupt_immediately_after_improved_checkpoint(self):
        from unittest.mock import patch
        from urp_cvrp.budget import Budget
        import local_search_v2.solvers as local
        instance=generate_instance(100,'uniform',2026100611)
        original=local.SearchState.observe
        def stop_after_save(state,routes,distances):
            original(state,routes,distances)
            if state.accepted_moves>0:
                raise BudgetExceeded('injected_after_improved_checkpoint')
        with patch.object(local.SearchState,'observe',stop_after_save):
            out=solve(instance,'multistart_vnd',11,Budget(5,5),CONFIG)
        self.assertTrue(check_solution(instance,out).accepted)
        self.assertGreater(out['search']['accepted_moves'],0)
        self.assertEqual(out['search']['termination'],'injected_after_improved_checkpoint')

    def test_pre_first_callback_pyvrp_stop_retains_feasible_complete_output(self):
        prepare('pyvrp_ils_s1e6')
        instance=generate_instance(50,'uniform',2026100620)
        budget=MarginBudget(0.25,1,0.02);budget.start_cpu=time.process_time()-0.24
        out=solve(instance,'pyvrp_ils_s1e6',11,budget,{**CONFIG,**CONFIG['profiles']['cpu025']})
        self.assertTrue(check_solution(instance,out).accepted)
        self.assertEqual(out['search']['termination'],'cpu_return_margin')
        self.assertEqual(out['search']['iterations'],0)

    def test_each_size_has_full_feasible_checkpoint_under_short_budget(self):
        # Test seeds are outside the 24 study instances and final namespace.
        for n in (50,100,200):
            instance=generate_instance(n,'uniform',2026100600+n)
            for method in CONFIG['algorithms']:
                rec=evaluate(instance,method,11,'cpu025',CONFIG,0)
                self.assertTrue(rec['accepted'],(n,method,rec))
                self.assertTrue(rec['budget_conformant'],(n,method,rec.get('solver_cpu_seconds')))
                self.assertTrue(check_solution(instance,rec['output']).accepted)
                self.assertGreaterEqual(rec['child_total_cpu_seconds'],rec['solver_cpu_seconds'])

    def test_raised_limits_and_fixed_families(self):
        self.assertEqual(CONFIG['move_evaluation_limit'],10000000)
        self.assertEqual(CONFIG['pyvrp_iterations'],1000000)
        self.assertEqual(CONFIG['multistart_count'],12)
        self.assertEqual(len(CONFIG['algorithms']),3)
        self.assertEqual(CONFIG['common_cpu_return_margin_seconds'],CONFIG['pyvrp_cpu_return_margin_seconds'])

    def test_nonconformance_stays_visible_and_excluded_explicitly(self):
        # Construct diagnostic rows only; never insert them in experiment files.
        rows=[]
        for method in CONFIG['algorithms']:
            for profile in CONFIG['profiles']:
                for seed in CONFIG['solver_seeds']:
                    rows.append({'instance_id':'unit','family':'uniform','n_customers':50,
                      'algorithm':method,'profile':profile,'solver_seed':seed,'accepted':True,'scoreable':True,
                      'status':'returned','search':{},'recomputed_cost':100,'solver_cpu_seconds':0.1,
                      'child_total_cpu_seconds':0.2,'total_wall_seconds':0.21,'child_peak_rss_kib':1,'solver_cpu_overrun_seconds':0})
        rows[0]['scoreable']=False;rows[0]['solver_cpu_overrun_seconds']=0.001
        report=summarize(rows,CONFIG)
        self.assertEqual(report['accepted'],18);self.assertEqual(report['in_budget_accepted'],17)
        self.assertEqual(report['comparisons']['cpu025__multistart_vnd_vs_parallel_savings']['paired_instances'],0)
        self.assertEqual(report['comparisons']['cpu025__multistart_vnd_vs_parallel_savings']['excluded_incomplete_or_nonconformant_instances'],['unit'])


if __name__=='__main__':unittest.main(verbosity=2)
