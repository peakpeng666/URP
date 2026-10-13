"""Source-only prospective tests of the fixed study state machine.

All generate/score/load_validation/emit adapters below are handwritten in-memory
fakes. They do not generate model candidates, evaluate mathematical graphs, load
the real validation panel, launch any process, or make network requests. Every
reported packing result is invented. Running this suite needs separate approval.

These tests verify sequencing and accounting at the trusted callback boundary.
They cannot establish OS resource isolation, actual durable persistence, adapter
integrity, native numerical behavior, tokenizer settings, or physical dispatch
counts below that boundary; those require separately authorized operational work.
"""

from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import pipeline
import policy


FF = {
    "schema": "math-dag-v1",
    "description": "Choose the earliest feasible bin with equal scores.",
    "constants": [{"type": "f64", "value": 0}],
    "nodes": [["mul", "bins", "c0"]],
    "return_node": 0,
}
BF = {
    "schema": "math-dag-v1",
    "description": "Choose the feasible bin with the smallest remaining capacity.",
    "constants": [{"type": "f64", "value": -1}],
    "nodes": [["mul", "bins", "c0"]],
    "return_node": 0,
}
LONG_BF = {
    "schema": "math-dag-v1",
    "description": "Handwritten redundant best-fit representation for sequencing tests.",
    "constants": [{"type": "f64", "value": -1}, {"type": "f64", "value": 0}],
    "nodes": [["mul", "bins", "c0"], ["add", 0, "c1"]],
    "return_node": 1,
}
VALIDATION_IDS = [f"handwritten_validation_{index}" for index in range(4)]
FAKE_BOUNDS = (50, 10, 60, 12)
EMPTY_WARNING_TRACE_SHA256 = hashlib.sha256(b'{"events":[]}').hexdigest()


def encode(graph):
    return json.dumps(graph, separators=(",", ":"), allow_nan=False).encode()


class ReserveUnavailable(RuntimeError):
    """Handwritten adapter's pre-dispatch resource reservation failure."""


class Adapters:
    """Trusted pure-data fakes; failures are explicit and never retried here."""

    def __init__(self):
        self.plan = json.loads((ROOT / "protocol.json").read_bytes())
        self.design = json.loads((ROOT / "data" / "design.json").read_bytes())["cases"]
        # The mock plan explicitly binds synthetic validation identifiers. The
        # frozen on-disk protocol and real validation panel are never changed.
        self.plan["data"]["validation_case_ids"] = list(VALIDATION_IDS)
        self.validation = [{"id": case_id, "split": "validation"} for case_id in VALIDATION_IDS]
        self.trace = []
        self.model_calls = []
        self.score_calls = []
        self.events = []
        self.validation_loads = 0
        self.validation_load_state = None
        self.commitment_saved = False
        self.saved_commitment = None
        self.generation_outcomes = {}
        self.score_exceptions = {}
        self.score_statuses = {}
        self.source_used_override = {}
        self.validation_used_override = {}
        self.assignment_override = {}
        self.case_id_override = {}
        self.checked_overrides = {}
        self.fail_event = None
        self.validation_exception = None
        self.study = pipeline.Study(
            self.plan, self.design, list(VALIDATION_IDS),
            self.generate, self.score, self.load_validation, self.emit,
        )

    def generate(self, slot, prompt, index):
        self.trace.append(("generate", slot["slot_id"]))
        self.model_calls.append({"slot": copy.deepcopy(slot), "prompt": prompt, "index": index})
        outcome = self.generation_outcomes.get(slot["slot_id"], encode(BF))
        if isinstance(outcome, Exception):
            raise outcome
        if type(outcome) is bytes:
            return {"status": "completed_valid_transport", "content": outcome, "evidence": {"fake": True, "slot_seed": slot["seed"]}}
        return {"status": outcome, "evidence": {"fake": True, "slot_seed": slot["seed"]}}

    def score(self, record, case, index):
        self.trace.append(("score", record["source_id"], case["id"]))
        self.score_calls.append({
            "source_id": record["source_id"], "case_id": case["id"],
            "index": index, "phase": self.study.phase,
            "graph_identity": record["graph_identity"],
            "raw_sha256": record["raw_sha256"],
        })
        if index in self.score_exceptions:
            raise self.score_exceptions[index]
        ids = VALIDATION_IDS if case["id"] in VALIDATION_IDS else self.study.design_ids
        position = ids.index(case["id"])
        # Invented deterministic design outcomes keyed by representation. They
        # are not mathematical claims about these handwritten equivalent DAGs.
        used = (53, 12, 64, 14) if record["graph_identity"] == policy.graph_identity(encode(FF)) else (51, 11, 62, 13)
        if record["graph_identity"] == policy.graph_identity(encode(LONG_BF)):
            used = (50, 10, 60, 12)
        used = self.source_used_override.get(record["source_id"], used)
        if case["id"] in VALIDATION_IDS:
            used = self.validation_used_override.get(record["graph_identity"], used)
        assignment = [(item % used[position]) for item in range(128)]
        assignment = self.assignment_override.get((record["source_id"], case["id"]), assignment)
        checked = {
            "case_id": self.case_id_override.get(index, case["id"]),
            "status": self.score_statuses.get((record["source_id"], case["id"]), "completed_valid"),
            "used_bins": used[position], "L1": FAKE_BOUNDS[position],
            "assignment": list(assignment),
            "residuals": [0] * used[position],
            "work_units": 128 * len(json.loads(record["program_json"])["nodes"]),
            "warning_events": 0,
            "warning_trace_sha256": EMPTY_WARNING_TRACE_SHA256,
            "complete_semantic_measurement": True,
        }
        checked.update(copy.deepcopy(self.checked_overrides.get(index, {})))
        return checked, {"fake": True, "adapter_index": index}

    def load_validation(self):
        self.trace.append(("load_validation",))
        self.validation_loads += 1
        self.validation_load_state = {
            "commitment_persisted": self.study.commitment_persisted,
            "ledger": copy.deepcopy(self.study.ledger),
        }
        if not self.commitment_saved:
            raise AssertionError("Validation attempted before successful commitment sink")
        if self.validation_exception is not None:
            raise self.validation_exception
        return copy.deepcopy(self.validation)

    def emit(self, event, payload):
        self.trace.append(("emit", event))
        self.events.append((event, copy.deepcopy(payload)))
        if event == self.fail_event:
            raise OSError("handwritten persistence failure: " + event)
        if event == "winner_commitment":
            self.commitment_saved = True
            self.saved_commitment = copy.deepcopy(payload)

    def run(self):
        return self.study.run()


class PipelineTestCase(unittest.TestCase):
    def assertNoValidation(self, adapters):
        self.assertEqual(adapters.validation_loads, 0)
        self.assertFalse(any(row["case_id"] in VALIDATION_IDS for row in adapters.score_calls))

    def request(self, result, source_id):
        return next(row for row in result["requests"] if row["slot_id"] == source_id)

    def candidate_rows(self, result, source_id, split="design"):
        return [row for row in result["ledger"] if row["role"] == "candidate" and row["source_id"] == source_id and row["split"] == split]


class FixedAccountingTests(PipelineTestCase):
    def test_constructor_rejects_wrong_or_reordered_design_binding(self):
        fake = Adapters()
        wrong = copy.deepcopy(fake.design)
        wrong[0]["id"] = "wrong_design_id"
        for design in (wrong, list(reversed(fake.design))):
            with self.subTest(ids=[case["id"] for case in design]):
                with self.assertRaisesRegex(ValueError, "protocol split ID/order binding"):
                    pipeline.Study(fake.plan, design, list(VALIDATION_IDS), fake.generate, fake.score, fake.load_validation, fake.emit)
        self.assertEqual(fake.trace, [])

    def test_constructor_rejects_wrong_or_reordered_validation_binding(self):
        fake = Adapters()
        wrong = ["wrong_validation_id"] + VALIDATION_IDS[1:]
        for validation_ids in (wrong, list(reversed(VALIDATION_IDS))):
            with self.subTest(ids=validation_ids):
                with self.assertRaisesRegex(ValueError, "protocol split ID/order binding"):
                    pipeline.Study(fake.plan, fake.design, validation_ids, fake.generate, fake.score, fake.load_validation, fake.emit)
        self.assertEqual(fake.trace, [])

    def test_constructor_rejects_duplicate_or_overlapping_split_ids(self):
        fake = Adapters()
        duplicate_design = copy.deepcopy(fake.design)
        duplicate_design[1]["id"] = duplicate_design[0]["id"]
        variants = (
            (duplicate_design, list(VALIDATION_IDS)),
            (fake.design, [VALIDATION_IDS[0]] * 4),
            (fake.design, [fake.design[0]["id"]] + VALIDATION_IDS[1:]),
        )
        for design, validation_ids in variants:
            with self.subTest(design_ids=[case["id"] for case in design], validation_ids=validation_ids):
                with self.assertRaisesRegex(ValueError, "fixed split IDs"):
                    pipeline.Study(fake.plan, design, validation_ids, fake.generate, fake.score, fake.load_validation, fake.emit)
        self.assertEqual(fake.trace, [])

    def test_initialization_predeclares_22_requests_and_all_208_rows(self):
        fake = Adapters()
        self.assertEqual(len(fake.study.requests), 22)
        self.assertEqual(len(fake.study.ledger), 208)
        self.assertEqual(Counter(row["role"] for row in fake.study.ledger), {"candidate": 176, "comparator": 24, "winner": 8})
        self.assertTrue(all(row["status"] == "not_run" for row in fake.study.requests + fake.study.ledger))
        self.assertEqual(fake.model_calls, [])
        self.assertEqual(fake.score_calls, [])
        self.assertFalse(fake.study.commitment_persisted)
        self.assertNoValidation(fake)

    def test_complete_run_calls_22_model_adapters_120_score_adapters_and_keeps_208_rows(self):
        fake = Adapters()
        result = fake.run()
        self.assertEqual(result["state"], "completed")
        self.assertIsNone(result["halt"])
        self.assertTrue(result["commitment_persisted"])
        self.assertEqual((result["model_adapter_calls"], result["scoring_adapter_calls"]), (22, 120))
        self.assertEqual((len(fake.model_calls), len(fake.score_calls), len(result["ledger"])), (22, 120, 208))
        self.assertEqual([row["index"] for row in fake.model_calls], list(range(22)))
        self.assertEqual([row["index"] for row in fake.score_calls], list(range(120)))
        self.assertEqual(Counter(row["status"] for row in result["requests"]), {"design_eligible": 22})
        self.assertTrue(all(row["adapter_dispatched"] for row in result["requests"]))
        self.assertEqual(Counter(row["status"] for row in result["ledger"]), {"completed_valid": 120, "not_run": 88})
        completed = [row for row in result["ledger"] if row["status"] == "completed_valid"]
        self.assertTrue(all(row["adapter_dispatched"] for row in completed))
        self.assertTrue(all(type(row["warning_events"]) is int and row["warning_events"] == 0 for row in completed))
        self.assertTrue(all(row["warning_trace_sha256"] == EMPTY_WARNING_TRACE_SHA256 for row in completed))
        self.assertTrue(all(row["reason"] == "not_selected_predeclared" for row in result["ledger"] if row["status"] == "not_run"))

    def test_slot_order_fixed_sampling_seeds_and_12_opportunities_per_arm(self):
        fake = Adapters()
        result = fake.run()
        self.assertEqual([row["slot"] for row in fake.model_calls], fake.plan["slots"])
        for row, slot in zip(result["requests"], fake.plan["slots"]):
            self.assertEqual(row["generation_evidence"]["slot_seed"], slot["seed"])
            self.assertEqual(result["sources"][slot["slot_id"]]["source_order"], 2 + fake.plan["slots"].index(slot))
        for arm in ("evolution", "control"):
            self.assertEqual(sum(row["slot"]["arm"] in (arm, "shared") for row in fake.model_calls), 12)
        self.assertEqual(sum(row["slot"]["arm"] == "shared" for row in fake.model_calls), 2)

    def test_fixed_seed_bytes_are_shared_between_seed_and_comparator_roles(self):
        fake = Adapters()
        result = fake.run()
        for source_id, order, graph in (("ff", 0, FF), ("bf", 1, BF)):
            seed = result["sources"][source_id]
            self.assertEqual(seed["origin"], "handwritten_seed")
            self.assertEqual(seed["source_order"], order)
            self.assertEqual(seed["graph_identity"], policy.graph_identity(encode(graph)))
            raw = (ROOT / "seeds" / (source_id + ".json")).read_bytes()
            self.assertEqual(seed["raw_sha256"], hashlib.sha256(raw).hexdigest())
            design_calls = [row for row in fake.score_calls if row["source_id"] == source_id and row["case_id"] in fake.study.design_ids]
            self.assertEqual(len(design_calls), 4)
            self.assertEqual([row["phase"] for row in design_calls], ["seed_design"] * 4)

    def test_representation_duplicates_are_all_scored_without_cache_reuse(self):
        fake = Adapters()
        result = fake.run()
        graph_ids = {result["sources"][slot["slot_id"]]["graph_identity"] for slot in fake.plan["slots"]}
        self.assertEqual(len(graph_ids), 1)
        for slot in fake.plan["slots"]:
            calls = [row for row in fake.score_calls if row["source_id"] == slot["slot_id"]]
            self.assertEqual([row["case_id"] for row in calls], fake.study.design_ids)
        self.assertEqual(result["selected"]["evolution"]["source_id"], "bf")
        self.assertEqual(result["selected"]["control"]["source_id"], "bf")
        winner_rows = [row for row in result["ledger"] if row["role"] == "winner"]
        self.assertEqual(Counter(row["arm"] for row in winner_rows), {"evolution": 4, "control": 4})
        self.assertTrue(all(row["source_id"] == "bf" and row["status"] == "completed_valid" for row in winner_rows))

    def test_run_preserves_frozen_plan_and_design_input_objects(self):
        fake = Adapters()
        before = (copy.deepcopy(fake.plan), copy.deepcopy(fake.design))
        fake.run()
        self.assertEqual((fake.plan, fake.design), before)


class GenerationSequencingTests(PipelineTestCase):
    def test_all_generation_operators_use_start_snapshot_despite_early_improvement(self):
        fake = Adapters()
        fake.generation_outcomes["g1_E1_evolution"] = encode(LONG_BF)
        result = fake.run()
        self.assertEqual(result["state"], "completed")
        expected_g1 = {"E1": ["bf", "ff"], "E2": ["bf", "ff"], "M1": ["bf"], "M2": ["ff"], "M3": ["bf"]}
        expected_g2 = {"E1": ["g1_E1_evolution", "bf"], "E2": ["g1_E1_evolution", "bf"], "M1": ["g1_E1_evolution"], "M2": ["bf"], "M3": ["g1_E1_evolution"]}
        for generation, expected in ((1, expected_g1), (2, expected_g2)):
            actual = {row["operator"]: row["parent_source_ids"] for row in result["requests"] if row["generation"] == generation and row["arm"] == "evolution"}
            self.assertEqual(actual, expected)
        snapshots = [payload for event, payload in fake.events if event == "generation_snapshot"]
        self.assertEqual(snapshots, [{"generation": 1, "parents": ["bf", "ff"]}, {"generation": 2, "parents": ["g1_E1_evolution", "bf"]}])
        self.assertEqual(result["history"][1]["evolution"], ["g1_E1_evolution", "bf"])
        self.assertEqual(result["selected"]["evolution"]["source_id"], "g1_E1_evolution")

    def test_control_and_shared_i1_prompts_never_receive_parent_or_fitness_feedback(self):
        fake = Adapters()
        fake.generation_outcomes["g1_E1_control"] = encode(LONG_BF)
        result = fake.run()
        independent = [row for row in fake.model_calls if row["slot"]["operator"] == "I1"]
        self.assertEqual(len(independent), 12)
        self.assertEqual(len({row["prompt"] for row in independent}), 1)
        for row in independent:
            self.assertNotIn("Parent 0", row["prompt"])
            self.assertNotIn("excess_numerator", row["prompt"])
            self.assertNotIn(LONG_BF["description"], row["prompt"])
        self.assertTrue(all(row["parent_source_ids"] == [] for row in result["requests"] if row["operator"] == "I1"))
        self.assertEqual(result["selected"]["control"]["source_id"], "g1_E1_control")
        self.assertEqual(result["selected"]["evolution"]["source_id"], "bf")

    def test_nonadherent_m2_output_is_retained_and_not_repaired_or_replaced(self):
        fake = Adapters()
        raw = encode(LONG_BF)
        fake.generation_outcomes["g1_M2_evolution"] = raw
        result = fake.run()
        source = result["sources"]["g1_M2_evolution"]
        self.assertFalse(source["operator_changes"][0]["parameter_only_observed"])
        self.assertEqual(source["program_json"].encode(), raw)
        self.assertEqual(result["selected"]["evolution"]["source_id"], "g1_M2_evolution")
        self.assertEqual(sum(row["slot"]["slot_id"] == "g1_M2_evolution" for row in fake.model_calls), 1)


class CommitmentAndValidationTests(PipelineTestCase):
    def test_commitment_sink_completes_before_validation_load_or_any_reference_scoring(self):
        fake = Adapters()
        result = fake.run()
        commit_index = fake.trace.index(("emit", "winner_commitment"))
        load_index = fake.trace.index(("load_validation",))
        self.assertLess(commit_index, load_index)
        for index, event in enumerate(fake.trace):
            if event[0] == "score" and (event[2] in VALIDATION_IDS or event[1] == "published_formula"):
                self.assertGreater(index, load_index)
        self.assertEqual(fake.validation_loads, 1)
        self.assertTrue(fake.commitment_saved)
        self.assertTrue(result["commitment_persisted"])
        self.assertTrue(fake.validation_load_state["commitment_persisted"])
        self.assertEqual(fake.saved_commitment, {"selected": result["selected"], "sha256": result["selected_hash"]})
        self.assertEqual(sum(row["phase"] in ("seed_design", "shared_initialization", "generation_1", "generation_2") for row in fake.score_calls), 96)

    def test_adverse_validation_results_cannot_replace_committed_seed_winner(self):
        fake = Adapters()
        fake.validation_used_override[policy.graph_identity(encode(BF))] = (128, 128, 128, 128)
        result = fake.run()
        self.assertEqual(result["state"], "completed")
        self.assertEqual(result["selected"], fake.saved_commitment["selected"])
        self.assertEqual(result["selected"]["evolution"]["source_id"], "bf")
        self.assertEqual(result["selected"]["evolution"]["fitness"]["per_case_used"], [51, 11, 62, 13])
        winner_rows = [row for row in result["ledger"] if row["role"] == "winner"]
        self.assertTrue(all(row["used_bins"] == 128 for row in winner_rows))

    def test_generated_winner_links_predeclared_candidate_rows_without_extra_dispatch(self):
        fake = Adapters()
        fake.generation_outcomes["init_0"] = encode(LONG_BF)
        result = fake.run()
        self.assertEqual(result["scoring_adapter_calls"], 120)
        self.assertTrue(all(winner["source_id"] == "init_0" for winner in result["selected"].values()))
        linked = self.candidate_rows(result, "init_0", "validation")
        self.assertEqual(len(linked), 4)
        self.assertTrue(all(row["status"] == "linked_winner_role" for row in linked))
        for row in linked:
            self.assertEqual(row["winner_links"], [
                {"arm": "evolution", "winner_case_status": "completed_valid", "reason": None},
                {"arm": "control", "winner_case_status": "completed_valid", "reason": None},
            ])
        physical_winner_rows = [row for row in result["ledger"] if row["role"] == "winner" and row["source_id"] == "init_0"]
        self.assertEqual(len(physical_winner_rows), 8)
        self.assertEqual(Counter(row["arm"] for row in physical_winner_rows), {"evolution": 4, "control": 4})

    def test_shared_winner_links_exist_after_commitment_before_validation_load(self):
        fake = Adapters()
        fake.generation_outcomes["init_0"] = encode(LONG_BF)
        result = fake.run()
        self.assertEqual(result["state"], "completed")
        at_load = fake.validation_load_state
        self.assertTrue(at_load["commitment_persisted"])
        linked = self.candidate_rows(at_load, "init_0", "validation")
        self.assertEqual(len(linked), 4)
        for row in linked:
            self.assertEqual(row["status"], "linked_winner_role")
            self.assertEqual(row["winner_links"], [
                {"arm": "evolution", "winner_case_status": "not_run", "reason": "awaiting_validation"},
                {"arm": "control", "winner_case_status": "not_run", "reason": "awaiting_validation"},
            ])
        winners = [row for row in at_load["ledger"] if row["role"] == "winner"]
        self.assertEqual(len(winners), 8)
        self.assertTrue(all(row["source_id"] == "init_0" and row["status"] == "not_run" for row in winners))
        self.assertTrue(all(row["reason"] == "committed_winner_awaiting_validation" for row in winners))

    def test_mid_validation_failure_preserves_per_case_status_and_both_shared_winner_links(self):
        for failure_index in (97, 101):
            fake = Adapters()
            fake.generation_outcomes["init_0"] = encode(LONG_BF)
            fake.score_exceptions[failure_index] = ReserveUnavailable("validation score reserve denied")
            with self.subTest(failure_index=failure_index):
                result = fake.run()
                self.assertEqual(result["state"], "incomplete")
                self.assertEqual(result["halt"]["phase"], "validation")
                self.assertTrue(result["commitment_persisted"])
                self.assertEqual(result["selected"], fake.saved_commitment["selected"])
                self.assertEqual((result["model_adapter_calls"], result["scoring_adapter_calls"]), (22, failure_index + 1))
                linked = self.candidate_rows(result, "init_0", "validation")
                self.assertEqual(len(linked), 4)
                for case_index, row in enumerate(linked):
                    self.assertEqual(row["status"], "linked_winner_role")
                    self.assertEqual([link["arm"] for link in row["winner_links"]], ["evolution", "control"])
                    for arm_index, link in enumerate(row["winner_links"]):
                        dispatch_index = 96 + 4 * arm_index + case_index
                        expected = "completed_valid" if dispatch_index < failure_index else "infrastructure_or_budget_stop" if dispatch_index == failure_index else "not_run"
                        self.assertEqual(link["winner_case_status"], expected)
                        physical = next(winner for winner in result["ledger"] if winner["role"] == "winner" and winner["arm"] == link["arm"] and winner["case_id"] == row["case_id"])
                        self.assertEqual(physical["source_id"], "init_0")
                        self.assertEqual(physical["status"], expected)
                        if expected == "not_run":
                            self.assertEqual(link["reason"], "study_stopped")
                            self.assertFalse(physical.get("adapter_dispatched", False))
                        elif expected == "completed_valid":
                            self.assertIsNone(link["reason"])
                            self.assertTrue(physical["adapter_dispatched"])
                        else:
                            self.assertIn("validation score reserve denied", link["reason"])
                            self.assertTrue(physical["adapter_dispatched"])

    def test_validation_load_failure_preserves_committed_selected_not_run_links(self):
        fake = Adapters()
        fake.generation_outcomes["init_0"] = encode(LONG_BF)
        fake.validation_exception = OSError("handwritten validation load failure")
        result = fake.run()
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(result["halt"]["phase"], "validation")
        self.assertTrue(result["commitment_persisted"])
        self.assertEqual((fake.validation_loads, len(fake.score_calls)), (1, 96))
        for row in self.candidate_rows(result, "init_0", "validation"):
            self.assertEqual(row["status"], "linked_winner_role")
            self.assertEqual(row["winner_links"], [
                {"arm": "evolution", "winner_case_status": "not_run", "reason": "study_stopped"},
                {"arm": "control", "winner_case_status": "not_run", "reason": "study_stopped"},
            ])
        winners = [row for row in result["ledger"] if row["role"] == "winner"]
        self.assertTrue(all(row["source_id"] == "init_0" and row["status"] == "not_run" for row in winners))

    def test_invalid_validation_case_is_reported_without_winner_reselection(self):
        fake = Adapters()
        fake.score_statuses[("bf", VALIDATION_IDS[0])] = "numeric_invalid"
        result = fake.run()
        self.assertEqual(result["state"], "completed")
        rows = [row for row in result["ledger"] if row["role"] == "winner" and row["case_id"] == VALIDATION_IDS[0]]
        self.assertEqual([row["status"] for row in rows], ["numeric_invalid", "numeric_invalid"])
        self.assertTrue(all(winner["source_id"] == "bf" for winner in result["selected"].values()))
        self.assertEqual(result["scoring_adapter_calls"], 120)

    def test_validation_id_order_mismatch_halts_before_any_validation_score(self):
        fake = Adapters()
        fake.validation.reverse()
        result = fake.run()
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(result["halt"]["phase"], "validation")
        self.assertIn("validation ID/order", result["halt"]["message"])
        self.assertEqual((fake.validation_loads, len(fake.score_calls)), (1, 96))
        self.assertFalse(any(row["case_id"] in VALIDATION_IDS for row in fake.score_calls))
        self.assertTrue(fake.commitment_saved)
        self.assertTrue(result["commitment_persisted"])


class FailureAndDenominatorTests(PipelineTestCase):
    def test_rejected_dag_consumes_its_request_but_keeps_four_unscored_design_rows(self):
        fake = Adapters()
        fake.generation_outcomes["init_0"] = b"not a JSON graph"
        result = fake.run()
        self.assertEqual(result["state"], "completed")
        self.assertEqual((result["model_adapter_calls"], result["scoring_adapter_calls"], len(result["ledger"])), (22, 116, 208))
        self.assertEqual(self.request(result, "init_0")["status"], "dag_rejected")
        self.assertNotIn("init_0", result["sources"])
        rows = self.candidate_rows(result, "init_0")
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(row["status"] == "not_run" and row["reason"] == "dag_rejected" for row in rows))

    def test_declared_ordinary_generation_failures_keep_denominators_without_retry(self):
        fake = Adapters()
        ordinary = {"init_0": "post_send_timeout", "init_1": "model_limit_stop", "g1_E1_evolution": "model_format_failure"}
        fake.generation_outcomes.update(ordinary)
        result = fake.run()
        self.assertEqual(result["state"], "completed")
        self.assertEqual((result["model_adapter_calls"], result["scoring_adapter_calls"], len(result["ledger"])), (22, 108, 208))
        for source_id, reason in ordinary.items():
            request = self.request(result, source_id)
            self.assertEqual((request["status"], request["reason"]), ("generation_failed", reason))
            self.assertTrue(request["adapter_dispatched"])
            self.assertEqual(sum(row["slot"]["slot_id"] == source_id for row in fake.model_calls), 1)
            self.assertTrue(all(row["status"] == "not_run" and row["reason"] == "generation_failed" for row in self.candidate_rows(result, source_id)))

    def test_returned_infrastructure_or_unknown_generation_status_stops_entire_study(self):
        for status in ("infrastructure_stop", "unknown_cleanup", "context_rejected", "token_limit", "not_run", "future_status", None):
            fake = Adapters()
            fake.generation_outcomes["init_0"] = status
            with self.subTest(status=status):
                result = fake.run()
                self.assertEqual(result["state"], "incomplete")
                self.assertEqual(result["halt"]["phase"], "shared_initialization")
                self.assertEqual(result["halt"]["type"], "ValueError")
                self.assertIn("generation infrastructure/unknown status", result["halt"]["message"])
                current = self.request(result, "init_0")
                self.assertEqual(current["status"], "infrastructure_or_budget_stop")
                self.assertTrue(current["adapter_dispatched"])
                self.assertEqual((result["model_adapter_calls"], result["scoring_adapter_calls"]), (1, 8))
                self.assertEqual((len(result["requests"]), len(result["ledger"])), (22, 208))
                self.assertTrue(all(row["status"] == "not_run" and row["reason"] == "study_stopped" for row in result["requests"][1:]))
                self.assertFalse(result["commitment_persisted"])
                self.assertNoValidation(fake)

    def test_numeric_invalid_design_retains_all_four_results_and_removes_fitness(self):
        fake = Adapters()
        fake.score_statuses[("init_0", fake.study.design_ids[0])] = "numeric_invalid"
        result = fake.run()
        self.assertEqual(result["state"], "completed")
        source = result["sources"]["init_0"]
        self.assertIsNone(source["fitness"])
        self.assertIsNone(source["behavior_signature"])
        self.assertEqual(len(source["design_results"]), 4)
        self.assertEqual(self.request(result, "init_0")["status"], "design_unresolved_or_invalid")
        self.assertEqual(result["scoring_adapter_calls"], 120)

    def test_duplicate_conflicting_design_fitness_halts_on_first_observation(self):
        fake = Adapters()
        fake.source_used_override["g1_E1_evolution"] = (50, 10, 60, 12)
        result = fake.run()
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(result["halt"]["phase"], "generation_1")
        self.assertIn("conflicting deterministic graph/case observation", result["halt"]["message"])
        self.assertEqual((result["model_adapter_calls"], result["scoring_adapter_calls"]), (3, 17))
        self.assertTrue(all(row["status"] == "not_run" for row in result["requests"] if row["generation"] == 2))
        self.assertNoValidation(fake)

    def test_duplicate_conflicting_observed_assignment_halts_even_with_identical_fitness(self):
        fake = Adapters()
        fake.assignment_override[("init_0", fake.study.design_ids[0])] = [1] * 128
        result = fake.run()
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(result["halt"]["phase"], "shared_initialization")
        self.assertIn("conflicting deterministic graph/case observation", result["halt"]["message"])
        self.assertEqual((result["model_adapter_calls"], result["scoring_adapter_calls"]), (1, 9))
        self.assertNoValidation(fake)

    def test_cross_role_conflicting_residual_work_or_warning_observation_halts(self):
        # Index 96 is evolution-winner validation case zero; index 100 is the
        # control-winner repetition of the same graph and case. These deliberate
        # adapter corruptions must not be hidden by identical fitness/assignment.
        for field, value in (("residuals", [1]), ("work_units", 999), ("warning_events", 1)):
            fake = Adapters()
            fake.checked_overrides[100] = {field: value}
            with self.subTest(field=field):
                result = fake.run()
                self.assertEqual(result["state"], "incomplete")
                self.assertEqual(result["halt"]["phase"], "validation")
                self.assertIn("conflicting deterministic graph/case observation", result["halt"]["message"])
                self.assertEqual((len(fake.model_calls), len(fake.score_calls)), (22, 101))
                self.assertTrue(fake.commitment_saved)
                self.assertEqual(result["selected"], fake.saved_commitment["selected"])
                failed = next(row for row in result["ledger"] if row["role"] == "winner" and row["arm"] == "control" and row["case_id"] == VALIDATION_IDS[0])
                self.assertEqual(failed["status"], "infrastructure_or_budget_stop")

    def test_equal_warning_counts_with_different_trace_digests_are_conflicting(self):
        fake = Adapters()
        first_digest = hashlib.sha256(b"handwritten warning trace A").hexdigest()
        second_digest = hashlib.sha256(b"handwritten warning trace B").hexdigest()
        fake.checked_overrides[96] = {"warning_events": 1, "warning_trace_sha256": first_digest}
        fake.checked_overrides[100] = {"warning_events": 1, "warning_trace_sha256": second_digest}
        result = fake.run()
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(result["halt"]["phase"], "validation")
        self.assertIn("conflicting deterministic graph/case observation", result["halt"]["message"])
        self.assertEqual((len(fake.model_calls), len(fake.score_calls)), (22, 101))
        observations = [row for row in result["ledger"] if row["role"] == "winner" and row["case_id"] == VALIDATION_IDS[0]]
        self.assertEqual([row["warning_events"] for row in observations], [1, 1])
        self.assertEqual([row["warning_trace_sha256"] for row in observations], [first_digest, second_digest])
        self.assertEqual([row["status"] for row in observations], ["completed_valid", "infrastructure_or_budget_stop"])
        self.assertTrue(result["commitment_persisted"])

    def test_partial_pair_stop_preserves_first_arm_and_marks_remaining_slots_not_run(self):
        fake = Adapters()
        fake.generation_outcomes["g1_E1_control"] = OSError("handwritten transport infrastructure failure")
        result = fake.run()
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(self.request(result, "g1_E1_evolution")["status"], "design_eligible")
        self.assertEqual(self.request(result, "g1_E1_control")["status"], "infrastructure_or_budget_stop")
        self.assertEqual((result["model_adapter_calls"], result["scoring_adapter_calls"]), (4, 20))
        self.assertTrue(all(row["status"] == "completed_valid" for row in self.candidate_rows(result, "g1_E1_evolution")))
        self.assertTrue(all(row["status"] == "not_run" and row["reason"] == "study_stopped" for row in result["requests"][4:]))
        self.assertEqual(len(result["ledger"]), 208)
        self.assertNoValidation(fake)

    def test_fixed_seed_failure_stops_before_model_calls(self):
        fake = Adapters()
        fake.score_statuses[("ff", fake.study.design_ids[0])] = "numeric_invalid"
        result = fake.run()
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(result["halt"]["phase"], "seed_design")
        self.assertIn("fixed seed did not complete", result["halt"]["message"])
        self.assertEqual((len(fake.model_calls), len(fake.score_calls)), (0, 4))
        self.assertNoValidation(fake)

    def test_scoring_adapter_wrong_case_binding_is_infrastructure_stop(self):
        fake = Adapters()
        fake.case_id_override[0] = "wrong_case"
        result = fake.run()
        self.assertEqual(result["state"], "incomplete")
        self.assertIn("scoring adapter case mismatch", result["halt"]["message"])
        first_row = next(row for row in result["ledger"] if row["role"] == "comparator" and row["source_id"] == "ff" and row["case_id"] == fake.study.design_ids[0])
        self.assertEqual(first_row["status"], "infrastructure_or_budget_stop")
        self.assertEqual((len(fake.model_calls), len(fake.score_calls)), (0, 1))
        self.assertNoValidation(fake)


class ReserveAndPersistenceTests(PipelineTestCase):
    def test_model_reserve_exception_halts_entire_study_instead_of_ordinary_failure_continuation(self):
        fake = Adapters()
        fake.generation_outcomes["init_0"] = ReserveUnavailable("model reserve denied")
        result = fake.run()
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(result["halt"], {"phase": "shared_initialization", "type": "ReserveUnavailable", "message": "model reserve denied"})
        self.assertEqual(self.request(result, "init_0")["status"], "infrastructure_or_budget_stop")
        self.assertEqual((len(fake.model_calls), len(fake.score_calls)), (1, 8))
        self.assertTrue(all(row["status"] == "not_run" for row in result["requests"][1:]))
        self.assertNoValidation(fake)

    def test_score_reserve_exception_propagates_into_source_and_global_stop_without_retry(self):
        fake = Adapters()
        fake.score_exceptions[8] = ReserveUnavailable("score reserve denied")
        result = fake.run()
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(result["halt"]["type"], "ReserveUnavailable")
        self.assertEqual(result["halt"]["message"], "score reserve denied")
        self.assertEqual((len(fake.model_calls), len(fake.score_calls)), (1, 9))
        self.assertEqual(self.request(result, "init_0")["status"], "infrastructure_or_budget_stop")
        rows = self.candidate_rows(result, "init_0")
        self.assertEqual(rows[0]["status"], "infrastructure_or_budget_stop")
        self.assertTrue(all(row["status"] == "not_run" and row["reason"] == "study_stopped" for row in rows[1:]))
        self.assertNoValidation(fake)

    def test_commitment_computation_failure_prevents_sink_and_validation(self):
        fake = Adapters()
        with mock.patch.object(pipeline, "commitment", side_effect=ValueError("handwritten commitment failure")):
            result = fake.run()
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(result["halt"]["phase"], "winner_commitment")
        self.assertIsNone(result["selected"])
        self.assertFalse(fake.commitment_saved)
        self.assertFalse(result["commitment_persisted"])
        self.assertFalse(any(event == "winner_commitment" for event, _ in fake.events))
        self.assertEqual((len(fake.model_calls), len(fake.score_calls)), (22, 96))
        self.assertNoValidation(fake)

    def test_commitment_persistence_failure_never_opens_validation(self):
        fake = Adapters()
        fake.fail_event = "winner_commitment"
        result = fake.run()
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(result["halt"]["phase"], "winner_commitment")
        self.assertEqual(result["halt"]["type"], "OSError")
        self.assertIsNotNone(result["selected"], "Computed selection is not proof of durable commitment")
        self.assertFalse(fake.commitment_saved)
        self.assertFalse(result["commitment_persisted"])
        self.assertIsNone(fake.saved_commitment)
        self.assertEqual((len(fake.model_calls), len(fake.score_calls)), (22, 96))
        self.assertNoValidation(fake)

    def test_failed_commitment_sink_does_not_create_selected_candidate_links(self):
        fake = Adapters()
        fake.generation_outcomes["init_0"] = encode(LONG_BF)
        fake.fail_event = "winner_commitment"
        result = fake.run()
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(result["selected"]["evolution"]["source_id"], "init_0")
        self.assertFalse(result["commitment_persisted"])
        for row in self.candidate_rows(result, "init_0", "validation"):
            self.assertEqual(row["status"], "not_run")
            self.assertEqual(row["reason"], "not_selected_predeclared")
            self.assertNotIn("winner_links", row)
        self.assertTrue(all(row["source_id"] is None for row in result["ledger"] if row["role"] == "winner"))
        self.assertNoValidation(fake)

    def test_start_event_persistence_failure_prevents_adapter_call(self):
        for event, expected_models, expected_scores in (("score_start", 0, 0), ("model_start", 0, 8)):
            fake = Adapters()
            fake.fail_event = event
            with self.subTest(event=event):
                result = fake.run()
                self.assertEqual(result["state"], "incomplete")
                self.assertEqual(result["halt"]["type"], "OSError")
                self.assertEqual((len(fake.model_calls), len(fake.score_calls)), (expected_models, expected_scores))
                self.assertEqual((result["model_adapter_calls"], result["scoring_adapter_calls"]), (expected_models, expected_scores))
                if event == "score_start":
                    current = next(row for row in result["ledger"] if row["role"] == "comparator" and row["source_id"] == "ff" and row["case_id"] == fake.study.design_ids[0])
                else:
                    current = self.request(result, "init_0")
                self.assertEqual(current["status"], "infrastructure_or_budget_stop")
                self.assertFalse(current["adapter_dispatched"])
                self.assertIn("handwritten persistence failure: " + event, current["reason"])
                terminal = event.replace("_start", "_terminal")
                terminals = [payload for name, payload in fake.events if name == terminal]
                self.assertEqual(len(terminals), 1)
                self.assertEqual(terminals[0]["status"], "infrastructure_or_budget_stop")
                self.assertFalse(terminals[0]["adapter_dispatched"])
                self.assertFalse(result["commitment_persisted"])
                self.assertNoValidation(fake)

    def test_terminal_event_persistence_failure_stops_before_next_dispatch(self):
        for event, expected_models, expected_scores in (("score_terminal", 0, 1), ("model_terminal", 1, 12)):
            fake = Adapters()
            fake.fail_event = event
            with self.subTest(event=event):
                result = fake.run()
                self.assertEqual(result["state"], "incomplete")
                self.assertEqual(result["halt"]["type"], "OSError")
                self.assertEqual((len(fake.model_calls), len(fake.score_calls)), (expected_models, expected_scores))
                if event == "score_terminal":
                    current = next(row for row in result["ledger"] if row["role"] == "comparator" and row["source_id"] == "ff" and row["case_id"] == fake.study.design_ids[0])
                else:
                    current = self.request(result, "init_0")
                self.assertTrue(current["adapter_dispatched"])
                self.assertIn("handwritten persistence failure: " + event, current["terminal_persistence_error"])
                self.assertNoValidation(fake)


if __name__ == "__main__":
    unittest.main()
