"""Handwritten fake-executor tests: this module never launches a worker.

Real packing and process-fault checks live only in validate_manual.py, where
each attempt and its cost is retained. These fixtures use three tiny synthetic
slots, never the prepared thirty-slot population or a benchmark input file.
"""

import copy
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from integrity import digest, verify
from run_batch import claim_approval, execute, finalize_budget, validate_approval
from runtime import AS, strict_json
import run_batch

METHOD = "EOH_formula_reimplementation"
SCOPE = "p3_eoh_formula_reimplementation_30_v1"


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class Operational(unittest.TestCase):
    def setUp(self):
        # Any accidental real subprocess is an immediate unit-test failure.
        self.spawn_guard = patch("subprocess.Popen", side_effect=AssertionError(
            "fake-executor unit tests must never dispatch a real worker"))
        self.spawn_guard.start()
        self.addCleanup(self.spawn_guard.stop)

    def make(self):
        slots = [{"id": f"handwritten{i}", "index": i, "instance_id": "micro",
                  "items_sha256": "handwritten", "n": 2, "capacity": 5,
                  "method": METHOD, "status": "not_run_pending_authorization"}
                 for i in range(3)]
        return slots, {"micro": {"items": [4, 1]}}

    def fake(self, *args):
        return {
            "pid": 123, "returncode": 0, "termination": None, "error": None,
            "reaped": True, "worker_cpu_seconds": 1.0,
            "cpu_evidence_complete": True, "worker_peak_rss_kib": 1000,
            "wall_seconds": 0.01, "cleanup_seconds": 0.0,
            "raw_output_sha256": "a" * 64, "raw_output_bytes": 0,
            "stderr_bytes": 0, "stderr_sha256": "b" * 64,
            "raw_stdout_base64": "", "raw_stderr_base64": "", "stderr_text": "",
            "result": {
                "method": METHOD, "pid": 123, "error": None,
                "assignment": [0, 1], "used_bins": 2, "residuals": [1, 4],
                "feasible_counts": [2, 2], "n_bin_feasibility_checks": 4,
                "warnings": {"kinds": [], "events": [], "complete": True,
                             "bound_error": None},
                "effective_limits": {"RLIMIT_AS": [AS, AS], "RLIMIT_CPU": [20, 20],
                                     "RLIMIT_FSIZE": [0, 0], "RLIMIT_NOFILE": [32, 32]},
            },
        }

    def runfake(self, executor=None, check=lambda: None, **kwargs):
        with tempfile.TemporaryDirectory(prefix="eoh_handwritten_fake_") as directory:
            out = pathlib.Path(directory)
            (out / "observations").mkdir()
            slots, instances = self.make()
            return execute(slots, instances, out, check,
                           executor=executor or self.fake, **kwargs)

    def assert_failed_first(self, report):
        self.assertEqual(report["requests_dispatched"], 1)
        self.assertEqual(report["completed_valid"], 0)
        self.assertEqual(report["rows"][0]["status"], "failed")
        self.assertEqual(report["rows"][1]["status"], "not_run_failure")
        self.assertFalse(report["certified_complete"])
        self.assertEqual(report["groups"], [])

    def test_fake_success_is_not_benchmark_certification(self):
        report = self.runfake()
        self.assertEqual(report["completed_valid"], 3)
        self.assertEqual(report["requests_dispatched"], 3)
        self.assertIsNone(report["stop_reason"])
        self.assertFalse(report["certified_complete"])
        self.assertEqual(report["groups"], [])
        self.assertEqual(report["cost"]["worker_cpu_seconds"], 3.0)
        self.assertTrue(report["cost"]["worker_cpu_evidence_complete"])

    def test_input_slots_are_not_mutated(self):
        slots, instances = self.make()
        before = copy.deepcopy((slots, instances))
        with tempfile.TemporaryDirectory() as directory:
            out = pathlib.Path(directory)
            (out / "observations").mkdir()
            execute(slots, instances, out, lambda: None, executor=self.fake)
        self.assertEqual((slots, instances), before)

    def test_executor_exception_keeps_cpu_unknown(self):
        def fail(*args):
            raise OSError("no returned execution observation")
        report = self.runfake(executor=fail)
        self.assert_failed_first(report)
        self.assertEqual(report["execution_counts"]["requests_without_returned_execution_evidence"], 1)
        self.assertFalse(report["cost"]["worker_cpu_evidence_complete"])
        self.assertTrue(report["cost"]["worker_cpu_sum_is_lower_bound_if_incomplete"])

    def test_cpu_reservation_before_first(self):
        report = self.runfake(budget_cpu=19.9)
        self.assertEqual(report["requests_dispatched"], 0)
        self.assertEqual(report["rows"][0]["status"], "not_run_budget_reservation")

    def test_cpu_reservation_before_next(self):
        report = self.runfake(budget_cpu=20.5)
        self.assertEqual(report["requests_dispatched"], 1)
        self.assertEqual(report["rows"][1]["status"], "not_run_budget_reservation")

    def test_wall_reservation_before_first(self):
        report = self.runfake(budget_wall=30.9)
        self.assertEqual(report["requests_dispatched"], 0)

    def test_wall_reservation_before_next(self):
        clock = Clock()
        def slow(*args):
            clock.t += 2
            return self.fake(*args)
        report = self.runfake(executor=slow, clock=clock, budget_wall=32)
        self.assertEqual(report["requests_dispatched"], 1)

    def test_predispatch_integrity_failure_launches_nothing(self):
        def changed():
            raise ValueError("changed frozen source")
        report = self.runfake(check=changed)
        self.assertEqual(report["requests_dispatched"], 0)
        self.assertEqual(report["stop_reason"], "integrity_failure")
        self.assertTrue(report["cost"]["worker_cpu_evidence_complete"])

    def test_final_integrity_failure_invalidates(self):
        calls = [0]
        def changed():
            calls[0] += 1
            if calls[0] == 4:
                raise ValueError("changed after final request")
        report = self.runfake(check=changed)
        self.assertEqual(report["completed_valid"], 3)
        self.assertEqual(report["stop_reason"], "integrity_failure")
        self.assertFalse(report["certified_complete"])
        self.assertEqual(report["groups"], [])

    def test_observation_failures_never_pass(self):
        changes = (("returncode", 7), ("termination", "wall_timeout"),
                   ("error", "handwritten failure"), ("reaped", False),
                   ("cpu_evidence_complete", False))
        for key, value in changes:
            with self.subTest(key=key):
                def invalid(*args):
                    result = self.fake(*args)
                    result[key] = value
                    return result
                self.assert_failed_first(self.runfake(executor=invalid))

    def test_wrong_method_pid_or_incomplete_warning_journal_fails(self):
        changes = (("method", "BF"), ("pid", 999),
                   ("warnings", {"kinds": [], "events": [], "complete": False,
                                 "bound_error": "handwritten warning overflow"}))
        for key, value in changes:
            with self.subTest(key=key):
                def invalid(*args):
                    observation = self.fake(*args)
                    observation["result"][key] = value
                    return observation
                self.assert_failed_first(self.runfake(executor=invalid))

    def test_invalid_assignment_or_residuals_fails(self):
        changes = (("assignment", [0, 0]), ("residuals", [0, 5]),
                   ("used_bins", 1))
        # [0,0] is feasible in C5 but contradicts the independently checked
        # claimed two-bin result; this deliberately tests metadata consistency.
        for key, value in changes:
            with self.subTest(key=key):
                def invalid(*args):
                    observation = self.fake(*args)
                    observation["result"][key] = value
                    return observation
                self.assert_failed_first(self.runfake(executor=invalid))

    def test_wrong_limits_or_work_count_fails(self):
        changes = (("effective_limits", {}), ("feasible_counts", [2]),
                   ("n_bin_feasibility_checks", 3))
        for key, value in changes:
            with self.subTest(key=key):
                def invalid(*args):
                    observation = self.fake(*args)
                    observation["result"][key] = value
                    return observation
                self.assert_failed_first(self.runfake(executor=invalid))

    def test_observation_persistence_failure_preserves_execution(self):
        real = run_batch.save
        def fail(path, value):
            if path.parent.name == "observations":
                raise OSError("injected observation persistence failure")
            return real(path, value)
        with patch("run_batch.save", side_effect=fail):
            report = self.runfake()
        self.assert_failed_first(report)
        self.assertEqual(report["rows"][0]["execution"]["pid"], 123)
        self.assertEqual(report["cost"]["worker_cpu_seconds"], 1.0)

    def test_start_journal_failure_prevents_dispatch(self):
        class BadJournal(io.StringIO):
            def write(self, value):
                raise OSError("injected start event failure")
        real = pathlib.Path.open
        def patched_open(path, *args, **kwargs):
            if path.name == "events.jsonl":
                return BadJournal()
            return real(path, *args, **kwargs)
        with patch.object(pathlib.Path, "open", patched_open):
            report = self.runfake()
        self.assertEqual(report["requests_dispatched"], 0)
        self.assertEqual(report["stop_reason"], "persistence_failure")

    def test_checkpoint_failure_preserves_execution(self):
        real = run_batch.save
        def fail(path, value):
            if path.name == "ledger_checkpoint.json":
                raise OSError("injected checkpoint failure")
            return real(path, value)
        with patch("run_batch.save", side_effect=fail):
            report = self.runfake()
        self.assertEqual(report["requests_dispatched"], 1)
        self.assertEqual(report["stop_reason"], "persistence_failure")
        self.assertEqual(report["rows"][0]["execution"]["pid"], 123)

    def test_report_failure_cannot_certify(self):
        real = run_batch.save
        def fail(path, value):
            if path.name == "report.json":
                raise OSError("injected report failure")
            return real(path, value)
        with patch("run_batch.save", side_effect=fail):
            report = self.runfake()
        self.assertEqual(report["stop_reason"], "persistence_failure")
        self.assertFalse(report["certified_complete"])
        self.assertEqual(report["cost"]["worker_cpu_seconds"], 3.0)

    def test_final_integrity_wall_cost_is_charged(self):
        clock, calls = Clock(), [0]
        def costly_check():
            calls[0] += 1
            if calls[0] == 4:
                clock.t += 700
        report = self.runfake(check=costly_check, clock=clock)
        self.assertEqual(report["requests_dispatched"], 3)
        self.assertEqual(report["stop_reason"], "observed_budget_exceeded")
        self.assertFalse(report["certified_complete"])

    def test_final_integrity_cpu_cost_is_charged(self):
        clock, calls = Clock(), [0]
        def costly_check():
            calls[0] += 1
            if calls[0] == 4:
                clock.t += 400
        report = self.runfake(check=costly_check, cpuclock=clock)
        self.assertEqual(report["stop_reason"], "observed_budget_exceeded")

    def test_whole_stage_overrun_invalidates(self):
        report = {"stop_reason": None, "certified_complete": True, "groups": [1]}
        finalize_budget(report, 301, 601, 300, 600)
        self.assertFalse(report["certified_complete"])
        self.assertEqual(report["groups"], [])

    def test_strict_json_rejects_duplicate_keys_at_every_depth(self):
        for raw in (b'{"a":1,"a":2}', b'{"outer":{"a":1,"a":2}}',
                    b'{"outer":[{"a":1,"a":2}]}'):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    strict_json(raw)

    def test_strict_json_rejects_nonfinite_literals_and_overflow_floats(self):
        for token in (b"NaN", b"Infinity", b"-Infinity", b"1e9999", b"-1e9999"):
            with self.subTest(token=token):
                with self.assertRaises(ValueError):
                    strict_json(b'{"value":' + token + b'}')

    def test_strict_json_accepts_finite_nested_payload(self):
        raw = b'{"zero":-0.0,"finite":1.25,"large":1e308,"nested":[1,true,null]}'
        self.assertEqual(strict_json(raw), {
            "zero": -0.0, "finite": 1.25, "large": 1e308,
            "nested": [1, True, None],
        })

    def approval(self):
        return {"freeze_sha256": "a" * 64, "scope": SCOPE, "max_requests": 30,
                "authorized": True, "run_id": "handwritten_test"}

    def test_approval_exact_scope_hash_and_limit(self):
        approval = self.approval()
        self.assertEqual(validate_approval(json.dumps(approval).encode(), "a" * 64), approval)
        for key, value in (("authorized", False), ("freeze_sha256", "b" * 64),
                           ("scope", "other"), ("max_requests", 31),
                           ("run_id", "../unsafe")):
            with self.subTest(key=key):
                changed = dict(approval)
                changed[key] = value
                with self.assertRaises(ValueError):
                    validate_approval(json.dumps(changed).encode(), "a" * 64)

    def test_approval_marker_single_use(self):
        approval = self.approval()
        raw = json.dumps(approval).encode()
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory)
            marker = claim_approval(raw, approval, path, path / "uses")
            before = marker.read_bytes()
            with self.assertRaises(FileExistsError):
                claim_approval(raw, approval, path, path / "uses")
            self.assertEqual(marker.read_bytes(), before)

    def test_manifest_replacement_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "freeze.json"
            contents = {
                "files": [], "runtime_roots": {}, "runtime_files": {}, "references": {},
                "python_executable": sys.executable,
                "python_prefix": sys.prefix,
                "python_base_prefix": sys.base_prefix,
                "python_exec_prefix": sys.exec_prefix,
                "python_base_exec_prefix": sys.base_exec_prefix,
                "python_executable_sha256": digest(sys.executable),
            }
            path.write_text(json.dumps(contents))
            expected = digest(path)
            verify(path, expected)
            contents["replacement"] = True
            path.write_text(json.dumps(contents))
            with self.assertRaises(ValueError):
                verify(path, expected)


if __name__ == "__main__":
    unittest.main()
