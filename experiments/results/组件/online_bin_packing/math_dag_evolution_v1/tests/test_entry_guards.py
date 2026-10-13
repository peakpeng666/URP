"""Pure-stdlib entry, reservation, and response-decoding regression tests.

No approval here authorizes a real study: approval documents are temporary fake
fixtures, execute is always mocked, and renderer/tokenizer/backend imports are
forbidden-call stubs. Decode inputs are clearly labelled offline copies of the
saved v2 smoke response with handwritten metadata mutations. No HTTP, tokenizer,
model, NumPy, numerical interpreter, or scoring worker is invoked.
"""

from contextlib import redirect_stdout
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import guard


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


entry = load_module("study_entry_guards_under_test", ROOT / "run_study.py")
FORBIDDEN_RENDERER = mock.Mock(side_effect=AssertionError("Renderer must not run in pure decoding tests"))
FORBIDDEN_TOKENIZER = mock.Mock(side_effect=AssertionError("Tokenizer must not run in pure decoding tests"))
FORBIDDEN_BACKEND = mock.Mock(side_effect=AssertionError("Backend must not run in pure decoding tests"))
jinja_stub = types.ModuleType("jinja2")
jinja_stub.__path__ = []
sandbox_stub = types.ModuleType("jinja2.sandbox")
sandbox_stub.ImmutableSandboxedEnvironment = FORBIDDEN_RENDERER
tokenizer_stub = types.ModuleType("tokenizer_runtime")
tokenizer_stub.request = FORBIDDEN_TOKENIZER
backend_stub = types.ModuleType("backend")
backend_stub.run_once = FORBIDDEN_BACKEND
with mock.patch.dict(sys.modules, {
    "jinja2": jinja_stub,
    "jinja2.sandbox": sandbox_stub,
    "tokenizer_runtime": tokenizer_stub,
    "backend": backend_stub,
}):
    generation = load_module("study_decode_guards_under_test", ROOT / "src" / "generation.py")

FAKE_FREEZE_SHA256 = "a" * 64


class ApprovalAndEntryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="entry_guard_fixture_", dir=ROOT / "logs")
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "fake_approval.json"
        self.approval = {
            "authorized": True,
            "scope": "p3_math_dag_twogen_22_once",
            "freeze_sha256": FAKE_FREEZE_SHA256,
            "run_id": "handwritten_test_only_01",
        }

    def write(self, document):
        self.path.write_text(json.dumps(document))

    def test_matching_explicit_scope_freeze_and_run_id_are_required(self):
        self.write(self.approval)
        self.assertEqual(entry.authorize(self.path, FAKE_FREEZE_SHA256), self.approval)
        for key, value in (("authorized", False), ("authorized", 1), ("scope", "other_scope"), ("freeze_sha256", "b" * 64)):
            wrong = dict(self.approval, **{key: value})
            self.write(wrong)
            with self.subTest(key=key, value=value):
                with self.assertRaisesRegex(ValueError, "explicit matching study approval required"):
                    entry.authorize(self.path, FAKE_FREEZE_SHA256)

    def test_run_id_rejects_paths_whitespace_empty_and_overlong_values(self):
        for value in ("", "../outside", "a/b", "two words", "a" * 65, "newline\n"):
            self.write(dict(self.approval, run_id=value))
            with self.subTest(run_id=value):
                with self.assertRaisesRegex(ValueError, "explicit matching study approval required"):
                    entry.authorize(self.path, FAKE_FREEZE_SHA256)
        self.write(dict(self.approval, run_id="a" * 64))
        self.assertEqual(entry.authorize(self.path, FAKE_FREEZE_SHA256)["run_id"], "a" * 64)

    def test_approval_size_10000_is_accepted_and_10001_rejected(self):
        raw = json.dumps(self.approval).encode()
        self.path.write_bytes(raw + b" " * (10000 - len(raw)))
        self.assertEqual(entry.authorize(self.path, FAKE_FREEZE_SHA256), self.approval)
        self.path.write_bytes(raw + b" " * (10001 - len(raw)))
        with self.assertRaisesRegex(ValueError, "file size bound"):
            entry.authorize(self.path, FAKE_FREEZE_SHA256)

    def test_default_main_only_verifies_and_never_authorizes_or_executes(self):
        output = io.StringIO()
        with mock.patch.object(sys, "argv", ["run_study.py", "--freeze-sha256", FAKE_FREEZE_SHA256]), \
             mock.patch.object(entry, "verify", return_value={}) as verify, \
             mock.patch.object(entry, "bounded_json", return_value={"mock": True}) as read_plan, \
             mock.patch.object(entry, "authorize", side_effect=AssertionError("No approval lookup allowed")) as authorize, \
             mock.patch.object(entry, "execute", side_effect=AssertionError("No execution allowed")) as execute, \
             redirect_stdout(output):
            entry.main()
        verify.assert_called_once_with(FAKE_FREEZE_SHA256)
        read_plan.assert_called_once_with(ROOT / "protocol.json")
        authorize.assert_not_called()
        execute.assert_not_called()
        self.assertEqual(json.loads(output.getvalue()), {
            "status": "verified_sources_only", "model_calls": 0,
            "score_calls": 0, "planned_model_calls_max": 22,
        })

    def test_execute_flag_without_approval_still_never_executes(self):
        with mock.patch.object(sys, "argv", ["run_study.py", "--freeze-sha256", FAKE_FREEZE_SHA256, "--execute-approved"]), \
             mock.patch.object(entry, "verify", return_value={}), \
             mock.patch.object(entry, "bounded_json", return_value={"mock": True}), \
             mock.patch.object(entry, "execute", side_effect=AssertionError("No execution allowed")) as execute:
            with self.assertRaisesRegex(ValueError, "approval file required"):
                entry.main()
        execute.assert_not_called()


class FakeClocks:
    def __init__(self):
        self.wall = 100.0
        self.own = 10.0
        self.child = 20.0

    def advance(self, *, wall=0.0, own=0.0, child=0.0):
        self.wall += wall
        self.own += own
        self.child += child


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((ROOT / "protocol.json").read_bytes())
        self.clocks = FakeClocks()
        self.budget = guard.Budget(self.plan, clock=lambda: self.clocks.wall, own=lambda: self.clocks.own, children=lambda: self.clocks.child)

    def test_frozen_debit_reserve_and_whole_stage_limits(self):
        budgets = self.plan["aggregate_budgets"]
        self.assertEqual(budgets["preparation_debit"], {"cpu_seconds": 200, "active_wall_seconds": 200})
        self.assertEqual(budgets["final_accounting_reserve"], {"cpu_seconds": 120, "wall_seconds": 120})
        self.assertEqual(budgets["reserve_before_model_call"], {"cpu_seconds": 245, "wall_seconds": 131})
        self.assertEqual(budgets["reserve_before_score_call"], {"cpu_seconds": 20, "wall_seconds": 31})
        self.assertEqual((budgets["whole_study_observed_cpu_seconds"], budgets["whole_study_active_wall_seconds"]), (5900, 3660))

    def test_model_reservation_accepts_exact_cpu_and_wall_boundary_including_both_reserves(self):
        # 5335 + 200 debit + 245 call + 120 final = 5900 CPU.
        # 3209 + 200 debit + 131 call + 120 final = 3660 wall.
        self.clocks.advance(own=100, child=5235, wall=3209)
        self.budget.reserve("model")
        self.clocks.advance(own=0.5)
        with self.assertRaisesRegex(RuntimeError, "whole CPU reservation unavailable"):
            self.budget.reserve("model")
        self.clocks.own -= 0.5
        self.clocks.advance(wall=0.5)
        with self.assertRaisesRegex(RuntimeError, "whole wall reservation unavailable"):
            self.budget.reserve("model")

    def test_score_reservation_accepts_exact_global_and_score_stage_boundaries(self):
        self.clocks.advance(own=5560, wall=3309)
        self.budget.score_cpu = 280
        self.budget.score_wall = 569
        self.budget.reserve("score")
        self.budget.score_cpu = 280.5
        with self.assertRaisesRegex(RuntimeError, "score stage reservation unavailable"):
            self.budget.reserve("score")
        self.budget.score_cpu = 280
        self.budget.score_wall = 569.5
        with self.assertRaisesRegex(RuntimeError, "score stage reservation unavailable"):
            self.budget.reserve("score")

    def test_score_charge_uses_fake_observed_own_child_and_wall_deltas(self):
        mark = self.budget.score_mark()
        self.clocks.advance(own=2, child=3, wall=7)
        self.budget.score_charge(mark)
        measured = self.budget.measured()
        self.assertEqual(measured, {
            "supervisor_cpu_seconds": 2, "children_cpu_seconds": 3,
            "active_wall_seconds": 7, "score_cpu_seconds": 5, "score_wall_seconds": 7,
        })
        terminal = self.budget.terminal()
        self.assertEqual(terminal["charged_cpu_seconds"], 205)
        self.assertEqual(terminal["charged_active_wall_seconds"], 207)
        self.assertTrue(terminal["within_charged_budget"])

    def test_terminal_debit_exact_budget_boundary_and_overrun(self):
        self.clocks.advance(own=5700, wall=3460)
        terminal = self.budget.terminal()
        self.assertEqual((terminal["charged_cpu_seconds"], terminal["charged_active_wall_seconds"]), (5900, 3660))
        self.assertTrue(terminal["within_charged_budget"])
        self.clocks.advance(child=0.5)
        self.assertFalse(self.budget.terminal()["within_charged_budget"])


class OfflineDecodeTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((ROOT / "protocol.json").read_bytes())
        self.slot = copy.deepcopy(self.plan["slots"][0])
        self.saved = ROOT / "interface_smoke_v2" / "runs" / "attempt01"
        raw = (self.saved / "response_body.json").read_bytes()
        self.saved_hash = hashlib.sha256(raw).hexdigest()
        self.body = json.loads(raw)
        self.execution = json.loads((self.saved / "result.json").read_bytes())
        # MOCK ONLY: adapt saved 128-token smoke metadata to the frozen formal
        # request profile; no new response is obtained and no file is rewritten.
        self.body["generation_settings"] = dict(copy.deepcopy(self.plan["sampling_base_profile"]), seed=self.slot["seed"])
        self.body["model"] = self.plan["command"][self.plan["command"].index("-m") + 1]
        self.prepared = {
            "prompt_tokens": self.body["tokens_evaluated"],
            "rendered_sha256": hashlib.sha256(self.body["prompt"].encode()).hexdigest(),
        }

    def tearDown(self):
        FORBIDDEN_RENDERER.assert_not_called()
        FORBIDDEN_TOKENIZER.assert_not_called()
        FORBIDDEN_BACKEND.assert_not_called()
        self.assertEqual(hashlib.sha256((self.saved / "response_body.json").read_bytes()).hexdigest(), self.saved_hash)

    def decode(self):
        return generation.decode(self.slot, json.dumps(self.body).encode(), self.execution, self.prepared, self.plan)

    def set_limit_output(self, count):
        self.body.update(tokens_predicted=count, tokens=[42] * count, stop=True, stop_type="limit", truncated=False)
        self.body["timings"]["predicted_n"] = count

    def test_saved_v2_response_as_labelled_mock_passes_pure_transport_decoding(self):
        self.assertEqual(self.saved_hash, "1b6a79bacecf34c854dc1242eda03b81c3c2b7925faf4844db72ee920cb0110f")
        outcome = self.decode()
        self.assertEqual(outcome["status"], "completed_valid_transport")
        self.assertEqual(outcome["content"], self.body["content"].encode())
        self.assertEqual(outcome["metadata"]["tokens_predicted"], 47)

    def test_385_output_tokens_are_an_infrastructure_violation_not_ordinary_limit_stop(self):
        self.set_limit_output(385)
        with self.assertRaisesRegex(ValueError, "output token ceiling violation"):
            self.decode()

    def test_384_output_tokens_with_legitimate_limit_stop_remain_ordinary(self):
        self.set_limit_output(384)
        outcome = self.decode()
        self.assertEqual(outcome["status"], "model_limit_stop")
        self.assertIsNone(outcome["content"])
        self.assertEqual(outcome["metadata"]["tokens_predicted"], 384)

    def test_premature_383_token_limit_stop_is_infrastructure_failure(self):
        self.set_limit_output(383)
        with self.assertRaisesRegex(ValueError, "premature or inconsistent limit stop"):
            self.decode()


if __name__ == "__main__":
    unittest.main()
