"""Freeze and execute one complete development batch. Never overwrite a run."""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import random
import shutil
import statistics
import time

from urp_cvrp.instance import load_instance
from urp_cvrp.checker import check_solution
from mature_pyvrp_v1.runtime import run

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, data):
    with Path(path).open("x") as handle:
        json.dump(data, handle, indent=2, allow_nan=False)
        handle.write("\n")


def inputs():
    path = ROOT / "data/dev/manifest.json"
    manifest = json.loads(path.read_text())
    if manifest["split"] != "dev":
        raise ValueError("dev only")
    instances = []
    for entry in manifest["instances"]:
        if Path(entry["file"]).name != entry["file"]:
            raise ValueError("local basename required")
        instance = load_instance(path.parent / entry["file"])
        if instance.split != "dev" or instance.sha256 != entry["sha256"]:
            raise ValueError("split or instance hash mismatch")
        instances.append(instance)
    return manifest, instances


def describe(values):
    return {"mean": statistics.mean(values), "median": statistics.median(values),
            "minimum": min(values), "maximum": max(values)} if values else None


def summarize(rows, config):
    by_algorithm = defaultdict(list)
    by_key = defaultdict(dict)
    for row in rows:
        by_algorithm[row["algorithm"]].append(row)
        by_key[(row["instance_id"], row["algorithm"])][row["solver_seed"]] = row
    methods = {}
    for method, runs in by_algorithm.items():
        methods[method] = {
            "runs": len(runs), "accepted": sum(r["accepted"] for r in runs),
            "status_counts": dict(Counter(r["status"] for r in runs)),
            "search_termination_counts": dict(Counter(r["search"].get("termination", "constructor") for r in runs)),
            "solver_cpu_seconds": describe([r["solver_cpu_seconds"] for r in runs if r.get("solver_cpu_seconds") is not None]),
            "child_total_cpu_seconds": describe([r["child_total_cpu_seconds"] for r in runs]),
            "total_wall_seconds": describe([r["total_wall_seconds"] for r in runs]),
            "peak_rss_kib": describe([r["child_peak_rss_kib"] for r in runs]),
            "cooperative_cpu_overshoot_seconds": max(max(0, r.get("solver_cpu_seconds", 0) - config["cpu_budget_seconds"]) for r in runs),
        }
    comparisons = {}
    for baseline, candidate in (("parallel_savings", "savings_vnd"), ("savings_vnd", "multistart_vnd"), ("multistart_vnd", "pyvrp_ils_s1e6"), ("pyvrp_ils_s1e6", "pyvrp_ils_s1e9")):
        instance_rows = []
        missing = []
        for instance_id in sorted({r["instance_id"] for r in rows}):
            left = by_key[(instance_id, baseline)]
            right = by_key[(instance_id, candidate)]
            if any(seed not in left or seed not in right or not left[seed]["accepted"] or not right[seed]["accepted"] for seed in config["solver_seeds"]):
                missing.append(instance_id)
                continue
            base_cost = statistics.mean(left[s]["recomputed_cost"] for s in config["solver_seeds"])
            candidate_cost = statistics.mean(right[s]["recomputed_cost"] for s in config["solver_seeds"])
            reduction = 100 * (base_cost - candidate_cost) / base_cost if base_cost else 0
            r = next(iter(left.values()))
            instance_rows.append({"instance_id": instance_id, "family": r["family"], "n_customers": r["n_customers"],
                                  "baseline_mean_cost": base_cost, "candidate_mean_cost": candidate_cost,
                                  "reduction_percent": reduction})
        cells = defaultdict(list)
        for r in instance_rows:
            cells[f'{r["family"]}_n{r["n_customers"]}'].append(r["reduction_percent"])
        reductions = [r["reduction_percent"] for r in instance_rows]
        comparisons[f"{candidate}_vs_{baseline}"] = {
            "paired_instances": len(instance_rows), "missing_incomplete_instances": missing,
            "unit": "equal-weight base instance after mean over solver seeds; development descriptive only",
            "reduction_percent": describe(reductions),
            "wins": sum(x > 1e-7 for x in reductions), "ties": sum(abs(x) <= 1e-7 for x in reductions),
            "losses": sum(x < -1e-7 for x in reductions),
            "strata": {k: {"n_instances": len(v), **describe(v)} for k, v in sorted(cells.items())},
            "instances": instance_rows,
        }
    return {"runs": len(rows), "instances": len({r["instance_id"] for r in rows}),
            "accepted": sum(r["accepted"] for r in rows), "algorithms": methods,
            "comparisons": comparisons,
            "claims": "Development mature-solver integration and scale sensitivity only. Strong-library adequacy, H1, H2, selectors and final holdouts remain open."}


def dependency_state_ok():
    provenance = json.loads((HERE / "dependency_provenance.json").read_text())
    dist = importlib.metadata.distribution("pyvrp")
    return dist.version == "0.14.0" and all(
        sha(dist.locate_file(rel)) == value
        for rel, value in provenance["pyvrp_installed_file_sha256"].items())


def execute(output):
    if not dependency_state_ok():
        raise ValueError("installed PyVRP differs from recorded dependency provenance")
    config = json.loads((HERE / "protocol.json").read_text())
    if config["split"] != "dev" or not config["single_worker"]:
        raise ValueError("dev serial only")
    output = Path(output).resolve()
    if not output.is_relative_to(HERE):
        raise ValueError("all run outputs must stay under this experiment subtree")
    output.mkdir(parents=True, exist_ok=False)
    manifest, instances = inputs()
    source_paths = sorted(list((ROOT / "urp_cvrp").glob("*.py")) + list(HERE.glob("*.py")) + [ROOT / "local_search_v2/solvers.py", ROOT / "local_search_v2/__init__.py", HERE / "protocol.json", HERE / "PROTOCOL.md", HERE / "requirements.lock.txt", HERE / "dependency_provenance.json"])
    source_hashes = {str(path.relative_to(ROOT)): sha(path) for path in source_paths}
    prior_paths = sorted([p for p in (ROOT / "results").iterdir() if p.is_file()] + list((ROOT / "data/dev").glob("*.json")))
    for previous in ("local_search_v1", "local_search_v2"):
        prior_paths += list((ROOT / previous).glob("*.py"))
        for pattern in ("*.json", "*.jsonl", "*.csv"):
            prior_paths += list((ROOT / previous / "runs").rglob(pattern))
    old_hashes = {str(p.relative_to(ROOT)): sha(p) for p in prior_paths}
    schedule = [(instance.instance_id, seed) for instance in instances for seed in config["solver_seeds"]]
    rng = random.Random(config["schedule_seed"])
    rng.shuffle(schedule)
    calls = []
    for instance_id, seed in schedule:
        methods = config["algorithms"][:]
        rng.shuffle(methods)
        calls.extend({"instance_id": instance_id, "seed": seed, "algorithm": method} for method in methods)
    packages = {}
    for name in ("pyvrp", "ortools", "vrpy", "numpy", "scipy"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    freeze = {"frozen_utc": utc(), "config": config, "source_hashes": source_hashes,
              "prior_artifact_hashes": old_hashes, "manifest_sha256": sha(ROOT / "data/dev/manifest.json"),
              "instance_sha256": {i.instance_id: i.sha256 for i in instances}, "calls": calls,
              "environment": {"python": platform.python_version(), "platform": platform.platform(),
                              "os": platform.freedesktop_os_release(), "packages": packages,
                              "cpu_model": next((line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines() if line.startswith("model name")), "unknown")},
              "final_holdout_status": "not_read_not_generated_not_evaluated"}
    for path in source_paths:
        destination = output / "source_snapshot" / path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    write_json(output / "freeze.json", freeze)
    by_id = {i.instance_id: i for i in instances}
    rows = []
    started_utc = utc()
    cpu_start, wall_start = time.process_time(), time.perf_counter()
    with (output / "raw.jsonl").open("x") as log:
        for index, call in enumerate(calls):
            instance = by_id[call["instance_id"]]
            result = run(instance, call["algorithm"], call["seed"], config)
            solver_output = result.pop("output")
            check_cpu, check_wall = time.process_time(), time.perf_counter()
            check = check_solution(instance, solver_output)
            checker_cpu, checker_wall = time.process_time() - check_cpu, time.perf_counter() - check_wall
            returned = result["status"] == "returned"
            row = {"call_index": index, "instance_id": instance.instance_id, "instance_sha256": instance.sha256,
                   "split": "dev", "family": instance.family, "n_customers": instance.n_customers,
                   "algorithm": call["algorithm"], "solver_seed": call["seed"], **result,
                   "status": ("ok" if check.accepted else "checker_rejected") if returned else result["status"],
                   "accepted": returned and check.accepted, "recomputed_cost": check.recomputed_cost if returned and check.accepted else None,
                   "reported_cost": solver_output.get("reported_cost") if isinstance(solver_output, dict) else None,
                   "routes": solver_output.get("routes") if isinstance(solver_output, dict) else None,
                   "search": solver_output.get("search", {}) if isinstance(solver_output, dict) else {},
                   "checker_errors": list(check.errors), "route_count": check.route_count,
                   "route_loads": list(check.route_loads), "checker_cpu_seconds": checker_cpu,
                   "checker_wall_seconds": checker_wall}
            rows.append(row)
            log.write(json.dumps(row, allow_nan=False) + "\n")
            log.flush()
            if (index + 1) % 60 == 0:
                print(f"{index + 1}/{len(calls)} calls recorded; {sum(r['accepted'] for r in rows)} accepted", flush=True)
    batch_wall, batch_cpu = time.perf_counter() - wall_start, time.process_time() - cpu_start
    child_cpu = sum(r["child_total_cpu_seconds"] for r in rows)
    result = {"started_utc": started_utc, "finished_utc": utc(), "config": config,
              "runs": rows, "summary": summarize(rows, config),
              "accounting": {"batch_wall_seconds": batch_wall, "batch_parent_cpu_seconds": batch_cpu,
                             "sum_complete_child_cpu_seconds": child_cpu,
                             "batch_parent_plus_complete_child_cpu_seconds": batch_cpu + child_cpu,
                             "sum_solver_cpu_seconds": sum(r.get("solver_cpu_seconds", 0) for r in rows),
                             "sum_checker_cpu_seconds": sum(r["checker_cpu_seconds"] for r in rows),
                             "sum_configured_cpu_budget_seconds": len(rows) * config["cpu_budget_seconds"],
                             "scope": "batch loop including raw-log flushes; excludes preparation/freezing, tests, final serialization, verification, development and human/model labor",
                             "external_model_api_calls": 0, "paid_api_cost": 0,
                             "currency_note": "No paid/model API used; cloud platform/assistant subscription cost not estimated"},
              "installed_pyvrp_files_unchanged": dependency_state_ok(),
              "source_unchanged": all(sha(ROOT / rel) == h for rel, h in source_hashes.items()),
              "prior_artifacts_unchanged": all(sha(ROOT / rel) == h for rel, h in old_hashes.items())}
    write_json(output / "results.json", result)
    write_json(output / "summary.json", result["summary"])
    with (output / "raw.csv").open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, allow_nan=False) if isinstance(v, (dict, list)) else v for k, v in row.items()})
    print(json.dumps({"output": str(output), "accepted": result["summary"]["accepted"], "runs": len(rows),
                      "accounting": result["accounting"], "source_unchanged": result["source_unchanged"],
                      "prior_artifacts_unchanged": result["prior_artifacts_unchanged"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    execute(parser.parse_args().output)
