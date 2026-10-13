import json
import math
from pathlib import Path
import time
import unittest
from urp_cvrp.budget import Budget
from urp_cvrp.checker import check_solution
from urp_cvrp.exact import exhaustive_optimum
from urp_cvrp.generate import generate_instance
from urp_cvrp.instance import from_dict
from mature_pyvrp_v1.adapter import prepare, solve, matrices, build, CPUIterationStop, PYVRP_METHODS
from mature_pyvrp_v1.runtime import run

ROOT=Path(__file__).resolve().parents[1]
CONFIG=json.loads((Path(__file__).parent/'protocol.json').read_text())


class AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prepare('pyvrp_ils_s1e6')

    def evaluate(self, instance, algorithm, seed=11, config=CONFIG):
        out=solve(instance,algorithm,seed,Budget(5,5),config)
        checked=check_solution(instance,out)
        self.assertTrue(checked.accepted,(algorithm,checked.errors,out))
        if instance.n_customers:
            m=out['search']
            self.assertTrue(m['integer_cost_matches'])
            self.assertLessEqual(abs(checked.recomputed_cost-m['quantized_cost_divided_by_scale']),m['route_rounding_bound']+1e-9)
            self.assertLessEqual(m['route_rounding_bound'],m['theoretical_rounding_bound_plus_float_slack'])
        return out

    def test_all_known_micro_optima(self):
        for case in json.loads((ROOT/'fixtures/known_optima.json').read_text())['cases']:
            for method in PYVRP_METHODS:
                out=self.evaluate(from_dict(case['instance']),method)
                self.assertAlmostEqual(out['reported_cost'],case['known_optimum'])

    def test_independent_exhaustive_oracle(self):
        for seed in (9101,9102,9103,9104):
            instance=generate_instance(5,'uniform',seed)
            exact=exhaustive_optimum(instance)['reported_cost']
            for method in PYVRP_METHODS:
                out=self.evaluate(instance,method,seed)
                self.assertGreaterEqual(out['reported_cost']+1e-9,exact)
                self.assertAlmostEqual(out['reported_cost'],exact,places=8)

    def test_generated_sizes_and_mapping(self):
        for n in (1,8,20,40):
            for family in ('uniform','clustered'):
                instance=generate_instance(n,family,8800+n)
                for method in PYVRP_METHODS:
                    out=self.evaluate(instance,method)
                    self.assertEqual(sorted(x for r in out['routes'] for x in r[1:-1]),list(range(1,n+1)))

    def test_full_capacity_forces_singleton_fleet(self):
        raw=generate_instance(8,'uniform',8612).to_dict()
        raw['demands']=[0]+[raw['capacity']]*8
        instance=from_dict(raw)
        for method in PYVRP_METHODS:
            out=self.evaluate(instance,method)
            self.assertEqual(len(out['routes']),8)
            self.assertEqual(out['search']['fleet_num_available'],8)
            self.assertEqual(out['search']['vehicle_fixed_cost'],0)

    def test_zero_demands_zero_distances(self):
        raw=generate_instance(8,'uniform',8613).to_dict()
        raw['demands']=[0]*9;raw['coordinates']=[[0,0]]*9
        for method in PYVRP_METHODS:
            out=self.evaluate(from_dict(raw),method)
            self.assertEqual(out['reported_cost'],0)

    def test_rounding_matrix_and_bound(self):
        instance=generate_instance(32,'uniform',8899)
        for scale in PYVRP_METHODS.values():
            d,q=matrices(instance,scale)
            for i in range(33):
                for j in range(33):
                    self.assertEqual(type(q[i][j]),int)
                    self.assertEqual(q[i][j],q[j][i])
                    self.assertLessEqual(abs(d[i][j]-q[i][j]/scale),0.5/scale+1e-12)

    def test_overflow_guard(self):
        raw=generate_instance(1,'uniform',86).to_dict();raw['coordinates']=[[0,0],[1e10,0]]
        for scale in PYVRP_METHODS.values():
            with self.assertRaises(ValueError):matrices(from_dict(raw),scale)

    def test_penalty_accumulation_overflow_guard(self):
        raw=generate_instance(2,'uniform',86).to_dict()
        raw['capacity']=10**16;raw['demands']=[0,10**16,10**16]
        for scale in PYVRP_METHODS.values():
            with self.assertRaises(ValueError):matrices(from_dict(raw),scale)

    def test_penalties_scale_in_cost_units(self):
        instance=generate_instance(8,'uniform',1)
        for method,scale in PYVRP_METHODS.items():
            out=self.evaluate(instance,method)
            self.assertEqual(out['search']['penalty_min'],0.1*scale)
            self.assertEqual(out['search']['penalty_max'],100000*scale)

    def test_replay_fixed_iterations(self):
        instance=generate_instance(20,'uniform',9871)
        for method in PYVRP_METHODS:
            a=self.evaluate(instance,method);b=self.evaluate(instance,method)
            self.assertEqual(a['routes'],b['routes']);self.assertEqual(a['reported_cost'],b['reported_cost'])
            self.assertEqual(a['search']['iterations'],1000)

    def test_stop_work_count(self):
        stop=CPUIterationStop(Budget(5,5),{**CONFIG,'pyvrp_iterations':3})
        self.assertFalse(stop(0));self.assertFalse(stop(0));self.assertFalse(stop(0));self.assertTrue(stop(0))
        self.assertEqual(stop.iterations,3);self.assertEqual(stop.reason,'iteration_limit')

    def test_stop_cpu_margin(self):
        budget=Budget(0.25,1);budget.start_cpu=time.process_time()-0.2451
        stop=CPUIterationStop(budget,CONFIG)
        self.assertTrue(stop(0));self.assertEqual(stop.reason,'cpu_return_margin')

    def test_isolated_solver_and_complete_accounting(self):
        instance=generate_instance(20,'uniform',8862)
        for method in ('parallel_savings','pyvrp_ils_s1e6','pyvrp_ils_s1e9'):
            record=run(instance,method,11,CONFIG)
            self.assertEqual(record['status'],'returned',record)
            self.assertTrue(check_solution(instance,record['output']).accepted)
            self.assertGreaterEqual(record['child_total_cpu_seconds'],record['solver_cpu_seconds'])
            self.assertLess(record['solver_cpu_seconds'],0.25)


if __name__=='__main__':unittest.main(verbosity=2)
