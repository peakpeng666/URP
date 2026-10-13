"""Read persisted results, check all routes, and replay without replacing runs."""
import argparse
import csv
import json
from pathlib import Path
import time
from urp_cvrp.checker import check_solution
from local_search_v2.run_experiment import ROOT, HERE, sha, inputs, summarize, write_json, utc
from local_search_v2.runtime import run


def verify(directory):
    directory = Path(directory).resolve()
    if not directory.is_relative_to(HERE):
        raise ValueError("only this experiment subtree")
    if (directory / "verification.json").exists():
        raise FileExistsError("verification is immutable; do not overwrite")
    start, cpu_start = time.perf_counter(), time.process_time()
    freeze = json.loads((directory / "freeze.json").read_text())
    result = json.loads((directory / "results.json").read_text())
    _, instances = inputs()
    by_id = {i.instance_id: i for i in instances}
    source_ok = all(sha(ROOT / r) == h for r, h in freeze["source_hashes"].items())
    snapshot_ok = all(sha(directory / "source_snapshot" / r) == h for r, h in freeze["source_hashes"].items())
    if not source_ok or not snapshot_ok:
        raise ValueError("source mismatch; do not run changed code as a replay")
    jsonl = [json.loads(line) for line in (directory / "raw.jsonl").read_text().splitlines()]
    with (directory / "raw.csv").open(newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    csv_ok = len(csv_rows) == len(result["runs"])
    for saved, text_row in zip(result["runs"], csv_rows):
        for key, value in saved.items():
            expected = json.dumps(value, allow_nan=False) if isinstance(value, (list, dict)) else "" if value is None else str(value)
            csv_ok = csv_ok and text_row[key] == expected
    schedule_ok = len(freeze["calls"]) == len(result["runs"]) and all(
        row["call_index"] == index and row["instance_id"] == call["instance_id"]
        and row["solver_seed"] == call["seed"] and row["algorithm"] == call["algorithm"]
        for index, (call, row) in enumerate(zip(freeze["calls"], result["runs"])))
    rechecked, replayed = [], []
    child_cpu = 0
    for row in result["runs"]:
        instance = by_id[row["instance_id"]]
        checked = check_solution(instance, {"routes": row["routes"], "reported_cost": row["reported_cost"]})
        rechecked.append(checked.accepted == row["accepted"] and
                         (not row["accepted"] or checked.recomputed_cost == row["recomputed_cost"]))
        repeat = run(instance, row["algorithm"], row["solver_seed"], result["config"])
        child_cpu += repeat["child_total_cpu_seconds"]
        output = repeat.get("output")
        replay_check = check_solution(instance, output)
        replayed.append({"call_index": row["call_index"], "status": repeat["status"],
                         "accepted": replay_check.accepted,
                         "same_routes": isinstance(output, dict) and output.get("routes") == row["routes"],
                         "same_cost": replay_check.accepted and replay_check.recomputed_cost == row["recomputed_cost"],
                         "child_total_cpu_seconds": repeat["child_total_cpu_seconds"],
                         "solver_cpu_seconds": repeat.get("solver_cpu_seconds"),
                         "search": output.get("search", {}) if isinstance(output, dict) else {}})
    legacy = json.loads((ROOT / "results/pilot.json").read_text())
    legacy_by_key = {(r["instance_id"], r["algorithm"], r["solver_seed"]): r for r in legacy["runs"]}
    legacy_checks = []
    for row in result["runs"]:
        old = legacy_by_key.get((row["instance_id"], row["algorithm"], row["solver_seed"]))
        if old:
            legacy_checks.append(row["routes"] == old["routes"] and row["recomputed_cost"] == old["recomputed_cost"])
    report = {"verified_utc": utc(), "source_hashes_match": source_ok, "snapshot_hashes_match": snapshot_ok,
              "prior_artifacts_unchanged": all(sha(ROOT / r) == h for r, h in freeze["prior_artifact_hashes"].items()),
              "raw_jsonl_matches_json": jsonl == result["runs"], "raw_csv_matches_json": csv_ok,
              "schedule_matches_freeze": schedule_ok,
              "summary_recomputed_matches": summarize(result["runs"], result["config"]) == result["summary"],
              "persisted_routes_rechecked": len(rechecked), "persisted_checks_match": sum(rechecked),
              "replay_count": len(replayed), "replay_exact_matches": sum(r["same_routes"] and r["same_cost"] for r in replayed),
              "legacy_constructor_comparisons": len(legacy_checks), "legacy_constructor_matches": sum(legacy_checks),
              "replays": replayed, "accounting": {"wall_seconds": time.perf_counter() - start,
              "parent_cpu_seconds": time.process_time() - cpu_start, "complete_child_cpu_seconds": child_cpu},
              "artifact_sha256": {p.name: sha(p) for p in directory.iterdir() if p.is_file()}}
    write_json(directory / "verification.json", report)
    print(json.dumps({k: v for k, v in report.items() if k not in ("replays", "artifact_sha256")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory")
    verify(parser.parse_args().directory)
