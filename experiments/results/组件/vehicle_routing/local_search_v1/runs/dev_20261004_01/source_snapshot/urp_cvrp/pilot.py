"""Run a strictly development-only, serial, small-budget pilot."""

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import statistics
import time

from . import __version__
from .baselines import ALGORITHM_VERSION
from .checker import CHECKER_VERSION, check_solution
from .instance import SPEC_VERSION, load_instance
from .runtime import run_isolated

LIMITATIONS = [
    "Development infrastructure self-check only; these are synthetic node-CVRP instances, not agricultural validation.",
    "No LLM/API/model training or generated-algorithm experiment was run. Required later P3/P5 LLM stages remain open.",
    "No PyVRP reproduction or mature strong-library baseline is complete. Three elementary construction baselines are implemented here.",
    "No trained selector, deployable selection gain, H1/H2 result, significance test or final held-out evaluation is claimed.",
    "Solver seeds are repeats of the same instance, not additional independent tasks. Nearest-neighbor and savings ignore seed by design.",
    "CPU budget is cooperative inside trusted solvers; supervisor wall timeout includes child startup and IPC. This is not a security sandbox.",
    "Objective is unrounded Euclidean distance in abstract coordinate units. No fixed fleet limit, route-count priority or agricultural constraints are modeled.",
    "Only this Debian cloud environment was exercised. Ubuntu 22.04 is a target, not a tested compatibility claim.",
]


def source_hash():
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def make_summary(runs, instance_count):
    by_algorithm = defaultdict(list)
    for run in runs:
        by_algorithm[run["algorithm"]].append(run)
    algorithms = {}
    for name, rows in by_algorithm.items():
        accepted = [row for row in rows if row["accepted"]]
        algorithms[name] = {
            "runs": len(rows), "accepted": len(accepted), "failed": len(rows) - len(accepted),
            "mean_distance_descriptive_only": statistics.mean(r["recomputed_cost"] for r in accepted) if accepted else None,
            "mean_solver_cpu_seconds": statistics.mean(r["solver_cpu_seconds"] for r in accepted) if accepted else None,
            "mean_total_wall_seconds": statistics.mean(r["total_wall_seconds"] for r in rows),
        }
    return {"instance_count": instance_count, "run_count": len(runs),
            "accepted_count": sum(r["accepted"] for r in runs),
            "failure_count": sum(not r["accepted"] for r in runs),
            "status_counts": dict(Counter(r["status"] for r in runs)),
            "algorithms": algorithms,
            "comparison_warning": "Pooled distances are only descriptive plumbing checks; no generalization or selector advantage follows."}


def run_pilot(config_path, data_dir, output_dir):
    config = json.loads(Path(config_path).read_text())
    if config.get("split") != "dev" or config.get("single_worker") is not True:
        raise ValueError("pilot requires development split and serial execution")
    manifest_path = Path(data_dir) / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("split") != "dev":
        raise ValueError("pilot cannot inspect a final test manifest")
    instances = []
    for entry in manifest["instances"]:
        filename = entry["file"]
        if Path(filename).name != filename:
            raise ValueError("manifest files must be local basenames")
        instance = load_instance(Path(data_dir) / filename)
        if instance.split != "dev" or instance.sha256 != entry["sha256"]:
            raise ValueError("data split or instance hash mismatch")
        instances.append(instance)
    # Freeze all experiment inputs before the first solver call. Existing
    # evidence is never silently replaced; choose a new output directory.
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename in ("freeze.json", "pilot.json", "pilot_raw.csv", "summary.json"):
        if (output_dir / filename).exists():
            raise FileExistsError(f"refuse to overwrite {output_dir / filename}; choose a new --output")
    frozen_source_hash = source_hash()
    frozen_manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    frozen_config_hash = hashlib.sha256(Path(config_path).read_bytes()).hexdigest()
    freeze = {"frozen_utc": datetime.now(timezone.utc).isoformat(),
              "source_sha256": frozen_source_hash, "manifest_sha256": frozen_manifest_hash,
              "config_sha256": frozen_config_hash, "config": config,
              "instance_sha256": {instance.instance_id: instance.sha256 for instance in instances},
              "split": "dev", "final_test_status": "not_generated_not_evaluated"}
    with (output_dir / "freeze.json").open("x") as handle:
        json.dump(freeze, handle, indent=2, allow_nan=False)
        handle.write("\n")
    started = datetime.now(timezone.utc).isoformat()
    parent_cpu, wall = time.process_time(), time.perf_counter()
    runs = []
    for instance in instances:
        for algorithm in config["algorithms"]:
            for seed in config["solver_seeds"]:
                run_id = f"{instance.instance_id}__{algorithm}__seed{seed}"
                run_started = datetime.now(timezone.utc).isoformat()
                result = run_isolated(instance, algorithm, seed, config["cpu_budget_seconds"], config["wall_budget_seconds"])
                output = result.pop("output", None)
                check_started = time.perf_counter()
                check = check_solution(instance, output)
                check_wall = time.perf_counter() - check_started
                returned = result["status"] == "returned"
                status = ("ok" if check.accepted else "checker_rejected") if returned else result["status"]
                runs.append({
                    "run_id": run_id, "instance_id": instance.instance_id,
                    "instance_sha256": instance.sha256, "split": instance.split,
                    "generation_seed": instance.generation_seed, "family": instance.family,
                    "n_customers": instance.n_customers, "algorithm": algorithm,
                    "algorithm_version": ALGORITHM_VERSION, "solver_seed": seed,
                    "started_utc": run_started, "finished_utc": datetime.now(timezone.utc).isoformat(),
                    **result, "status": status, "accepted": returned and check.accepted,
                    "feasible": returned and check.feasible, "cost_consistent": returned and check.cost_consistent,
                    "recomputed_cost": check.recomputed_cost,
                    "reported_cost": output.get("reported_cost") if type(output) is dict else None,
                    "routes": output.get("routes") if type(output) is dict else None,
                    "errors": list(check.errors) if returned else [result["error"]],
                    "route_loads": list(check.route_loads), "route_count": check.route_count,
                    "checker_wall_seconds": check_wall,
                })
    result = {
        "schema_version": "cvrp-pilot-v1", "status": "development_self_check_only",
        "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
        "spec": {"version": SPEC_VERSION, "objective": "sum_unrounded_euclidean_distance",
                 "depot": 0, "fleet": "unlimited_identical_vehicles", "distance_units": "abstract_coordinate_units"},
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "operating_system": platform.freedesktop_os_release(), "machine": platform.machine(),
                        "cpu_model": next((line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines() if line.startswith("model name")), "unknown"),
                        "thread_policy": "serial supervisor; one solver process; standard library only",
                        "package_version": __version__, "checker_version": CHECKER_VERSION,
                        "algorithm_version": ALGORITHM_VERSION, "source_sha256": frozen_source_hash},
        "config": config, "manifest_sha256": frozen_manifest_hash, "config_sha256": frozen_config_hash,
        "input_freeze": freeze, "source_unchanged_during_run": source_hash() == frozen_source_hash,
        "instances": [instance.to_dict() for instance in instances], "runs": runs,
        "summary": make_summary(runs, len(instances)), "limitations": LIMITATIONS,
        "accounting": {"pilot_wall_seconds": time.perf_counter() - wall,
                       "parent_cpu_seconds": time.process_time() - parent_cpu,
                       "sum_child_worker_cpu_seconds": sum(r["worker_cpu_seconds"] or 0 for r in runs),
                       "sum_solver_cpu_budget_seconds": sum(r["cpu_budget_seconds"] for r in runs),
                       "sum_supervisor_wall_budget_seconds": sum(r["wall_budget_seconds"] for r in runs),
                       "note": "Child interpreter startup CPU is not included in worker CPU; timeout CPU would be missing, not zero-cost. Total wall includes child startup/IPC but checker time is separately measured."},
    }
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "pilot.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    with (output_dir / "pilot_raw.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(runs[0]) if runs else ["run_id"])
        writer.writeheader()
        for row in runs:
            writer.writerow({key: json.dumps(value, allow_nan=False) if isinstance(value, (list, dict)) else value
                             for key, value in row.items()})
    (output_dir / "summary.json").write_text(json.dumps(result["summary"], indent=2) + "\n")
    print(json.dumps(result["summary"], indent=2))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/pilot.json")
    parser.add_argument("--data", default="data/dev")
    parser.add_argument("--output", default="results")
    args = parser.parse_args()
    run_pilot(args.config, args.data, args.output)


if __name__ == "__main__":
    main()
