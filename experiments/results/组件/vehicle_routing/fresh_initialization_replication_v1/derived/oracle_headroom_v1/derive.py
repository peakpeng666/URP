"""Post-hoc development oracle, using existing primary outputs only.

No solvers are imported or executed. Every input cell must contain all five
predeclared seeds, accepted and in budget. A seed is never an inference unit.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, median
import time

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent.parent
RUN = STUDY / "runs/dev_20261004_01"
ALGORITHMS = ("multistart_vnd", "pyvrp_ils_random", "pyvrp_ils_savings_warm")
SEEDS = (11, 29, 47, 71, 97)
PROFILES = {"cpu025": 0.25, "cpu100": 1.0}
FAMILIES = {"multistart_vnd": "VND", "pyvrp_ils_random": "PyVRP",
            "pyvrp_ils_savings_warm": "PyVRP"}
TIE_TOLERANCE = 1e-9


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def original_hashes():
    """Protect every previously existing study artifact, excluding caches."""
    return {str(p.relative_to(STUDY)): sha256(p)
            for p in sorted(STUDY.rglob("*")) if p.is_file()
            and "derived" not in p.relative_to(STUDY).parts
            and "__pycache__" not in p.relative_to(STUDY).parts}


def stats(values):
    return {"mean": mean(values), "median": median(values),
            "minimum": min(values), "maximum": max(values), "sum": sum(values)}


def regret(costs, oracle):
    gaps = [c - o for c, o in zip(costs, oracle)]
    assert all(g >= -1e-10 for g in gaps)
    return {
        "absolute_distance_units": stats(gaps),
        "relative_to_oracle_percent": stats([100 * g / o for g, o in zip(gaps, oracle)]),
        "recoverable_improvement_over_configuration_percent": stats(
            [100 * g / c for g, c in zip(gaps, costs)]),
        "ratio_of_mean_costs_regret_percent": 100 * (mean(costs) - mean(oracle)) / mean(oracle),
        "ratio_of_mean_costs_improvement_percent": 100 * (mean(costs) - mean(oracle)) / mean(costs),
        "strict_positive_regret_instances": sum(g > TIE_TOLERANCE for g in gaps),
        "oracle_tied_instances": sum(abs(g) <= TIE_TOLERANCE for g in gaps),
    }


def aggregate_cells(runs):
    assert len(runs) == 600, "Use all 600 primary calls, not replay or filtered cases"
    assert sorted(r["call_index"] for r in runs) == list(range(600))
    cells = defaultdict(dict)
    distributions = {}
    for row in runs:
        assert row["accepted"] and row["budget_conformant"] and row["scoreable"]
        assert row["split"] == "dev" and row["n_customers"] == 200
        assert row["algorithm"] in ALGORITHMS and row["profile"] in PROFILES
        assert row["solver_seed"] in SEEDS
        assert row["cpu_budget_seconds"] == PROFILES[row["profile"]]
        assert row["family"] in ("uniform", "clustered")
        value = row["recomputed_cost"]
        assert math.isfinite(value) and value > 0
        key = row["profile"], row["instance_id"], row["algorithm"]
        assert row["solver_seed"] not in cells[key], "Duplicate seed"
        cells[key][row["solver_seed"]] = value
        old = distributions.setdefault(row["instance_id"], row["family"])
        assert old == row["family"]
    assert len(distributions) == 20
    assert Counter(distributions.values()) == {"uniform": 10, "clustered": 10}
    assert len(cells) == 120
    for profile in PROFILES:
        for instance in distributions:
            for algorithm in ALGORITHMS:
                assert set(cells[profile, instance, algorithm]) == set(SEEDS)
    return {k: mean(v[s] for s in SEEDS) for k, v in cells.items()}, distributions


def analyze(runs):
    cells, distributions = aggregate_cells(runs)
    budgets = {}
    for profile, ceiling in PROFILES.items():
        ids = sorted(distributions)
        costs = {a: [cells[profile, i, a] for i in ids] for a in ALGORITHMS}
        means = {a: mean(values) for a, values in costs.items()}
        best = min(ALGORITHMS, key=lambda a: means[a])
        oracle = [min(cells[profile, i, a] for a in ALGORITHMS) for i in ids]
        pyvrp_oracle = [min(cells[profile, i, a] for a in ALGORITHMS[1:]) for i in ids]
        rows = []
        winners = Counter()
        family_winners = Counter()
        for i, optimum, pyvrp_optimum in zip(ids, oracle, pyvrp_oracle):
            values = {a: cells[profile, i, a] for a in ALGORITHMS}
            tied = [a for a in ALGORITHMS if abs(values[a] - optimum) <= TIE_TOLERANCE]
            winner_label = "|".join(tied)
            family_label = "|".join(sorted({FAMILIES[a] for a in tied}))
            winners[winner_label] += 1
            family_winners[family_label] += 1
            gap = values[best] - optimum
            rows.append({"instance_id": i, "distribution": distributions[i],
                         "five_seed_mean_costs": values,
                         "oracle_winner_configurations": tied,
                         "oracle_winner_algorithm_families": sorted({FAMILIES[a] for a in tied}),
                         "oracle_cost": optimum, "pyvrp_initialization_oracle_cost": pyvrp_optimum,
                         "best_single_configuration": best,
                         "best_single_absolute_regret": gap,
                         "best_single_relative_regret_to_oracle_percent": 100 * gap / optimum,
                         "best_single_recoverable_improvement_percent": 100 * gap / values[best],
                         "additional_absolute_headroom_from_vnd": pyvrp_optimum - optimum})
        normalized_best = min(ALGORITHMS,
                              key=lambda a: mean(c / o for c, o in zip(costs[a], oracle)))
        budgets[profile] = {
            "cpu_ceiling_seconds": ceiling, "instances": 20,
            "configuration_mean_costs": means, "best_single_configuration": best,
            "best_single_by_mean_relative_oracle_regret": normalized_best,
            "oracle_mean_cost": mean(oracle),
            "configuration_winner_counts": {a: winners.get(a, 0) for a in ALGORITHMS},
            "tied_winner_sets": {a: n for a, n in winners.items() if "|" in a},
            "algorithm_family_winner_counts": dict(sorted(family_winners.items())),
            "configuration_residual_regret": {a: regret(costs[a], oracle) for a in ALGORITHMS},
            "best_single_residual_regret": regret(costs[best], oracle),
            "within_pyvrp_initialization_headroom": regret(costs[best], pyvrp_oracle),
            "additional_vnd_family_headroom_after_pyvrp_initialization_oracle": regret(pyvrp_oracle, oracle),
            "distribution_summaries": {}, "instances_detail": rows,
        }
        for distribution in ("uniform", "clustered"):
            subset = [r for r in rows if r["distribution"] == distribution]
            counts = Counter("|".join(r["oracle_winner_configurations"]) for r in subset)
            budgets[profile]["distribution_summaries"][distribution] = {
                "instances": len(subset),
                "configuration_winner_counts": {a: counts.get(a, 0) for a in ALGORITHMS},
                "best_single_residual_regret": regret(
                    [r["five_seed_mean_costs"][best] for r in subset],
                    [r["oracle_cost"] for r in subset]),
            }
    return budgets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "analysis.json")
    args = parser.parse_args()
    assert not args.output.exists(), "Never overwrite an existing derivation"
    wall_start, cpu_start = time.perf_counter(), time.process_time()
    before = original_hashes()
    results = json.loads((RUN / "results.json").read_text())
    assert results["source_unchanged"] and results["prior_artifacts_unchanged"]
    budgets = analyze(results["runs"])
    after = original_hashes()
    assert before == after, "Previously existing study artifacts changed"
    output = {
        "schema_version": "cvrp-fresh-posthoc-oracle-headroom-v1",
        "scope": "Post-hoc descriptive development analysis of 600 primary calls; 20 base instances",
        "source_sha256": sha256(Path(__file__).resolve()),
        "input_results_sha256": sha256(RUN / "results.json"),
        "original_study_artifact_hashes": before,
        "original_study_artifacts_unchanged": before == after,
        "algorithm_families": FAMILIES,
        "formulas": {
            "cell_cost": "C[i,a,b] = arithmetic mean of the five original unrounded validated seed costs",
            "best_single": "argmin_a mean_i C[i,a,b], independently for each CPU ceiling",
            "oracle": "O[i,b] = min_a C[i,a,b]; min AFTER averaging seeds, never per-seed cherry-picking",
            "absolute_regret": "C[i,a,b] - O[i,b] in original coordinate distance units",
            "relative_regret": "100 * (C[i,a,b] - O[i,b]) / O[i,b]; then arithmetic mean over instances",
            "recoverable_improvement": "100 * (C[i,a,b] - O[i,b]) / C[i,a,b]; then arithmetic mean over instances",
            "ratio_of_means": "Reported separately; not interchangeable with mean instance-relative percentages",
            "winner_ties": "Absolute cost tolerance 1e-9; exact minimum still defines oracle cost",
        },
        "limitations": [
            "The best fixed configuration and oracle winners are chosen after seeing the same development outcomes.",
            "Two algorithm families are represented; PyVRP random and warm are initialization-policy variants.",
            "This is not an executable selector, not a confidence bound, and not a generalization guarantee.",
            "Five-seed means are estimated from CPU-stopped runs; observed timed replay variation remains relevant.",
            "The oracle assumes free knowledge of outcomes; feature extraction, selection, training and mistakes have no charged deployment model here.",
            "Small residual quality gaps alone do not justify selector training; assess additional mature-family coverage first.",
            "No solver rerun, selector training, library tuning or final-holdout access occurs in this analysis.",
        ],
        "budgets": budgets,
        "derivation_accounting": {
            "process_cpu_seconds_before_final_serialization": time.process_time() - cpu_start,
            "wall_seconds_before_final_serialization": time.perf_counter() - wall_start,
            "scope": "Parsing, arithmetic and before/after hashing; excludes interpreter startup, final write, tests and independent review",
        },
    }
    with args.output.open("x") as stream:
        json.dump(output, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"output": str(args.output), "sha256": sha256(args.output),
                      "prior_hashes_unchanged": before == after,
                      "derivation_accounting": output["derivation_accounting"]}, indent=2))


if __name__ == "__main__":
    main()
