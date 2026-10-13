"""Fault-injection checks for the independent, read-only scientific validator."""
import copy
import tempfile
import unittest
from pathlib import Path

import numpy as np

from scripts.validate_data import (
    ValidationError, Validator, compare_csv, decision, features, near, replay, safe_path,
)


class TrajectoryValidationTests(unittest.TestCase):
    def setUp(self):
        # Deliberately use slot 3 before slot 0: slot index is not used-bin count.
        self.items = [60, 40, 70, 20]
        self.row = {"used_bins": 2}
        self.arrays = {k: np.asarray(v, dtype=np.int64) for k, v in {
            "assignment": [3, 3, 0, 0],
            "pre_remaining": [100, 40, 100, 30],
            "post_remaining": [40, 0, 30, 10],
            "feasible_counts": [4, 4, 3, 3],
            "used_bins_after": [1, 1, 2, 2],
            "remaining": [10, 100, 100, 0],
        }.items()}

    def test_noncontiguous_slots_and_empty_slots(self):
        self.assertEqual(replay(self.items, self.row, self.arrays, prefix_length=2), [100, 100, 100, 0])

    def test_each_corrupted_array_is_rejected_with_location(self):
        for key in self.arrays:
            with self.subTest(key=key):
                corrupt = copy.deepcopy(self.arrays)
                corrupt[key][0] += 1
                with self.assertRaises(ValidationError) as error:
                    replay(self.items, self.row, corrupt, location="test.npz", prefix_length=2)
                self.assertIn("test.npz/", error.exception.location)

    def test_overcapacity_rejected(self):
        with self.assertRaisesRegex(ValidationError, "capacity"):
            replay([60, 41, 70, 20], self.row, self.arrays)

    def test_invalid_assignment_and_final_count_rejected(self):
        self.arrays["assignment"][0] = -1
        with self.assertRaisesRegex(ValidationError, "assignment"):
            replay(self.items, self.row, self.arrays)
        self.arrays["assignment"][0] = 3
        with self.assertRaisesRegex(ValidationError, "used_bins"):
            replay(self.items, {"used_bins": 4}, self.arrays)

    def test_float_integer_like_and_short_arrays_rejected(self):
        self.arrays["assignment"] = self.arrays["assignment"].astype(float)
        with self.assertRaisesRegex(ValidationError, "integer dtype"):
            replay(self.items, self.row, self.arrays)
        self.arrays["assignment"] = np.array([3, 3, 0], dtype=int)
        with self.assertRaisesRegex(ValidationError, "shape"):
            replay(self.items, self.row, self.arrays)


class FeatureDecisionTests(unittest.TestCase):
    def test_features_have_defined_denominators_and_linear_quantiles(self):
        values = features([1] * 250 + [100] * 250, [0, 50] + [100] * 4998)
        self.assertEqual(len(values), 31)
        self.assertEqual(values[0], .5)
        self.assertEqual(values[9], .5)
        self.assertAlmostEqual(values[10], .505)
        self.assertAlmostEqual(values[11], .495)
        self.assertEqual(values[12:15], [.01, .505, 1.0])
        self.assertAlmostEqual(values[15], 1 / 499)
        self.assertEqual(values[16], 0)
        self.assertAlmostEqual(values[17], .99)
        self.assertEqual(values[18], 2 / 500)
        self.assertEqual(values[19], .5)
        self.assertEqual(values[24], .5)
        self.assertEqual(values[-2:], [.25, .25])

    def test_equal_neighbor_distances_stable_and_prediction_ties_use_sbs(self):
        model = {"mean": [0], "scale": [1], "x": [[1], [-1], [1], [-1], [1], [-1]],
                 "y": [[10, 12], [12, 10], [11, 11], [11, 11], [11, 11], [99, 1]],
                 "k": 5, "sbs_index": 1}
        result = decision([0], model)
        self.assertEqual(result["neighbors"], [0, 1, 2, 3, 4])
        self.assertEqual(result["squared_distances"], [1] * 5)
        self.assertEqual(result["predicted_final_bins"], [11, 11])
        self.assertEqual(result["selected_index"], 1)

    def test_nonfinite_or_wrong_shape_fails(self):
        with self.assertRaisesRegex(ValidationError, "non-finite"):
            near([float("nan")], [0], "test")
        with self.assertRaisesRegex(ValidationError, "shape"):
            near([1], [[1]], "test")


class FailureReportingTests(unittest.TestCase):
    def test_missing_dataset_cannot_pass_and_does_not_write_into_input(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = Validator(root).run()
            self.assertEqual(report["status"], "FAIL")
            self.assertFalse(report["passed"])
            self.assertEqual(report["coverage"]["runs"], 0)
            self.assertEqual(report["failures"][0]["type"], "FileNotFoundError")
            self.assertEqual(list(root.iterdir()), [])

    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValidationError, "escapes"):
                safe_path(Path(temp), "../outside.json")

    def test_duplicate_csv_rows_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "rows.csv"
            path.write_text("id,bins\none,3\none,4\n", encoding="utf-8")
            with self.assertRaisesRegex(ValidationError, "unique key"):
                compare_csv(path, [{"id": "one", "bins": 3}, {"id": "two", "bins": 4}], ["id"])

    def test_corrupt_csv_statistic_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "rows.csv"
            path.write_text("id,bins\none,4\n", encoding="utf-8")
            with self.assertRaisesRegex(ValidationError, "numeric mismatch"):
                compare_csv(path, [{"id": "one", "bins": 3}], ["id"])


if __name__ == "__main__":
    unittest.main()
