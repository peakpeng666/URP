import json,math
from pathlib import Path
import unittest
from unittest.mock import patch
from urp_cvrp.budget import Budget
from urp_cvrp.checker import check_solution
from urp_cvrp.generate import generate_instance
from urp_cvrp.instance import from_dict
from urp_cvrp.baselines import savings
from initialization_ablation_v1 import adapter
from initialization_ablation_v1.experiment import instances,evaluate
from mature_pyvrp_v1 import adapter as previous

ROOT=Path(__file__).resolve().parents[1]
CONFIG=json.loads((Path(__file__).parent/'protocol.json').read_text())


class AblationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):adapter.prepare('pyvrp_ils_random')

    def test_public_solution_uses_zero_based_client_indices(self):
        instance=generate_instance(3,'uniform',2026100901)
        model,_,_=adapter.build(instance,1000000);data=model.data();lib=adapter._backend[0]
        initial=lib.Solution(data,[[0],[1],[2]])
        self.assertTrue(initial.is_feasible())
        with self.assertRaises(ValueError):lib.Solution(data,[[1],[2],[3]])

    def test_new_random_public_dispatch_matches_previous_fixed_work(self):
        previous.prepare('pyvrp_ils_s1e6');cfg={**CONFIG,'pyvrp_iterations':40}
        for family in ('uniform','clustered'):
            instance=generate_instance(20,family,2026100902)
            for seed in (11,29,47):
                old=previous.solve(instance,'pyvrp_ils_s1e6',seed,Budget(5,5),cfg)
                new=adapter.solve(instance,'pyvrp_ils_random',seed,Budget(5,5),cfg)
                self.assertEqual(old['routes'],new['routes']);self.assertEqual(old['reported_cost'],new['reported_cost'])

    def test_zero_iteration_returns_validated_warm_incumbent(self):
        instance=generate_instance(50,'uniform',2026100903)
        warm=savings(instance,11,Budget(5,5))
        out=adapter.solve(instance,'pyvrp_ils_savings_warm',11,Budget(5,5),{**CONFIG,'pyvrp_iterations':0})
        self.assertTrue(check_solution(instance,out).accepted)
        self.assertEqual(out['reported_cost'],warm['reported_cost'])
        self.assertEqual(out['routes'],warm['routes'])
        self.assertEqual(out['search']['iterations'],0)
        self.assertEqual(out['search']['integer_cost'],out['search']['warm_start_integer_cost'])

    def test_warm_routes_checked_and_never_worse_in_integer_proxy(self):
        for family in ('uniform','clustered'):
            instance=generate_instance(50,family,2026100904)
            out=adapter.solve(instance,'pyvrp_ils_savings_warm',29,Budget(5,5),{**CONFIG,'pyvrp_iterations':40})
            self.assertTrue(check_solution(instance,out).accepted)
            m=out['search']
            self.assertTrue(check_solution(instance,{'routes':m['warm_start_routes'],'reported_cost':m['warm_start_original_cost']}).accepted)
            self.assertTrue(m['incumbent_not_worse_than_initial_integer_cost'])
            self.assertGreater(m['warm_start_constructor_cpu_seconds'],0)
            self.assertGreater(m['warm_start_independent_validation_cpu_seconds'],0)

    def test_corrupt_warm_start_rejected_before_library(self):
        instance=generate_instance(5,'uniform',2026100905)
        with patch('urp_cvrp.baselines.savings',return_value={'routes':[[0,1,0]],'reported_cost':0}):
            with self.assertRaisesRegex(ValueError,'independent warm-start checker'):
                adapter.solve(instance,'pyvrp_ils_savings_warm',11,Budget(5,5),CONFIG)

    def test_known_micro_optima(self):
        cases=json.loads((ROOT/'fixtures/known_optima.json').read_text())['cases']
        for case in cases:
            for method in CONFIG['algorithms']:
                instance=from_dict(case['instance'])
                out=adapter.solve(instance,method,11,Budget(5,5),{**CONFIG,'pyvrp_iterations':100})
                self.assertTrue(check_solution(instance,out).accepted)
                self.assertAlmostEqual(out['reported_cost'],case['known_optimum'])

    def test_warm_start_charged_inside_measured_solver_cpu(self):
        instance=generate_instance(200,'uniform',2026100906)
        rec=evaluate(instance,'pyvrp_ils_savings_warm',11,'cpu025',CONFIG,0)
        self.assertTrue(rec['accepted']);self.assertTrue(rec['budget_conformant'])
        phase_cpu=rec['search']['warm_start_constructor_cpu_seconds']+rec['search']['warm_start_independent_validation_cpu_seconds']
        self.assertGreater(phase_cpu,0);self.assertLess(phase_cpu,rec['solver_cpu_seconds'])
        self.assertGreater(rec['child_total_cpu_seconds'],rec['solver_cpu_seconds'])

    def test_forced_singleton_warm_conversion(self):
        raw=generate_instance(8,'uniform',2026100907).to_dict()
        raw['demands']=[0]+[raw['capacity']]*8
        instance=from_dict(raw)
        out=adapter.solve(instance,'pyvrp_ils_savings_warm',11,Budget(5,5),{**CONFIG,'pyvrp_iterations':20})
        self.assertTrue(check_solution(instance,out).accepted)
        self.assertEqual(len(out['routes']),8)
        self.assertEqual(sorted(r[1] for r in out['routes']),list(range(1,9)))
        self.assertTrue(out['search']['incumbent_not_worse_than_initial_integer_cost'])

    def test_same_24_frozen_scale_instances(self):
        manifest=json.loads((ROOT/'scale_budget_v1/data/dev/manifest.json').read_text())
        self.assertEqual({i.instance_id:i.sha256 for i in instances()},{r['instance_id']:r['sha256'] for r in manifest['instances']})
        self.assertEqual(len(instances()),24)


if __name__=='__main__':unittest.main(verbosity=2)
