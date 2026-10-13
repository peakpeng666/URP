"""Handwritten, data-only tests for the prospective selection policy.

All case results below are invented trusted-result fixtures, not measurements.
The fixed FF/BF graphs and their handwritten structural variants are validated
as JSON data only. These tests never import the numerical interpreter or NumPy,
call a scoring worker/model/server, or open the validation panel. Run this file
alone, only in the separately approved stdlib-test window.

Mock generation plans demonstrate composition of the real policy helpers. They
do not claim to test a production supervisor, which this policy API does not
provide. In particular, durable commitment-before-validation, resource budgets,
request/score dispatch accounting, and actual within-generation snapshot use
need operational integration tests when that supervisor exists.
"""

import copy
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("evolution_policy_under_test", ROOT / "src" / "policy.py")
policy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy)

DESIGN_IDS = [
    "design_historical_design_5k_0_p128_c100",
    "design_historical_design_5k_0_p128_c500",
    "design_historical_design_5k_1_p128_c100",
    "design_historical_design_5k_1_p128_c500",
]

# These are fixed handwritten data, not generated candidates or runtime code.
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
    "description": "Handwritten best-fit representation with a redundant zero addition.",
    "constants": [{"type": "f64", "value": -1}, {"type": "f64", "value": 0}],
    "nodes": [["mul", "bins", "c0"], ["add", 0, "c1"]],
    "return_node": 1,
}


def encode(program):
    return json.dumps(program, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def fake_cases(used=(51, 11, 62, 13), bounds=(50, 10, 60, 12), assignment_offset=0):
    """Invented trusted evidence; no claim of feasible packing is made here."""
    return [
        {
            "case_id": case_id,
            "status": "completed_valid",
            "used_bins": bins,
            "L1": bound,
            "assignment": [(item + assignment_offset) % bins for item in range(128)],
        }
        for case_id, bins, bound in zip(DESIGN_IDS, used, bounds)
    ]


def record(source_id, source_order, graph, *, used=(51, 11, 62, 13), origin="generated"):
    raw = encode(graph)
    cases = fake_cases(used=used)
    return {
        "source_id": source_id,
        "source_order": source_order,
        "origin": origin,
        "program_json": raw.decode("utf-8"),
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "graph_identity": policy.graph_identity(raw),
        "fitness": policy.fitness(cases, DESIGN_IDS),
        "behavior_signature": policy.behavior_signature(cases),
    }


def seeds():
    # Deliberately different invented fitness: source order must not override it.
    return [
        record("FF", 0, FF, used=(53, 12, 64, 14), origin="seed"),
        record("BF", 1, BF, used=(51, 11, 62, 13), origin="seed"),
    ]


def mock_plan_generation(plan, generation, start_population):
    """Plan all prompts before invented outputs arrive; no model dispatch."""
    snapshot = copy.deepcopy(start_population)
    return [
        {
            "slot_id": slot["slot_id"],
            "operator": slot["operator"],
            "parent_ids": [parent["source_id"] for parent in policy.parents(snapshot, slot["operator"])],
            "prompt": policy.build_prompt(slot["operator"], policy.parents(snapshot, slot["operator"])),
        }
        for slot in plan["slots"]
        if slot["generation"] == generation
    ]


class FrozenPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = json.loads((ROOT / "protocol.json").read_bytes())
        cls.design = json.loads((ROOT / "data" / "design.json").read_bytes())

    def test_design_ids_and_order_are_frozen(self):
        self.assertEqual([case["id"] for case in self.design["cases"]], DESIGN_IDS)
        self.assertEqual([case["capacity"] for case in self.design["cases"]], [100, 500, 100, 500])
        self.assertTrue(all(case["split"] == "design" and case["n"] == 128 for case in self.design["cases"]))

    def test_22_physical_slots_12_per_arm_with_two_shared(self):
        slots = self.plan["slots"]
        self.assertEqual(len(slots), 22)
        self.assertEqual(len({slot["slot_id"] for slot in slots}), 22)
        shared = [slot for slot in slots if slot["arm"] == "shared"]
        self.assertEqual([slot["slot_id"] for slot in shared], ["init_0", "init_1"])
        self.assertEqual(self.plan["model_calls_max"], 22)
        self.assertEqual(self.plan["shared_initialization_calls"], 2)
        self.assertEqual(self.plan["arm_unique_calls"], 10)
        self.assertEqual(self.plan["per_arm_model_opportunities"], 12)
        for arm in ("evolution", "control"):
            self.assertEqual(sum(slot["arm"] in (arm, "shared") for slot in slots), 12)

    def test_frozen_slot_order_pair_seeds_and_operators(self):
        expected = ["init_0", "init_1"]
        for pair, (generation, operator) in enumerate(
            (generation, operator) for generation in (1, 2) for operator in ("E1", "E2", "M1", "M2", "M3")
        ):
            arms = ("evolution", "control") if pair % 2 == 0 else ("control", "evolution")
            expected.extend(f"g{generation}_{operator}_{arm}" for arm in arms)
            pair_slots = [slot for slot in self.plan["slots"] if slot.get("pair") == pair]
            self.assertEqual([slot["arm"] for slot in pair_slots], list(arms))
            self.assertEqual([slot["seed"] for slot in pair_slots], [2026100510 + pair] * 2)
            for slot in pair_slots:
                self.assertEqual(slot["operator"], operator if slot["arm"] == "evolution" else "I1")
        self.assertEqual([slot["slot_id"] for slot in self.plan["slots"]], expected)
        self.assertEqual([slot["seed"] for slot in self.plan["slots"][:2]], [2026100500, 2026100501])
        self.assertTrue(all(slot["operator"] == "I1" for slot in self.plan["slots"][:2]))

    def test_ledger_preserves_all_88_design_rows_in_slot_case_order(self):
        before = copy.deepcopy(self.plan)
        rows = policy.initialize_ledger(self.plan, self.design["cases"])
        self.assertEqual(len(rows), 88)
        self.assertEqual(
            [(row["slot_id"], row["case_id"]) for row in rows],
            [(slot["slot_id"], case_id) for slot in self.plan["slots"] for case_id in DESIGN_IDS],
        )
        self.assertTrue(all(row["status"] == "not_run" and row["reason"] == "awaiting_generation" for row in rows))
        self.assertEqual(self.plan, before)

    def test_ledger_predeclares_validation_without_reading_validation_panel(self):
        synthetic_validation = [{"id": f"handwritten_validation_{index}", "split": "validation"} for index in range(4)]
        rows = policy.initialize_ledger(self.plan, self.design["cases"] + synthetic_validation)
        self.assertEqual(len(rows), 176)
        validation_rows = [row for row in rows if row["split"] == "validation"]
        self.assertEqual(len(validation_rows), 88)
        self.assertTrue(all(row["status"] == "not_run" and row["reason"] == "not_selected_predeclared" for row in validation_rows))


class FitnessTests(unittest.TestCase):
    def test_exact_ratio_of_sums_not_average_of_case_ratios(self):
        cases = fake_cases()
        result = policy.fitness(cases, DESIGN_IDS)
        self.assertEqual(result, {
            "excess_numerator": 5,
            "excess_denominator": 132,
            "sum_used_bins": 137,
            "sum_L1": 132,
            "per_case_used": [51, 11, 62, 13],
            "per_case_L1": [50, 10, 60, 12],
        })
        ratio = Fraction(result["excess_numerator"], result["excess_denominator"])
        per_case_average = sum(Fraction(row["used_bins"] - row["L1"], row["L1"]) for row in cases) / 4
        self.assertEqual(ratio, Fraction(5, 132))
        self.assertNotEqual(ratio, per_case_average)
        self.assertTrue(all(type(result[key]) is int for key in ("excess_numerator", "excess_denominator", "sum_used_bins", "sum_L1")))

    def test_exact_design_id_order_binding_rejects_reordered_missing_extra_or_renamed_rows(self):
        cases = fake_cases()
        wrong_name = copy.deepcopy(cases)
        wrong_name[0]["case_id"] = "unbound_design_case"
        duplicate = copy.deepcopy(cases)
        duplicate[1]["case_id"] = duplicate[0]["case_id"]
        for invalid in (list(reversed(cases)), cases[:-1], cases + [cases[0]], wrong_name, duplicate):
            with self.subTest(ids=[row["case_id"] for row in invalid]):
                with self.assertRaisesRegex(ValueError, "exact design case order/binding"):
                    policy.fitness(invalid, DESIGN_IDS)

    def test_expected_design_ids_must_be_four_distinct_ids_in_a_list(self):
        for expected in (tuple(DESIGN_IDS), DESIGN_IDS[:-1], DESIGN_IDS + ["extra"], [DESIGN_IDS[0]] * 4):
            with self.subTest(expected=expected):
                with self.assertRaisesRegex(ValueError, "frozen design IDs"):
                    policy.fitness(fake_cases(), expected)

    def test_any_noncompleted_case_removes_eligibility(self):
        for index in range(4):
            for status in ("not_run", "timeout", "numeric_invalid", "infeasible", "diagnostic_limit", None):
                cases = fake_cases()
                cases[index]["status"] = status
                with self.subTest(index=index, status=status):
                    self.assertIsNone(policy.fitness(cases, DESIGN_IDS))

    def test_used_bins_and_bounds_require_bounded_exact_integers(self):
        mutations = (
            ("used_bins", True), ("used_bins", 51.0), ("used_bins", 129),
            ("used_bins", 49), ("used_bins", None), ("L1", False),
            ("L1", 50.0), ("L1", 0), ("L1", 52), ("L1", None),
        )
        for field, value in mutations:
            cases = fake_cases()
            cases[0][field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaisesRegex(ValueError, "fitness evidence"):
                    policy.fitness(cases, DESIGN_IDS)

    def test_fitness_does_not_mutate_trusted_evidence(self):
        cases = fake_cases()
        before = copy.deepcopy(cases)
        policy.fitness(cases, DESIGN_IDS)
        self.assertEqual(cases, before)

    def test_rank_key_uses_fraction_then_used_sum_then_source_order(self):
        candidate = record("init_0", 2, FF)
        self.assertEqual(policy.rank_key(candidate), (Fraction(5, 132), 137, 2))
        self.assertIs(type(policy.rank_key(candidate)[0]), Fraction)
        # Synthetic exact fractions distinguish ratio order from numerator order.
        lower = copy.deepcopy(candidate)
        lower["fitness"].update(excess_numerator=2, excess_denominator=100, sum_used_bins=102)
        higher = copy.deepcopy(candidate)
        higher["fitness"].update(excess_numerator=1, excess_denominator=10, sum_used_bins=11)
        self.assertLess(policy.rank_key(lower), policy.rank_key(higher))
        same_ratio = copy.deepcopy(lower)
        same_ratio["fitness"].update(excess_numerator=4, excess_denominator=200, sum_used_bins=204)
        self.assertLess(policy.rank_key(lower), policy.rank_key(same_ratio))


class RetentionTests(unittest.TestCase):
    def test_best_two_distinct_graphs_and_earliest_duplicate_source(self):
        ff, bf = seeds()
        duplicate = record("init_0", 2, BF, used=(51, 11, 62, 13))
        later = record("init_1", 3, LONG_BF, used=(52, 11, 62, 13))
        records = [later, duplicate, ff, bf]
        before = copy.deepcopy(records)
        retained = policy.retain(records)
        self.assertEqual([row["source_id"] for row in retained], ["BF", "init_1"])
        self.assertEqual(len({row["graph_identity"] for row in retained}), 2)
        self.assertEqual(records, before)
        self.assertEqual(len(records), 4, "Retention must not erase request-denominator records")

    def test_equal_fitness_uses_frozen_source_order_not_input_order(self):
        ff = record("FF", 0, FF, origin="seed")
        bf = record("BF", 1, BF, origin="seed")
        init = record("init_0", 2, LONG_BF)
        self.assertEqual([row["source_id"] for row in policy.retain([init, bf, ff])], ["FF", "BF"])

    def test_invalid_results_never_displace_eligible_records(self):
        ff, bf = seeds()
        invalid = record("init_0", 2, LONG_BF)
        invalid["fitness"] = None
        self.assertEqual([row["source_id"] for row in policy.retain([invalid, ff, bf])], ["BF", "FF"])
        self.assertEqual(policy.retain([invalid]), [])

    def test_duplicate_fitness_conflict_rejected_even_for_later_better_record(self):
        original = record("FF", 0, FF, origin="seed")
        for used in ((50, 10, 60, 12), (52, 12, 63, 14)):
            conflicting = record("init_0", 2, FF, used=used)
            # Isolate the fitness conflict from an assignment-signature conflict.
            conflicting["behavior_signature"] = original["behavior_signature"]
            with self.subTest(used=used):
                with self.assertRaisesRegex(ValueError, "duplicate deterministic result conflict"):
                    policy.retain([conflicting, original])

    def test_duplicate_observed_behavior_conflict_rejected(self):
        original = record("BF", 1, BF, origin="seed")
        conflicting = record("init_1", 3, BF)
        conflicting["behavior_signature"] = policy.behavior_signature(fake_cases(assignment_offset=1))
        self.assertNotEqual(original["behavior_signature"], conflicting["behavior_signature"])
        with self.assertRaisesRegex(ValueError, "duplicate deterministic result conflict"):
            policy.retain([original, conflicting])

    def test_same_observed_behavior_does_not_collapse_distinct_graphs(self):
        ff = record("FF", 0, FF, origin="seed")
        bf = record("BF", 1, BF, origin="seed")
        self.assertEqual(ff["behavior_signature"], bf["behavior_signature"])
        self.assertNotEqual(ff["graph_identity"], bf["graph_identity"])
        self.assertEqual(len(policy.retain([ff, bf])), 2)

    def test_seed_can_win_while_generated_only_best_remains_a_diagnostic(self):
        ff, bf = seeds()
        generated = record("init_0", 2, LONG_BF, used=(52, 12, 63, 14))
        all_records = [ff, bf, generated]
        population = policy.retain(all_records)
        diagnostic = policy.retain([row for row in all_records if row["origin"] == "generated"], n=1)
        self.assertEqual(population[0]["source_id"], "BF")
        self.assertEqual(diagnostic[0]["source_id"], "init_0")
        committed, _ = policy.commitment(population, population)
        self.assertEqual(committed["evolution"]["source_id"], "BF")
        self.assertEqual(committed["evolution"]["origin"], "seed")
        self.assertNotEqual(committed["evolution"]["source_id"], diagnostic[0]["source_id"])


class ParentAndSnapshotTests(unittest.TestCase):
    def test_i1_always_uses_no_parents(self):
        self.assertEqual(policy.parents([], "I1"), [])
        self.assertEqual(policy.parents(seeds(), "I1"), [])

    def test_e1_e2_take_both_best_first_m1_m3_best_and_m2_second(self):
        population = seeds()
        expected = {"E1": ["BF", "FF"], "E2": ["BF", "FF"], "M1": ["BF"], "M2": ["FF"], "M3": ["BF"]}
        for operator, parent_ids in expected.items():
            with self.subTest(operator=operator):
                self.assertEqual([row["source_id"] for row in policy.parents(population, operator)], parent_ids)

    def test_evolution_operators_reject_insufficient_or_duplicate_population(self):
        ff, bf = seeds()
        for population in ([], [ff], [ff, ff], [ff, bf, ff]):
            for operator in ("E1", "E2", "M1", "M2", "M3"):
                with self.subTest(operator=operator, size=len(population)):
                    with self.assertRaisesRegex(ValueError, "insufficient distinct eligible parents"):
                        policy.parents(population, operator)

    def test_unknown_operator_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown frozen operator"):
            policy.parents(seeds(), "M4")

    def test_mock_generation_holds_start_snapshot_until_all_pairs_complete(self):
        plan = json.loads((ROOT / "protocol.json").read_bytes())
        initial = policy.retain(seeds())
        generation_one = mock_plan_generation(plan, 1, initial)
        self.assertEqual(len(generation_one), 10)
        newcomer = record("g1_E1_evolution", 4, LONG_BF, used=(50, 10, 60, 12))
        updated = policy.retain(initial + [newcomer])
        self.assertEqual(updated[0]["source_id"], newcomer["source_id"])
        # A genuinely different best record has arrived, but every preplanned
        # generation-one parent still comes from the frozen start population.
        for row in generation_one:
            self.assertNotIn(newcomer["source_id"], row["parent_ids"])
            self.assertNotIn(LONG_BF["description"], row["prompt"])
        g1_evolution = {row["operator"]: row["parent_ids"] for row in generation_one if row["operator"] != "I1"}
        self.assertEqual(g1_evolution, {"E1": ["BF", "FF"], "E2": ["BF", "FF"], "M1": ["BF"], "M2": ["FF"], "M3": ["BF"]})
        generation_two = mock_plan_generation(plan, 2, updated)
        g2_evolution = {row["operator"]: row["parent_ids"] for row in generation_two if row["operator"] != "I1"}
        self.assertEqual(g2_evolution["M1"], [newcomer["source_id"]])
        self.assertEqual(g2_evolution["M2"], ["BF"])
        self.assertEqual(g2_evolution["E2"], [newcomer["source_id"], "BF"])
        self.assertTrue(all(row["parent_ids"] == [] for row in generation_one + generation_two if row["operator"] == "I1"))

    def test_control_prompt_is_independent_of_cumulative_best_population(self):
        initial = policy.retain(seeds())
        better = record("g1_E1_control", 5, LONG_BF, used=(50, 10, 60, 12))
        improved = policy.retain(initial + [better])
        self.assertNotEqual(initial[0]["source_id"], improved[0]["source_id"])
        self.assertEqual(
            policy.build_prompt("I1", policy.parents(initial, "I1")),
            policy.build_prompt("I1", policy.parents(improved, "I1")),
        )


class PromptTests(unittest.TestCase):
    def test_parent_arity_is_enforced_for_each_operator(self):
        for operator, arity in (("I1", 0), ("E1", 2), ("E2", 2), ("M1", 1), ("M2", 1), ("M3", 1)):
            for supplied in (0, 1, 2, 3):
                if supplied == arity:
                    continue
                with self.subTest(operator=operator, supplied=supplied):
                    with self.assertRaisesRegex(ValueError, "parent arity"):
                        policy.build_prompt(operator, [seeds()[0]] * supplied)
        with self.assertRaisesRegex(ValueError, "operator"):
            policy.build_prompt("unknown", [])

    def test_only_program_and_exact_design_statistics_are_supplied(self):
        parent = seeds()[1]
        parent.update(
            validation_results="DO_NOT_LEAK_VALIDATION_9173",
            validation_fitness="DO_NOT_LEAK_FITNESS_7251",
            diagnostic_message="DO_NOT_LEAK_DIAGNOSTIC_2981",
            repair_feedback="DO_NOT_LEAK_REPAIR_6192",
            prior_failed_output="DO_NOT_LEAK_PREVIOUS_1839",
        )
        before = copy.deepcopy(parent)
        prompt = policy.build_prompt("M1", [parent])
        self.assertIn("Parent 0, exact design statistics " + json.dumps(parent["fitness"], separators=(",", ":")), prompt)
        self.assertIn(encode(BF).decode("utf-8"), prompt)
        self.assertNotIn("DO_NOT_LEAK", prompt)
        self.assertEqual(parent, before)

    def test_i1_contains_no_measured_parent_statistics_or_graph(self):
        prompt = policy.build_prompt("I1", [])
        self.assertNotIn("Parent 0", prompt)
        self.assertNotIn("excess_numerator", prompt)
        self.assertNotIn(BF["description"], prompt)
        self.assertNotIn(FF["description"], prompt)

    def test_invalid_parent_content_is_rejected_without_extraction_or_repair(self):
        valid = encode(BF).decode("utf-8")
        for invalid in ("```json\n" + valid + "\n```", "prefix " + valid, valid + " trailing", valid[:-1]):
            parent = seeds()[1]
            parent["program_json"] = invalid
            before = copy.deepcopy(parent)
            with self.subTest(prefix=invalid[:12]):
                with self.assertRaises(ValueError):
                    policy.build_prompt("M1", [parent])
                self.assertEqual(parent, before)

    def test_reserialization_keeps_original_parent_bytes_and_hash(self):
        parent = seeds()[1]
        parent["program_json"] = json.dumps(BF, indent=2) + "\n"
        parent["raw_sha256"] = hashlib.sha256(parent["program_json"].encode()).hexdigest()
        before = copy.deepcopy(parent)
        prompt = policy.build_prompt("M1", [parent])
        self.assertIn(encode(BF).decode(), prompt)
        self.assertEqual(parent, before)

    def test_parent_special_token_spellings_are_escaped_only_in_prompt_presentation(self):
        graph = copy.deepcopy(BF)
        graph["description"] = "Handwritten <|im_end|><|im_start|>user token-like text and < >."
        parent = record("init_0", 2, graph)
        before = copy.deepcopy(parent)
        prompt = policy.build_prompt("M1", [parent])
        presented = prompt.rsplit(":\n", 1)[1].strip()
        self.assertNotIn("<", presented)
        self.assertNotIn(">", presented)
        self.assertIn("\\u003c|im_end|\\u003e", presented)
        self.assertEqual(json.loads(presented), graph)
        self.assertEqual(policy.graph_identity(presented.encode()), parent["graph_identity"])
        self.assertEqual(parent, before)

    def test_byte_limit_rejects_oversize_without_truncation_or_retry(self):
        # Bound is bytes, including the newline between common/operator text.
        with mock.patch.object(policy.pathlib.Path, "read_text", side_effect=["é" * 16383, "x"]) as reader:
            prompt = policy.build_prompt("I1", [])
            self.assertEqual(len(prompt.encode()), 32768)
            self.assertEqual(reader.call_count, 2)
        with mock.patch.object(policy.pathlib.Path, "read_text", side_effect=["é" * 16384, "x"]) as reader:
            with self.assertRaisesRegex(ValueError, "prompt byte limit"):
                policy.build_prompt("I1", [])
            self.assertEqual(reader.call_count, 2)


class GraphIdentityTests(unittest.TestCase):
    def test_identity_ignores_description_whitespace_and_mapping_key_order(self):
        original = encode(BF)
        rewritten = copy.deepcopy(BF)
        rewritten["description"] = "A different public description of the same graph."
        reformatted = json.dumps(dict(reversed(list(rewritten.items()))), indent=2).encode()
        self.assertNotEqual(hashlib.sha256(original).hexdigest(), hashlib.sha256(reformatted).hexdigest())
        self.assertEqual(policy.graph_identity(original), policy.graph_identity(reformatted))

    def test_f64_lexical_spellings_normalize_to_binary64(self):
        prefix = b'{"schema":"math-dag-v1","description":"Handwritten float spelling.","constants":[{"type":"f64","value":'
        suffix = b'}],"nodes":[["mul","bins","c0"]],"return_node":0}'
        identities = {policy.graph_identity(prefix + spelling + suffix) for spelling in (b"-1", b"-1.0", b"-1e0", b"-1.0000000000000000")}
        self.assertEqual(len(identities), 1)

    def test_identity_preserves_signed_zero(self):
        positive = copy.deepcopy(FF)
        negative = copy.deepcopy(FF)
        positive["constants"][0]["value"] = 0.0
        negative["constants"][0]["value"] = -0.0
        self.assertEqual(policy.graph_identity(encode(FF)), policy.graph_identity(encode(positive)))
        self.assertNotEqual(policy.graph_identity(encode(positive)), policy.graph_identity(encode(negative)))

    def test_identity_preserves_constant_type_node_order_reference_and_root(self):
        base = copy.deepcopy(LONG_BF)
        base["nodes"] = [["div", "bins", "item"], ["mul", "bins", "c0"], ["add", 1, "c1"]]
        base["return_node"] = 2
        variants = []
        tag = copy.deepcopy(base)
        tag["constants"][0]["type"] = "i32"
        variants.append(tag)
        order = copy.deepcopy(base)
        order["nodes"][0], order["nodes"][1] = order["nodes"][1], order["nodes"][0]
        variants.append(order)
        reference = copy.deepcopy(base)
        reference["nodes"][2][1] = 0
        variants.append(reference)
        root = copy.deepcopy(base)
        root["return_node"] = 0
        variants.append(root)
        for variant in variants:
            with self.subTest(graph=variant):
                self.assertNotEqual(policy.graph_identity(encode(base)), policy.graph_identity(encode(variant)))


class StructuralAdherenceTests(unittest.TestCase):
    def test_parameter_only_change_requires_same_nodes_root_and_constant_tags(self):
        result = policy.structural_changes(encode(FF), encode(BF))
        self.assertFalse(result["same_graph_identity"])
        self.assertFalse(result["nodes_changed"])
        self.assertFalse(result["return_node_changed"])
        self.assertTrue(result["constant_types_same"])
        self.assertTrue(result["constant_values_changed"])
        self.assertTrue(result["parameter_only_observed"])
        self.assertFalse(result["shorter_node_count_observed"])
        self.assertFalse(result["semantic_equivalence_proven"])

    def test_description_only_noop_does_not_count_as_parameter_change(self):
        child = copy.deepcopy(BF)
        child["description"] = "This description changed without changing graph data."
        result = policy.structural_changes(encode(BF), encode(child))
        self.assertTrue(result["same_graph_identity"])
        self.assertFalse(result["constant_values_changed"])
        self.assertFalse(result["parameter_only_observed"])

    def test_node_root_type_or_count_change_is_not_parameter_only(self):
        base = copy.deepcopy(LONG_BF)
        variants = []
        node = copy.deepcopy(base)
        node["nodes"][1][0] = "sub"
        variants.append(node)
        root = copy.deepcopy(base)
        root["return_node"] = 0
        variants.append(root)
        tag = copy.deepcopy(base)
        tag["constants"][1]["type"] = "i32"
        variants.append(tag)
        count = copy.deepcopy(base)
        count["constants"].append({"type": "f64", "value": 1})
        variants.append(count)
        for variant in variants:
            with self.subTest(graph=variant):
                self.assertFalse(policy.structural_changes(encode(base), encode(variant))["parameter_only_observed"])

    def test_shorter_node_count_is_descriptive_not_semantic_proof(self):
        result = policy.structural_changes(encode(LONG_BF), encode(BF))
        self.assertEqual((result["parent_nodes"], result["child_nodes"]), (2, 1))
        self.assertTrue(result["shorter_node_count_observed"])
        self.assertTrue(result["nodes_changed"])
        self.assertFalse(result["semantic_equivalence_proven"])
        self.assertFalse(policy.structural_changes(encode(BF), encode(BF))["shorter_node_count_observed"])

    def test_signed_zero_parameter_change_reports_changed_constant_value(self):
        child = copy.deepcopy(FF)
        child["constants"][0]["value"] = -0.0
        result = policy.structural_changes(encode(FF), encode(child))
        self.assertFalse(result["same_graph_identity"])
        self.assertTrue(result["parameter_only_observed"])
        # Regression: Python tuple equality alone loses the signed-zero change.
        self.assertTrue(result["constant_values_changed"])

    def test_nonadherent_valid_output_is_retained_without_replacement(self):
        ff, bf = seeds()
        child = record("g1_M2_evolution", 11, LONG_BF, used=(50, 10, 60, 12))
        flags = policy.structural_changes(encode(FF), encode(LONG_BF))
        self.assertFalse(flags["parameter_only_observed"])
        self.assertEqual(policy.retain([ff, bf, child])[0]["source_id"], "g1_M2_evolution")


class BehaviorSignatureTests(unittest.TestCase):
    def test_signature_is_exact_ordered_case_id_assignment_digest(self):
        cases = fake_cases()
        framed = [[case["case_id"], case["assignment"]] for case in cases]
        expected = hashlib.sha256(json.dumps(framed, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(policy.behavior_signature(cases), expected)

    def test_signature_ignores_graph_description_fitness_and_other_metadata(self):
        cases = fake_cases()
        annotated = copy.deepcopy(cases)
        for case in annotated:
            case.update(description="different", graph_identity="different", used_bins=128, L1=1, elapsed_seconds=999, diagnostic="different")
        self.assertEqual(policy.behavior_signature(cases), policy.behavior_signature(annotated))

    def test_assignment_case_binding_and_order_all_affect_signature(self):
        original = fake_cases()
        changed_assignment = copy.deepcopy(original)
        changed_assignment[0]["assignment"][0] = 1
        changed_id = copy.deepcopy(original)
        changed_id[0]["case_id"] += "_different"
        for variant in (changed_assignment, changed_id, list(reversed(original))):
            self.assertNotEqual(policy.behavior_signature(original), policy.behavior_signature(variant))

    def test_incomplete_or_failed_cases_have_no_behavior_signature(self):
        self.assertIsNone(policy.behavior_signature(fake_cases()[:-1]))
        for index in range(4):
            cases = fake_cases()
            cases[index]["status"] = "not_run"
            self.assertIsNone(policy.behavior_signature(cases))

    def test_assignment_requires_128_exact_bounded_integer_labels_and_string_case_id(self):
        for value in (True, 0.0, -1, 128, None):
            cases = fake_cases()
            cases[0]["assignment"][0] = value
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "behavior evidence"):
                    policy.behavior_signature(cases)
        for assignment in ([0] * 127, [0] * 129, tuple([0] * 128), None):
            cases = fake_cases()
            cases[0]["assignment"] = assignment
            with self.assertRaisesRegex(ValueError, "behavior evidence"):
                policy.behavior_signature(cases)
        cases = fake_cases()
        cases[0]["case_id"] = 0
        with self.assertRaisesRegex(ValueError, "behavior evidence"):
            policy.behavior_signature(cases)


class CommitmentTests(unittest.TestCase):
    def test_commitment_is_stable_and_hashes_only_allowed_design_winner_fields(self):
        population = policy.retain(seeds())
        winners, digest = policy.commitment(population, list(reversed(population)))
        expected_fields = {"source_id", "source_order", "graph_identity", "raw_sha256", "fitness", "origin"}
        self.assertEqual(set(winners), {"evolution", "control"})
        self.assertTrue(all(set(winner) == expected_fields for winner in winners.values()))
        self.assertEqual(winners["evolution"]["source_id"], "BF")
        expected_raw = json.dumps(winners, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        self.assertEqual(digest, hashlib.sha256(expected_raw).hexdigest())
        self.assertEqual(policy.commitment(list(reversed(population)), population), (winners, digest))

    def test_validation_feedback_cannot_change_design_commitment(self):
        population = policy.retain(seeds())
        original = policy.commitment(population, population)
        after_validation = copy.deepcopy(population)
        for candidate in after_validation:
            candidate["validation_results"] = {"used_bins": 99999 if candidate["source_id"] == "BF" else 1}
            candidate["validation_fitness"] = -99999 if candidate["source_id"] == "FF" else 99999
            candidate["validation_winner"] = candidate["source_id"] == "FF"
            candidate["diagnostic_message"] = "Invented adverse held-out outcome."
        self.assertEqual(policy.commitment(after_validation, after_validation), original)

    def test_changing_committed_source_identity_or_design_fitness_changes_hash(self):
        population = policy.retain(seeds())
        _, original_hash = policy.commitment(population, population)
        for field, value in (("source_id", "different-source"), ("raw_sha256", "0" * 64), ("origin", "generated")):
            changed = copy.deepcopy(population)
            changed[0][field] = value
            with self.subTest(field=field):
                self.assertNotEqual(policy.commitment(changed, population)[1], original_hash)
        changed = copy.deepcopy(population)
        changed[0]["fitness"] = policy.fitness(fake_cases(used=(50, 10, 60, 12)), DESIGN_IDS)
        self.assertNotEqual(policy.commitment(changed, population)[1], original_hash)

    def test_commitment_rejects_missing_two_entry_population(self):
        population = policy.retain(seeds())
        for evolution, control in (([], population), (population, population[:1]), (population + population[:1], population)):
            with self.assertRaisesRegex(ValueError, "missing population"):
                policy.commitment(evolution, control)


if __name__ == "__main__":
    unittest.main()
