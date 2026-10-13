"""Handwritten microcases only: no benchmark loading or packing-policy calls."""

import ast
from copy import deepcopy
from pathlib import Path
import unittest

from src.checker import MAX_ITEMS, ValidationError, aggregate_records, check_assignment


class CheckerTests(unittest.TestCase):
    def test_noncontiguous_first_use_and_nonempty_count(self):
        result = check_assignment([6, 4, 3], 10, [2, 2, 0], 2, [7, 10, 0])
        self.assertEqual(result["loads"], [3, 0, 10])
        self.assertEqual(result["used_bins"], 2)
        self.assertEqual(result["L1"], 2)
        self.assertEqual(result["per_instance_excess"], 0.0)

    def test_original_order_is_preserved(self):
        items, assignment, residuals = [9, 1, 6, 4], [3, 3, 1, 1], [10, 0, 10, 0]
        before = deepcopy((items, assignment, residuals))
        result = check_assignment(items, 10, assignment, 2, residuals)
        self.assertEqual(result["loads"], [0, 10, 0, 10])
        self.assertEqual((items, assignment, residuals), before)

    def test_exactly_full_bins_and_full_size_item(self):
        result = check_assignment([6, 4, 10], 10, [0, 0, 1], 2, [0, 0, 10])
        self.assertEqual(result["total_size"], 20)
        self.assertEqual(result["L1"], 2)
        self.assertEqual(result["excess_bins"], 0)

    def test_ceiling_uses_exact_integer_arithmetic(self):
        capacity = 10 ** 100
        result = check_assignment([capacity, 1], capacity, [0, 1], 2)
        self.assertEqual(result["L1"], 2)
        self.assertEqual(result["total_size"], capacity + 1)

    def test_stronger_bound_is_diagnostic_only(self):
        result = check_assignment([6, 6, 6], 10, [0, 1, 2], 3)
        self.assertEqual(result["L1"], 2)
        self.assertEqual(result["large_item_count"], 3)
        self.assertEqual(result["diagnostic_lower_bound"], 3)
        self.assertEqual(result["per_instance_excess"], 0.5)

    def test_half_capacity_is_not_large(self):
        result = check_assignment([5, 5, 5], 10, [0, 0, 1], 2)
        self.assertEqual(result["large_item_count"], 0)
        odd_result = check_assignment([4, 5], 9, [0, 0], 1)
        self.assertEqual(odd_result["large_item_count"], 1)

    def test_lower_bound_excess_is_not_optimality_gap(self):
        # Five 4s require three bins, since no bin can fit three 4s. L1 is only 2.
        result = check_assignment([4, 4, 4, 4, 4], 10, [0, 0, 1, 1, 2], 3)
        self.assertEqual(result["diagnostic_lower_bound"], 2)
        self.assertEqual(result["per_instance_excess"], 0.5)
        self.assertNotIn("optimality_gap", result)

    def test_empty_microinput(self):
        result = check_assignment([], 10, [], 0, [])
        for name in ("n", "used_bins", "total_size", "L1", "diagnostic_lower_bound", "excess_bins"):
            self.assertEqual(result[name], 0)
        self.assertIsNone(result["per_instance_excess"])
        self.assertEqual(result["loads"], [])
        self.assertEqual(result["residuals"], [])

    def test_capacity_must_be_positive_exact_integer(self):
        for capacity in (True, False, 0, -1, 10.0, float("nan"), None, "10"):
            with self.subTest(capacity=capacity), self.assertRaises(ValidationError):
                check_assignment([1], capacity, [0], 1)

    def test_items_must_be_positive_exact_integer_within_capacity(self):
        for item in (True, False, 0, -1, 11, 1.0, float("nan"), None, "1"):
            with self.subTest(item=item), self.assertRaises(ValidationError):
                check_assignment([item], 10, [0], 1)

    def test_integer_subclasses_are_rejected(self):
        class AlmostInt(int):
            pass
        for args in (
            ([AlmostInt(1)], 10, [0], 1),
            ([1], AlmostInt(10), [0], 1),
            ([1], 10, [AlmostInt(0)], 1),
            ([1], 10, [0], AlmostInt(1)),
            ([1], 10, [0], 1, [AlmostInt(9)]),
        ):
            with self.subTest(args=args), self.assertRaises(ValidationError):
                check_assignment(*args)

    def test_inputs_require_lists(self):
        for args in (((1,), 10, [0], 1), ([1], 10, (0,), 1), ([1], 10, [0], 1, (9,))):
            with self.subTest(args=args), self.assertRaises(ValidationError):
                check_assignment(*args)

    def test_item_count_limit_without_solver(self):
        self.assertEqual(check_assignment([1] * MAX_ITEMS, MAX_ITEMS, [0] * MAX_ITEMS, 1)["L1"], 1)
        with self.assertRaises(ValidationError):
            check_assignment([1] * (MAX_ITEMS + 1), MAX_ITEMS + 1, [0] * (MAX_ITEMS + 1), 1)

    def test_missing_or_extra_assignment(self):
        for assignment in ([], [0], [0, 0, 1]):
            with self.subTest(assignment=assignment), self.assertRaises(ValidationError):
                check_assignment([3, 4], 10, assignment, 1)

    def test_assignment_types_and_bin_bounds(self):
        for bin_id in (True, False, 0.0, -1, 2, None, "0"):
            with self.subTest(bin_id=bin_id), self.assertRaises(ValidationError):
                check_assignment([3, 4], 10, [0, bin_id], 1)

    def test_capacity_overflow_is_rejected(self):
        with self.assertRaises(ValidationError):
            check_assignment([6, 5], 10, [0, 0], 1)

    def test_forged_count_and_count_types(self):
        for count in (0, 1, 3, -1, True, False, 2.0, None, "2"):
            with self.subTest(count=count), self.assertRaises(ValidationError):
                check_assignment([6, 4, 3], 10, [2, 2, 0], count)

    def test_missing_extra_or_forged_residuals(self):
        for residuals in ([7, 10], [7, 10, 0, 10], [10, 7, 0], [7, 9, 0], [7, 10, 1]):
            with self.subTest(residuals=residuals), self.assertRaises(ValidationError):
                check_assignment([6, 4, 3], 10, [2, 2, 0], 2, residuals)

    def test_residual_types_and_bounds(self):
        for residual in (True, False, 9.0, -1, 11, None, "9"):
            with self.subTest(residual=residual), self.assertRaises(ValidationError):
                check_assignment([1], 10, [0], 1, [residual])

    def test_no_solver_or_controller_imports(self):
        source = Path(__file__).resolve().parents[1] / "src" / "checker.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                modules.append(node.module)
        self.assertEqual(modules, ["fractions"])


class AggregationTests(unittest.TestCase):
    @staticmethod
    def record(items, assignment, used, method="FF", capacity=10):
        return {**check_assignment(items, capacity, assignment, used), "method": method}

    def unequal_records(self):
        return [
            self.record([1, 1, 1, 1], [0, 1, 2, 3], 4),  # L1=1, excess=3
            self.record([10, 10, 1, 1], [0, 1, 2, 2], 3),  # L1=3, excess=0
            self.record([6, 6, 6, 6], [0, 1, 2, 3], 4),  # L1=3, excess=1/3
            self.record([5, 5, 5, 5], [0, 0, 1, 1], 2),  # L1=2, excess=0
            self.record([10, 10, 10, 10], [0, 1, 2, 3], 4),  # L1=4, excess=0
        ]

    def test_ratio_of_sums_differs_from_mean_of_ratios(self):
        group, = aggregate_records(self.unequal_records())
        self.assertEqual(group["sum_used_bins"], 17)
        self.assertEqual(group["sum_L1"], 13)
        self.assertEqual(group["record_count"], 5)
        self.assertEqual(group["primary_excess"], 4 / 13)
        self.assertEqual(group["mean_per_instance_excess"], 2 / 3)
        self.assertNotEqual(group["primary_excess"], group["mean_per_instance_excess"])
        self.assertNotIn("optimality_gap", group)

    def test_aggregation_groups_by_all_three_keys(self):
        records = self.unequal_records()
        for method, capacity, items, assignment, used in (
            ("BF", 10, [1, 1, 1, 1], [0, 0, 0, 0], 1),
            ("FF", 11, [1, 1, 1, 1], [0, 0, 0, 0], 1),
            ("FF", 10, [1], [0], 1),
        ):
            records.extend(self.record(items, assignment, used, method, capacity) for _ in range(5))
        groups = aggregate_records(records)
        self.assertEqual([(g["n"], g["capacity"], g["method"]) for g in groups],
                         [(1, 10, "FF"), (4, 10, "BF"), (4, 10, "FF"), (4, 11, "FF")])
        self.assertTrue(all(g["record_count"] == 5 for g in groups))

    def test_aggregation_does_not_trust_precomputed_excess(self):
        records = self.unequal_records()
        for record in records:
            record["per_instance_excess"] = -999
            record["excess_bins"] = -999
            record["diagnostic_lower_bound"] = -999
        group, = aggregate_records(records)
        self.assertEqual(group["primary_excess"], 4 / 13)
        self.assertEqual(group["mean_per_instance_excess"], 2 / 3)

    def test_exactly_five_records_are_required(self):
        records = self.unequal_records()
        for bad_records in ([], records[:1], records[:4], records + [records[0]]):
            with self.subTest(count=len(bad_records)), self.assertRaises(ValidationError):
                aggregate_records(bad_records)

    def test_incomplete_group_rejects_entire_aggregation(self):
        records = self.unequal_records()
        records.append(self.record([1], [0], 1, "BF"))
        with self.assertRaises(ValidationError):
            aggregate_records(records)

    def test_empty_microinstances_cannot_be_aggregated(self):
        empty_record = self.record([], [], 0)
        with self.assertRaises(ValidationError):
            aggregate_records([empty_record] * 5)
        records = self.unequal_records()
        records[0]["L1"] = 0
        with self.assertRaises(ValidationError):
            aggregate_records(records)

    def test_missing_record_fields(self):
        for field in ("n", "capacity", "method", "used_bins", "L1"):
            records = self.unequal_records()
            del records[0][field]
            with self.subTest(field=field), self.assertRaises(ValidationError):
                aggregate_records(records)

    def test_invalid_record_fields(self):
        bad_fields = (
            ("n", True), ("n", 0), ("n", MAX_ITEMS + 1), ("n", 4.0),
            ("capacity", True), ("capacity", 0), ("capacity", 10.0),
            ("used_bins", True), ("used_bins", 0), ("used_bins", 5), ("used_bins", 4.0),
            ("L1", True), ("L1", 0), ("L1", 5), ("L1", 1.0),
            ("method", None), ("method", ""), ("method", "  "), ("method", 1),
        )
        for field, value in bad_fields:
            records = self.unequal_records()
            records[0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValidationError):
                aggregate_records(records)

    def test_used_bins_below_l1_rejected(self):
        records = self.unequal_records()
        records[1]["used_bins"] = 2
        with self.assertRaises(ValidationError):
            aggregate_records(records)

    def test_aggregation_input_types_and_no_mutation(self):
        for records in (None, {}, (), [None] * 5):
            with self.subTest(records=records), self.assertRaises(ValidationError):
                aggregate_records(records)
        records = self.unequal_records()
        before = deepcopy(records)
        aggregate_records(records)
        self.assertEqual(records, before)


if __name__ == "__main__":
    unittest.main()
