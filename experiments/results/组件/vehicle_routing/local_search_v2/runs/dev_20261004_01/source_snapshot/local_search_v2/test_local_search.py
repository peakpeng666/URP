import json
import math
from pathlib import Path
import random
import unittest

from urp_cvrp.baselines import distance_matrix, savings
from urp_cvrp.budget import Budget
from urp_cvrp.checker import check_solution
from urp_cvrp.exact import exhaustive_optimum
from urp_cvrp.generate import generate_instance
from urp_cvrp.instance import from_dict
from local_search_v2.solvers import solve, cost, moves, apply_move, descend, SearchState, output
from local_search_v2.runtime import run

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((Path(__file__).parent / "protocol.json").read_text())
KINDS = ("two_opt", "relocate", "swap", "two_opt_star")


def raw_instance(coords, demands, capacity):
    raw = generate_instance(0, "uniform", 1).to_dict()
    raw.update(coordinates=coords, demands=demands, capacity=capacity, split="unit_test")
    return from_dict(raw)


class LocalSearchTests(unittest.TestCase):
    def test_every_delta_and_move_against_full_independent_checker(self):
        checked = 0
        for seed in range(20):
            instance = generate_instance(8, "uniform" if seed % 2 else "clustered", 9000 + seed)
            if seed % 3 == 0:
                raw = instance.to_dict()
                raw["demands"] = [0] * 9
                instance = from_dict(raw)
            routes = [r[1:-1] for r in savings(instance, seed, Budget(5, 5))["routes"]]
            if seed % 2:
                routes = [list(range(1, 4)), list(range(4, 7)), [7, 8]]
                if any(sum(instance.demands[x] for x in r) > instance.capacity for r in routes):
                    routes = [[i] for i in range(1, 9)]
            d = distance_matrix(instance, Budget(5, 5))
            old = check_solution(instance, output(routes, d)).recomputed_cost
            for kind in KINDS:
                for delta, move in moves(routes, instance.demands, instance.capacity, d, kind):
                    changed = apply_move(routes, move)
                    result = check_solution(instance, output(changed, d))
                    self.assertTrue(result.accepted, (move, result.errors))
                    self.assertAlmostEqual(delta, result.recomputed_cost - old, places=9)
                    checked += 1
        self.assertGreater(checked, 1000)

    def test_local_search_never_worsens_savings(self):
        for n in (0, 1, 5, 8, 20, 40):
            for family in ("uniform", "clustered"):
                instance = generate_instance(n, family, 5000 + n)
                base = savings(instance, 11, Budget(5, 5))["reported_cost"]
                for name in ("savings_vnd", "multistart_vnd"):
                    result = solve(instance, name, 11, Budget(5, 5), CONFIG)
                    check = check_solution(instance, result)
                    self.assertTrue(check.accepted, check.errors)
                    self.assertLessEqual(check.recomputed_cost, base + 1e-9)

    def test_known_optima(self):
        for case in json.loads((ROOT / "fixtures/known_optima.json").read_text())["cases"]:
            for name in ("savings_vnd", "multistart_vnd"):
                instance = from_dict(case["instance"])
                result = solve(instance, name, 11, Budget(5, 5), CONFIG)
                self.assertTrue(check_solution(instance, result).accepted)
                self.assertAlmostEqual(result["reported_cost"], case["known_optimum"])

    def test_never_beats_exact_micro_optimum(self):
        for seed in (314, 315, 316, 317):
            instance = generate_instance(5, "uniform", seed)
            optimum = exhaustive_optimum(instance)["reported_cost"]
            for name in ("savings_vnd", "multistart_vnd"):
                result = solve(instance, name, seed, Budget(5, 5), CONFIG)
                self.assertTrue(check_solution(instance, result).accepted)
                self.assertGreaterEqual(result["reported_cost"] + 1e-9, optimum)

    def test_completed_descent_has_no_improving_declared_neighbor(self):
        for seed in range(8):
            instance = generate_instance(12, "uniform", 4000 + seed)
            d = distance_matrix(instance, Budget(5, 5))
            routes = [r[1:-1] for r in savings(instance, seed, Budget(5, 5))["routes"]]
            state = SearchState(1000000, Budget(5, 5), 1e-9)
            routes = descend(instance, routes, d, state)
            for kind in KINDS:
                for delta, move in moves(routes, instance.demands, instance.capacity, d, kind):
                    self.assertGreaterEqual(delta, -1e-9)

    def test_seed_replay_with_work_limit(self):
        instance = generate_instance(20, "clustered", 9123)
        for name in ("savings_vnd", "multistart_vnd"):
            a = solve(instance, name, 29, Budget(5, 5), CONFIG)
            b = solve(instance, name, 29, Budget(5, 5), CONFIG)
            self.assertEqual(a, b)

    def test_zero_distances_demands_and_full_capacity(self):
        cases = [raw_instance([[0, 0]] * 6, [0] * 6, 3),
                 raw_instance([[i, 0] for i in range(6)], [0] + [3] * 5, 3)]
        for instance in cases:
            for name in ("savings_vnd", "multistart_vnd"):
                result = solve(instance, name, 11, Budget(5, 5), CONFIG)
                self.assertTrue(check_solution(instance, result).accepted)

    def test_move_limit_returns_feasible_incumbent(self):
        instance = generate_instance(20, "uniform", 123)
        result = solve(instance, "multistart_vnd", 11, Budget(5, 5),
                       {**CONFIG, "move_evaluation_limit": 1})
        self.assertTrue(check_solution(instance, result).accepted)
        self.assertEqual(result["search"]["termination"], "move_evaluation_limit")
        self.assertEqual(result["search"]["move_evaluations"], 1)

    def test_cap_prevents_generator_lookahead(self):
        from unittest.mock import patch
        import local_search_v2.solvers as module
        instance = generate_instance(20, "uniform", 123)
        real_moves = module.moves
        yielded = [0]
        def counted_moves(*args):
            for candidate in real_moves(*args):
                yielded[0] += 1
                yield candidate
        with patch.object(module, "moves", counted_moves):
            result = module.solve(instance, "multistart_vnd", 11, Budget(5, 5),
                                  {**CONFIG, "move_evaluation_limit": 1})
        self.assertTrue(check_solution(instance, result).accepted)
        self.assertEqual(result["search"]["move_evaluations"], 1)
        self.assertEqual(yielded[0], 1)

    def test_budget_exhaustion_returns_feasible_incumbent(self):
        instance = generate_instance(20, "uniform", 123)
        class StopBudget:
            def __init__(self):
                self.calls = 0
            def check(self):
                from urp_cvrp.budget import BudgetExceeded
                self.calls += 1
                if self.calls > 100:
                    raise BudgetExceeded("test_budget")
        result = solve(instance, "multistart_vnd", 11, StopBudget(), CONFIG)
        self.assertTrue(check_solution(instance, result).accepted)
        self.assertEqual(result["search"]["termination"], "test_budget")


class RuntimeTests(unittest.TestCase):
    def test_exact_child_accounting_includes_startup(self):
        result = run(generate_instance(8, "uniform", 1), "savings_vnd", 11, CONFIG)
        self.assertEqual(result["status"], "returned", result)
        self.assertGreaterEqual(result["child_total_cpu_seconds"], result["worker_cpu_seconds"])
        self.assertGreater(result["child_peak_rss_kib"], 0)
        self.assertEqual(result["child_exit_code"], 0)

    def test_killed_cpu_and_sleep_are_counted(self):
        for algorithm in ("__spin", "__sleep"):
            result = run(generate_instance(0, "uniform", 1), algorithm, 11,
                         {**CONFIG, "wall_budget_seconds": 0.2}, True)
            self.assertEqual(result["status"], "hard_wall_timeout")
            self.assertGreater(result["child_total_cpu_seconds"], 0)
            self.assertEqual(result["child_exit_code"], -9)
            self.assertLess(result["total_wall_seconds"], 1.0)

    def test_exception_and_nonfinite_output(self):
        for algorithm, expected in (("__exception", "solver_exception"), ("__nan", "invalid_serialization")):
            result = run(generate_instance(0, "uniform", 1), algorithm, 11, CONFIG, True)
            self.assertEqual(result["status"], expected)
            self.assertGreater(result["child_total_cpu_seconds"], 0)

    def test_allowlist(self):
        with self.assertRaises(ValueError):
            run(generate_instance(0, "uniform", 1), "__spin", 11, CONFIG)


if __name__ == "__main__":
    unittest.main(verbosity=2)
