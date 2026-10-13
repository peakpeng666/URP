"""Handwritten prospective tests. Prepared as source; not executed by the author.

Numerical/import/test execution requires the separately authorized coordinated
window and supervised limits. These tests never execute downloaded author code,
query a model/backend, generate candidates, or consume a research evaluation slot.
"""
import copy
from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
import sys
import unittest
import warnings as pywarnings

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
from schema import StructureError, validate_program
from interpreter import (
    ContractFault, InputInvalid, NumericInvalid, WorkBudget, WorkLimit,
    check_value, evaluate, pack,
)
from warnings_log import DiagnosticLimit, UnexpectedWarning, WarningLog

TYPE_TAGS = {"SI32": "i32", "VI64": "vi64", "SF64": "f64", "VF64": "vf64", "VB": "vb"}
FROZEN_FORMULA_SHA256 = "282deba5a6c4a0f5247a0750fdd11b78d2e2dbec88738787f9ef72d034fdb3e4"
# Filled only by the authorized domain comparison test. Compact public evidence,
# not raw arrays or a claim of independent proof of the published algorithm.
EVIDENCE = []


def raw_program(name):
    return (FIXTURES / "programs" / (name + ".json")).read_bytes()


def program(name):
    return validate_program(raw_program(name))


def base_object():
    return json.loads(raw_program("vector_cast"))


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def combined_value_hash(values):
    """Ordered dtype/shape/value framing; preserve scalar shape and raw bits."""
    digest = hashlib.sha256(b"math-dag-v1:ordered-values:v1\n")
    for index, value in enumerate(values):
        array = np.asarray(value)
        raw = array.tobytes(order="C")
        digest.update(str(index).encode("ascii") + b"\x00")
        digest.update(array.dtype.str.encode("ascii") + b"\x00")
        digest.update(encode(list(array.shape)) + b"\x00")
        digest.update(str(len(raw)).encode("ascii") + b":" + raw + b"\x00\n")
    return digest.hexdigest()


class StructuralControls(unittest.TestCase):
    def test_all_handwritten_runtime_controls_validate(self):
        for path in sorted((FIXTURES / "programs").glob("*.json")):
            with self.subTest(path=path.name):
                validate_program(path.read_bytes())

    def test_invalid_raw_and_handwritten_mutations(self):
        cases = json.loads((FIXTURES / "validation_cases.json").read_bytes())["cases"]
        for case in cases:
            with self.subTest(case=case["id"]):
                if "raw" in case:
                    raw = case["raw"].encode("utf-8")
                else:
                    obj = base_object()
                    obj.update(copy.deepcopy(case.get("replace", {})))
                    obj.update(copy.deepcopy(case.get("add", {})))
                    if "remove" in case:
                        del obj[case["remove"]]
                    raw = encode(obj)
                with self.assertRaises(StructureError):
                    validate_program(raw)

    def test_constant_and_node_count_boundaries(self):
        obj = base_object()
        obj["constants"] *= 16
        obj["nodes"] = [["div", "bins", "c15"]]
        self.assertEqual(len(validate_program(encode(obj)).constants), 16)
        obj["constants"].append({"type": "f64", "value": 1})
        with self.assertRaises(StructureError):
            validate_program(encode(obj))
        obj = base_object()
        obj["nodes"] = [["div", "bins", "c0"] for _ in range(64)]
        obj["return_node"] = 63
        self.assertEqual(len(validate_program(encode(obj)).nodes), 64)
        obj["nodes"].append(["div", "bins", "c0"])
        obj["return_node"] = 64
        with self.assertRaises(StructureError):
            validate_program(encode(obj))

    def test_constant_endpoints_and_f64_integer_literal(self):
        for tag in ("i32", "f64"):
            for value in (-1000, 0, 1000):
                with self.subTest(tag=tag, value=value):
                    obj = base_object()
                    obj["constants"] = [{"type": tag, "value": value}]
                    validated = validate_program(encode(obj))
                    self.assertEqual(validated.constants, ((tag, value),))
        obj = base_object()
        obj["constants"] = []
        obj["nodes"] = [["div", "bins", "item"]]
        self.assertEqual(validate_program(encode(obj)).constants, ())

    def test_raw_byte_limit_exact_and_plus_one(self):
        raw = encode(base_object())
        padded = raw + b" " * (32768 - len(raw))
        self.assertEqual(len(padded), 32768)
        validate_program(padded)
        with self.assertRaises(StructureError):
            validate_program(padded + b" ")
        obj = base_object()
        obj["description"] = "\u00e9" * 512
        raw = encode(obj)
        padded = raw + b" " * (32769 - len(raw))
        self.assertLess(len(padded.decode("utf-8")), 32768)
        with self.assertRaises(StructureError):
            validate_program(padded)

    def test_description_utf8_byte_boundary(self):
        for text in ("a" * 1024, "\u00e9" * 512):
            obj = base_object()
            obj["description"] = text
            validate_program(encode(obj))
            obj["description"] = text + "a"
            with self.assertRaises(StructureError):
                validate_program(encode(obj))
        for text in ("", "   "):
            obj = base_object()
            obj["description"] = text
            with self.assertRaises(StructureError):
                validate_program(encode(obj))

    def test_deep_huge_and_invalid_encoding_are_controlled(self):
        hostile = [b"[" * 12000 + b"]" * 12000, b"\xff", b"\xef\xbb\xbf" + encode(base_object())]
        obj = base_object()
        for digits in (400, 5000):
            raw = encode(obj).replace(b'"value":1', b'"value":' + b"9" * digits)
            hostile.append(raw)
        obj["nodes"] = [["div", "bins", "c" + "9" * 5000]]
        hostile.append(encode(obj))
        for raw in hostile:
            with self.subTest(length=len(raw), prefix=raw[:20]):
                self.assertLessEqual(len(raw), 32768)
                with self.assertRaises(StructureError):
                    validate_program(raw)
        for raw in ("{}", bytearray(b"{}"), memoryview(b"{}"), None):
            with self.assertRaises(StructureError):
                validate_program(raw)

    def test_immutable_program_and_canonical_identity(self):
        raw = raw_program("published_eoh")
        first = validate_program(raw)
        second = validate_program(encode(json.loads(raw)))
        self.assertNotEqual(first.raw_sha256, second.raw_sha256)
        self.assertEqual(first.canonical_sha256, second.canonical_sha256)
        with self.assertRaises(FrozenInstanceError):
            first.return_node = 0
        self.assertIs(type(first.nodes), tuple)
        self.assertTrue(all(type(row) is tuple for row in first.nodes))
        self.assertIs(type(first.constants), tuple)
        self.assertTrue(all(type(row) is tuple for row in first.constants))

    def test_published_fifteen_nodes_and_five_constants(self):
        p = program("published_eoh")
        mapping = json.loads((FIXTURES / "published_formula_mapping.json").read_bytes())
        self.assertEqual(len(p.nodes), 15)
        self.assertEqual(len(p.constants), 5)
        self.assertEqual(p.return_node, 14)
        self.assertEqual(p.types, tuple(TYPE_TAGS[x] for x in mapping["node_types"]))
        self.assertEqual(p.nodes[12], ("mul", 11, 1))


class NumericalControls(unittest.TestCase):
    def test_handwritten_expected_outcomes(self):
        cases = json.loads((FIXTURES / "evaluation_cases.json").read_bytes())["cases"]
        for case in cases:
            with self.subTest(case=case["id"]):
                p = validate_program((FIXTURES / case["program"]).read_bytes())
                item = np.int32(case["item"])
                bins = np.array(case["bins"], dtype=np.int64)
                before = bins.tobytes()
                expected = case["expected"]
                work = WorkBudget()
                journal = WarningLog()
                with journal:
                    if "failure" in expected:
                        with self.assertRaises(NumericInvalid):
                            evaluate(p, item, bins, work, journal, placement=17, trace=True)
                        result = None
                    else:
                        result = evaluate(p, item, bins, work, journal, placement=17, trace=True)
                self.assertEqual(bins.tobytes(), before)
                self.assertEqual(bins.dtype, np.dtype("int64"))
                self.assertEqual(bins.shape, (len(case["bins"]),))
                self.assertTrue(journal.payload()["complete"])
                if "warning_nodes" in expected:
                    self.assertEqual([e[1] for e in journal.events], expected["warning_nodes"])
                    self.assertTrue(all(e[0] == 17 for e in journal.events))
                if "warning_operations" in expected:
                    messages = [journal.kinds[e[2]]["message"] for e in journal.events]
                    for message, operation in zip(messages, expected["warning_operations"]):
                        self.assertIn(operation, message)
                if "warning_count" in expected:
                    self.assertEqual(len(journal.events), expected["warning_count"])
                if "first_failed_node" in expected:
                    self.assertEqual(work.used, len(bins) * (expected["first_failed_node"] + 1))
                if result is None:
                    continue
                self.assertEqual(result["scores"].dtype, np.dtype("float64"))
                self.assertEqual(result["scores"].shape, bins.shape)
                self.assertTrue(np.all(np.isfinite(result["scores"])))
                self.assertEqual(work.used, len(bins) * len(p.nodes))
                self.assertEqual(len(result["values"]), len(p.nodes))
                self.assertEqual(len(result["trace"]), len(p.nodes))
                if "node_types" in expected:
                    self.assertEqual(p.types, tuple(TYPE_TAGS[x] for x in expected["node_types"]))
                if "final_values" in expected:
                    np.testing.assert_array_equal(result["scores"], expected["final_values"])
                if "final_sign_bits" in expected:
                    np.testing.assert_array_equal(np.signbit(result["scores"]), expected["final_sign_bits"])
                if "argmax" in expected:
                    self.assertEqual(int(np.argmax(result["scores"])), expected["argmax"])
                for index in range(len(p.nodes)):
                    key = "node_" + str(index)
                    value = result["values"][index]
                    if key + "_value" in expected:
                        self.assertEqual(value, expected[key + "_value"])
                    if key + "_values" in expected:
                        np.testing.assert_array_equal(value, expected[key + "_values"])
                    status = expected.get(key)
                    if status == "finite_positive":
                        self.assertTrue(np.all(np.isfinite(value) & (value > 0)))
                    elif status == "positive_infinity":
                        self.assertTrue(np.all(np.isposinf(value)))
                    elif status == "positive_zero":
                        self.assertTrue(np.all((value == 0) & ~np.signbit(value)))
                    elif status == "nan_scalar":
                        self.assertIs(type(value), np.float64)
                        self.assertTrue(np.isnan(value))

    def test_published_trace_matches_reviewed_handwritten_formula(self):
        # Only this already-reviewed handwritten module is imported. The author
        # evidence directory is never an import path or executable input.
        reviewed = ROOT.parent / "published_eoh_formula_v1" / "src"
        self.assertEqual(hashlib.sha256((reviewed / "formula.py").read_bytes()).hexdigest(), FROZEN_FORMULA_SHA256)
        sys.path.insert(0, str(reviewed))
        try:
            import formula
        finally:
            sys.path.pop(0)
        self.assertEqual(Path(formula.__file__).resolve(), (reviewed / "formula.py").resolve())
        mapping = json.loads((FIXTURES / "published_formula_mapping.json").read_bytes())
        p = program("published_eoh")
        fixed_cases = [(1, [1, 5]), (1, [355, 356, 500]), (10, [10, 39, 40, 41]), (100, [100, 399, 400, 401, 454, 455, 500])]
        EVIDENCE.clear()

        def compare_one(raw_item, bins):
            item = np.int32(raw_item)
            before = bins.tobytes()
            before_shape, before_dtype = bins.shape, bins.dtype
            with WarningLog() as journal:
                result = evaluate(p, item, bins, WorkBudget(), journal, placement=raw_item, trace=True)
            self.assertEqual((bins.shape, bins.dtype), (before_shape, before_dtype))
            self.assertEqual(bins.tobytes(), before)
            with pywarnings.catch_warnings(record=True) as reference_warnings:
                pywarnings.simplefilter("always")
                with np.errstate(divide="warn", over="warn", invalid="warn", under="ignore"):
                    reference = formula.score_trace(item, bins)
            self.assertEqual((bins.shape, bins.dtype), (before_shape, before_dtype))
            self.assertEqual(bins.tobytes(), before)
            reference_values = [None] * 15
            named_count = 0
            for row in mapping["nodes"]:
                if "reviewed_trace_key" not in row:
                    continue
                expected = reference[row["reviewed_trace_key"]]
                actual = result["values"][row["node"]]
                self.assertEqual(actual.dtype, expected.dtype)
                self.assertEqual(actual.shape, expected.shape)
                self.assertEqual(actual.tobytes(), expected.tobytes())
                reference_values[row["node"]] = expected
                named_count += 1
            self.assertEqual(named_count, 9)
            # These six source-ordered operations are direct handwritten NumPy
            # expressions with strong scalar constants. They check transcription;
            # they are not a second independent numerical proof.
            unnamed = {
                3: np.divide(reference["diff"], bins),
                6: np.multiply(item, np.int32(3)),
                7: np.greater(reference["diff"], np.multiply(item, np.int32(3))),
                8: np.add(reference["comb"], np.float64(0.8)),
                9: np.add(reference["comb"], np.float64(0.3)),
                11: np.add(reference["exp"], np.float64(0.7)),
            }
            self.assertEqual(len(unnamed), 6)
            for node, expected in unnamed.items():
                actual = result["values"][node]
                self.assertEqual(type(actual), type(expected))
                self.assertEqual(actual.dtype, expected.dtype)
                self.assertEqual(actual.shape, expected.shape)
                self.assertEqual(actual.tobytes(), expected.tobytes())
                reference_values[node] = expected
            self.assertTrue(all(value is not None for value in reference_values))
            self.assertEqual(combined_value_hash(result["values"]), combined_value_hash(reference_values))
            self.assertEqual([journal.kinds[e[2]]["message"] for e in journal.events], [str(w.message) for w in reference_warnings])
            self.assertTrue(journal.payload()["complete"])
            self.assertEqual(work_units := result["work_units"], 15 * len(bins))
            self.assertLessEqual(work_units, 5000000)
            self.assertEqual((bins.shape, bins.dtype), (before_shape, before_dtype))
            self.assertEqual(bins.tobytes(), before)
            return result, journal

        for raw_item, raw_bins in fixed_cases:
            with self.subTest(fixed_item=raw_item, fixed_bins=raw_bins):
                compare_one(raw_item, np.array(raw_bins, dtype=np.int64))
        pairs = 0
        denominator_infinite = 0
        for raw_item in range(1, 101):
            with self.subTest(domain_item=raw_item):
                bins = np.arange(raw_item, 501, dtype=np.int64)
                result, journal = compare_one(raw_item, bins)
                inf_count = int(np.count_nonzero(np.isposinf(result["values"][12])))
                self.assertEqual(inf_count, 146 - raw_item)
                self.assertEqual([event[1] for event in journal.events], [12])
                self.assertEqual([event[0] for event in journal.events], [raw_item])
                pairs += len(bins)
                denominator_infinite += inf_count
                EVIDENCE.append({
                    "item": raw_item,
                    "length": len(bins),
                    "final_sha256": hashlib.sha256(result["scores"].tobytes()).hexdigest(),
                    "denominator_inf_count": inf_count,
                    "warning_nodes": [event[1] for event in journal.events],
                    "values_sha256": combined_value_hash(result["values"]),
                })
        self.assertEqual(pairs, 45050)
        self.assertEqual(denominator_infinite, 9550)
        self.assertEqual(len(EVIDENCE), 100)
        self.assertEqual([row["item"] for row in EVIDENCE], list(range(1, 101)))
        self.assertLess(len(encode(EVIDENCE)), 400000)

    def test_mixed_type_broadcast_and_comparison_edges(self):
        obj = base_object()
        obj["constants"] = [{"type": "f64", "value": 2}, {"type": "f64", "value": 0.5}]
        obj["nodes"] = [
            ["div", "bins", "c0"],
            ["gt", "c0", "bins"],
            ["gt", "bins", 0],
            ["gt", 0, "bins"],
            ["where", 1, "c0", 0],
            ["where", 1, 0, "c0"],
            ["add", "c0", "bins"],
            ["sub", "c0", "bins"],
            ["mul", "c0", "bins"],
            ["div", "c0", "bins"],
            ["gt", "item", "bins"],
            ["gt", "c1", 0],
        ]
        obj["return_node"] = 6
        p = validate_program(encode(obj))
        self.assertEqual(p.types, ("vf64", "vb", "vb", "vb", "vf64", "vf64", "vf64", "vf64", "vf64", "vf64", "vb", "vb"))
        bins = np.array([1, 4], dtype=np.int64)
        before = bins.tobytes()
        with WarningLog() as journal:
            result = evaluate(p, np.int32(1), bins, WorkBudget(), journal, trace=True)
        expected_values = [
            [0.5, 2], [True, False], [True, True], [False, False],
            [2, 2], [0.5, 2], [3, 6], [1, -2], [2, 8], [2, 0.5],
            [False, False], [False, False],
        ]
        for value, tag, expected in zip(result["values"], p.types, expected_values):
            self.assertEqual(value.dtype, np.dtype("bool" if tag == "vb" else "float64"))
            self.assertEqual(value.shape, (2,))
            np.testing.assert_array_equal(value, expected)
        self.assertEqual(journal.events, [])
        self.assertEqual(result["work_units"], 24)
        self.assertEqual(bins.tobytes(), before)

    def test_input_rejections_charge_no_work(self):
        p = program("vector_cast")
        valid = np.array([1], dtype=np.int64)
        cases = [(True, valid), (1, valid), (np.int64(1), valid), (np.float64(1), valid), (np.int32(0), valid), (np.int32(101), np.array([101], dtype=np.int64))]
        for bins in ([], [1], np.array([], dtype=np.int64), np.array(1, dtype=np.int64), np.array([[1]], dtype=np.int64), np.array([1], dtype=np.int32), np.array([1], dtype=np.float64), np.array([1], dtype=object), np.array([0], dtype=np.int64), np.array([501], dtype=np.int64), np.ones(10001, dtype=np.int64)):
            cases.append((np.int32(1), bins))
        cases.append((np.int32(2), np.array([1], dtype=np.int64)))
        for item, bins in cases:
            work = WorkBudget()
            with self.assertRaises(InputInvalid):
                evaluate(p, item, bins, work)
            self.assertEqual(work.used, 0)

    def test_vector_length_layout_and_input_immutability(self):
        p = program("vector_cast")
        for length in (1, 2, 17, 10000):
            source = np.resize(np.array([1, 500, 5], dtype=np.int64), length)
            for bins in (source, source[::-1], source.copy()):
                before = bins.tobytes()
                result = evaluate(p, np.int32(1), bins, WorkBudget(), trace=True)
                self.assertEqual(result["scores"].shape, (length,))
                np.testing.assert_array_equal(result["scores"], bins)
                self.assertEqual(bins.tobytes(), before)

    def test_trace_classification_and_contract_faults(self):
        with WarningLog() as journal:
            result = evaluate(program("dead_warning_order"), np.int32(1), np.array([1, 5], dtype=np.int64), WorkBudget(), journal, trace=True)
        self.assertEqual([x["nan_count"] for x in result["trace"]], [1, 1, 0, 0, 0, 0, 0])
        self.assertEqual([x["positive_infinity_count"] for x in result["trace"]], [0, 0, 1, 1, 1, 1, 0])
        with self.assertRaises(ContractFault):
            evaluate({}, np.int32(1), np.array([1], dtype=np.int64), WorkBudget())
        for value, tag, n in ((np.array([1.0], dtype=np.float32), "vf64", 1), (np.array([[1.0]]), "vf64", 1), (np.array([1.0, 2.0]), "vf64", 1), (1.0, "f64", 1)):
            with self.assertRaises(ContractFault):
                check_value(value, tag, n)


class ResourceAndPackingControls(unittest.TestCase):
    def test_work_budget_constructor_and_inclusive_boundary(self):
        for limit in (-1, 5000001, True, 1.0):
            with self.assertRaises(ValueError):
                WorkBudget(limit)
        work = WorkBudget(5000000)
        work.charge(5000000)
        self.assertEqual(work.used, 5000000)
        with self.assertRaises(WorkLimit):
            work.charge(1)
        self.assertEqual(work.used, 5000000)
        for amount in (-1, True, 1.0):
            with self.assertRaises(ContractFault):
                WorkBudget().charge(amount)

    def test_every_node_including_scalar_dead_and_after_root_is_charged(self):
        for name in ("dtype_promotion", "warning_after_root", "dead_warning_order"):
            p = program(name)
            bins = np.array([1, 5], dtype=np.int64)
            exact = len(p.nodes) * len(bins)
            with WarningLog() as journal:
                result = evaluate(p, np.int32(1), bins, WorkBudget(exact), journal)
            self.assertEqual(result["work_units"], exact)
            work = WorkBudget(exact - 1)
            with WarningLog() as journal, self.assertRaises(WorkLimit):
                evaluate(p, np.int32(1), bins, work, journal)
            self.assertEqual(work.used, exact - len(bins))

    def test_64_nodes_at_maximum_vector_length(self):
        obj = base_object()
        obj["nodes"] = [["div", "bins", "c0"] for _ in range(64)]
        obj["return_node"] = 0
        p = validate_program(encode(obj))
        bins = np.ones(10000, dtype=np.int64)
        result = evaluate(p, np.int32(1), bins, WorkBudget(640000))
        self.assertEqual(result["work_units"], 640000)
        work = WorkBudget(639999)
        with self.assertRaises(WorkLimit):
            evaluate(p, np.int32(1), bins, work)
        self.assertEqual(work.used, 630000)

    def test_64_nodes_and_256_placements_at_full_feasibility(self):
        obj = base_object()
        obj["nodes"] = [["div", "bins", "c0"] for _ in range(64)]
        obj["return_node"] = 63
        p = validate_program(encode(obj))
        expected_work = 256 * 256 * 65
        self.assertEqual(expected_work, 4259840)
        work = WorkBudget(expected_work)
        result = pack(p, [1] * 256, 500, work)
        self.assertEqual(result["work_units"], expected_work)
        self.assertEqual(work.used, expected_work)
        self.assertEqual(result["placements"], 256)
        self.assertEqual(result["feasible_counts"], [256] * 256)
        self.assertEqual(result["assignment"], list(range(256)))
        self.assertEqual(result["residuals"], [499] * 256)
        self.assertEqual(result["used_bins"], 256)
        self.assertTrue(all(0 <= residual <= 500 for residual in result["residuals"]))
        self.assertEqual(sum(500 - residual for residual in result["residuals"]), 256)

    def test_empty_and_small_packing_accounting(self):
        p = program("vector_cast")
        empty = pack(p, [], 100, WorkBudget(0))
        self.assertEqual(empty, {"assignment": [], "residuals": [], "used_bins": 0, "feasible_counts": [], "work_units": 0, "placements": 0})
        # Handwritten control prefers larger residual capacities. At capacity two,
        # each item takes the earliest fresh bin. This is not a quality result.
        result = pack(p, [1, 1, 1], 2, WorkBudget(18))
        self.assertEqual(result["assignment"], [0, 1, 2])
        self.assertEqual(result["residuals"], [1, 1, 1])
        self.assertEqual(result["used_bins"], 3)
        self.assertEqual(result["feasible_counts"], [3, 3, 3])
        self.assertEqual(result["work_units"], 18)
        with self.assertRaises(WorkLimit):
            pack(p, [1, 1, 1], 2, WorkBudget(17))
        # Exact fills remove bins from feasibility, so scan and DAG charges differ.
        result = pack(p, [2, 2, 2], 2, WorkBudget(15))
        self.assertEqual(result["assignment"], [0, 1, 2])
        self.assertEqual(result["feasible_counts"], [3, 2, 1])
        self.assertEqual(result["work_units"], 9 + 3 + 2 + 1)

    def test_packing_placement_count_and_domain_limits(self):
        p = program("vector_cast")
        result = pack(p, [1] * 256, 1, WorkBudget())
        self.assertEqual(result["placements"], 256)
        self.assertEqual(result["used_bins"], 256)
        self.assertEqual(result["assignment"], list(range(256)))
        self.assertEqual(result["work_units"], 256 * 256 + 256 * 257 // 2)
        cases = [([1] * 257, 1), ((1,), 1), ([True], 1), ([np.int32(1)], 1), ([0], 1), ([101], 500), ([2], 1), ([1], 0), ([1], 501), ([1], True), ([1], 1.0)]
        for items, capacity in cases:
            work = WorkBudget()
            with self.assertRaises(InputInvalid):
                pack(p, items, capacity, work)
            self.assertEqual(work.used, 0)

    def test_warning_order_across_placements(self):
        with WarningLog() as journal:
            result = pack(program("dead_warning_order"), [1, 1, 1], 2, WorkBudget(), journal)
        self.assertEqual(result["placements"], 3)
        self.assertEqual([(e[0], e[1]) for e in journal.events], [(placement, node) for placement in range(3) for node in range(6)])

    def test_default_12000_warning_event_boundary(self):
        obj = base_object()
        obj["constants"] = [{"type": "f64", "value": -1}, {"type": "f64", "value": 1}]
        obj["nodes"] = [["sqrt", "c0"] for _ in range(63)] + [["div", "bins", "c1"]]
        obj["return_node"] = 63
        p = validate_program(encode(obj))
        journal = WarningLog()
        work = WorkBudget()
        result = None
        old_showwarning = pywarnings.showwarning
        with self.assertRaises(DiagnosticLimit), journal:
            result = pack(p, [1] * 256, 500, work, journal)
        self.assertIsNone(result)
        self.assertEqual(journal.max_events, 12000)
        self.assertEqual(len(journal.events), 12000)
        self.assertEqual(len(journal.kinds), 1)
        self.assertEqual(journal.events, [[index // 63, index % 63, 0] for index in range(12000)])
        self.assertEqual(journal.events[-1], [190, 29, 0])
        self.assertEqual((journal.current_placement, journal.current_node), (190, 30))
        self.assertFalse(journal.payload()["complete"])
        self.assertEqual(journal.payload()["incomplete_reason"], "warning event bound")
        # 190 complete placements, then a feasibility scan and the first 31
        # warning nodes of placement 190. Its vector root never executes.
        self.assertEqual(work.used, (190 * 65 + 1 + 31) * 256)
        self.assertEqual(work.used, 3169792)
        self.assertIs(pywarnings.showwarning, old_showwarning)

    def test_warning_budget_failure_is_explicit_and_state_restored(self):
        old_showwarning = pywarnings.showwarning
        for kwargs, reason in (({"max_events": 1}, "warning event bound"), ({"max_kinds": 0}, "warning kind bound"), ({"max_text": 1}, "warning text bound")):
            journal = WarningLog(**kwargs)
            with self.assertRaises(DiagnosticLimit), journal:
                evaluate(program("dead_warning_order"), np.int32(1), np.array([1], dtype=np.int64), WorkBudget(), journal)
            self.assertFalse(journal.payload()["complete"])
            self.assertEqual(journal.payload()["incomplete_reason"], reason)
            self.assertIs(pywarnings.showwarning, old_showwarning)
        with self.assertRaises(UnexpectedWarning), WarningLog():
            pywarnings.warn("handwritten unexpected-source control", UserWarning)
        self.assertIs(pywarnings.showwarning, old_showwarning)


if __name__ == "__main__":
    unittest.main()
