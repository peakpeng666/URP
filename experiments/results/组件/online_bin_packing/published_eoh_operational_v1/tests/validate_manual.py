"""Fourteen fixed handwritten micro/fault requests, never benchmark data.

This script is inert on import. Execution requires an explicit reviewed-runtime
SHA256 and fresh output directory. Each dispatch intent and returned observation
is saved before assertions, including failed attempts. A failed check stops the
remaining requests; reruns require a different output directory. The hash is a
review pin, not authorization to run: the caller still needs the approved CPU
window. No model, generated candidate, downloaded program, or actual benchmark
instance is evaluated here.

Planned coverage: seven packing examples and seven transport faults. Worker
limits remain 20 CPU seconds, 30 wall seconds plus 1 cleanup second, and 2 GiB
address space. The two timeout probes shorten only the wall limit. There is no
unbounded/random/exhaustive test and no automatic retry.
"""

import argparse
import base64
import hashlib
import importlib.util
import json
import math
import os
import pathlib
import resource
import sys
import time
import traceback

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
METHOD = "EOH_formula_reimplementation"
AS = 2 * 1024**3
CPU = 20
WALL = 30
CLEANUP = 1
STDOUT_BOUND = 400_000
STDERR_BOUND = 16_384


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def save(path, value):
    """Create each evidence file once; never overwrite a previous attempt."""
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def load_checker():
    path = ROOT.parent / "paper_baseline_v1" / "src" / "checker.py"
    spec = importlib.util.spec_from_file_location("frozen_manual_checker", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.check_assignment


def expected_feasible_counts(items, capacity, assignment):
    residuals = [capacity] * len(items)
    counts = []
    for item, selected in zip(items, assignment):
        counts.append(sum(residual >= item for residual in residuals))
        require(residuals[selected] >= item, "selected bin was infeasible")
        residuals[selected] -= item
    return counts


def assert_execution_evidence(observation):
    require(type(observation.get("pid")) is int, "missing worker PID")
    require(observation.get("reaped") is True, "worker not confirmed reaped")
    require(observation.get("cpu_evidence_complete") is True,
            "incomplete per-worker CPU evidence")
    for key in ("worker_cpu_seconds", "wall_seconds", "cleanup_seconds"):
        value = observation.get(key)
        require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
                "invalid cost field: " + key)
    require(type(observation.get("worker_peak_rss_kib")) in (int, float)
            and observation["worker_peak_rss_kib"] > 0,
            "missing worker peak RSS")
    require(observation["cleanup_seconds"] <= CLEANUP + 0.5,
            "cleanup exceeded one-second allowance plus observation tolerance")
    for key, length_key, hash_key, bound in (
        ("raw_stdout_base64", "raw_output_bytes", "raw_output_sha256", STDOUT_BOUND),
        ("raw_stderr_base64", "stderr_bytes", "stderr_sha256", STDERR_BOUND),
    ):
        raw = base64.b64decode(observation[key], validate=True)
        require(len(raw) == observation[length_key] <= bound + 1,
                "bounded stream length evidence mismatch: " + key)
        require(hashlib.sha256(raw).hexdigest() == observation[hash_key],
                "bounded stream hash evidence mismatch: " + key)


def assert_warnings(result, capacity, item_count):
    warnings = result.get("warnings")
    require(type(warnings) is dict, "missing warning journal")
    require(warnings.get("complete") is True and warnings.get("bound_error") is None,
            "incomplete/bounded-out warning journal")
    kinds, events = warnings.get("kinds"), warnings.get("events")
    require(type(kinds) is list and type(events) is list, "warning journal schema")
    for event in events:
        require(type(event) is list and len(event) == 3,
                "warning event schema")
        require(type(event[2]) is int and 0 <= event[2] < len(kinds),
                "warning kind reference")
    if capacity == 500:
        require(len(events) == item_count, "not every capacity-500 warning was retained")
        require(all(kind.get("category") == "RuntimeWarning"
                    and kind.get("filename") == "formula.py"
                    and "overflow encountered in multiply" == kind.get("message")
                    for kind in kinds), "unexpected overflow-warning kind")
        require([event[:2] for event in events] == [["pack", i] for i in range(item_count)],
                "warning phases/item indices not preserved")
    else:
        require(kinds == [] and events == [], "unexpected warning on small microinput")


def assert_pack(observation, case, checker):
    assert_execution_evidence(observation)
    require(observation.get("returncode") == 0, "nonzero worker exit")
    require(observation.get("termination") is None, "worker terminated by bound")
    require(observation.get("error") is None, "worker transport/decode error")
    result = observation.get("result")
    require(type(result) is dict, "missing worker result")
    require(result.get("method") == METHOD and result.get("error") is None,
            "worker method/error mismatch")
    items, capacity = case["items"], case["capacity"]
    checked = checker(items, capacity, result["assignment"], result["used_bins"],
                      result["residuals"])
    require(result.get("pid") == observation["pid"], "worker PID mismatch")
    require(result.get("effective_limits") == {
        "RLIMIT_AS": [AS, AS], "RLIMIT_CPU": [CPU, CPU],
        "RLIMIT_FSIZE": [0, 0], "RLIMIT_NOFILE": [32, 32],
    }, "worker effective limits mismatch")
    require(result.get("n_bin_feasibility_checks") == len(items)**2,
            "all-bin feasibility work count mismatch")
    require(result.get("feasible_counts") == expected_feasible_counts(
        items, capacity, result["assignment"]), "feasible-count replay mismatch")
    if "expected_assignment" in case:
        require(result["assignment"] == case["expected_assignment"],
                "handwritten assignment expectation mismatch")
    assert_warnings(result, capacity, len(items))
    return checked


def manual_cases():
    # These are independently written tiny examples, not samples from data files.
    cases = [
        {"name": "empty", "items": [], "capacity": 100, "expected_assignment": []},
        {"name": "source_proven_non_exact_fit", "items": [4, 1], "capacity": 5,
         "expected_assignment": [0, 1]},
        {"name": "exact_fit", "items": [40, 60], "capacity": 100,
         "expected_assignment": [0, 0]},
        {"name": "full_duplicates", "items": [100, 100], "capacity": 100,
         "expected_assignment": [0, 1]},
        {"name": "equal_residual_first_tie", "items": [6, 6, 4], "capacity": 10,
         "expected_assignment": [0, 1, 0]},
        {"name": "low_integer_duplicates", "items": [1, 1, 1, 1], "capacity": 5,
         "expected_assignment": [0, 1, 2, 3]},
        {"name": "capacity500_warning_journal", "items": [1, 1], "capacity": 500,
         "expected_assignment": [0, 0]},
    ]
    for case in cases:
        case.update(kind="packing", method=METHOD, wall=WALL)
    plausible = {"method": METHOD, "error": None, "assignment": [],
                 "residuals": [], "used_bins": 0,
                 "feasible_counts": [], "n_bin_feasibility_checks": 0,
                 "effective_limits": {
                     "RLIMIT_AS": [AS, AS], "RLIMIT_CPU": [CPU, CPU],
                     "RLIMIT_FSIZE": [0, 0], "RLIMIT_NOFILE": [32, 32],
                 },
                 "warnings": {"kinds": [], "events": [], "complete": True,
                              "bound_error": None}}
    payload = json.dumps(plausible, separators=(",", ":"))
    faults = [
        ("stderr_separate", "import os;os.write(1,b'{}');os.write(2,b'handwritten stderr\\n')", WALL),
        ("malformed_json", "import os;os.write(1,b'{not-json')", WALL),
        ("nonzero_plausible_payload", "import json,os;p=json.loads(" + repr(payload)
         + ");p['pid']=os.getpid();os.write(1,json.dumps(p).encode());raise SystemExit(7)", WALL),
        ("stdout_bound", "import os,time;os.write(1,b'x'*500000);time.sleep(2)", WALL),
        ("stderr_bound", "import os,time;os.write(2,b'x'*20000);time.sleep(2)", WALL),
        ("timeout", "import time;time.sleep(2)", 0.1),
        ("eof_live_child", "import os,time;os.close(1);os.close(2);time.sleep(2)", 0.1),
    ]
    for name, code, wall in faults:
        cases.append({"name": name, "kind": "transport", "items": [],
                      "capacity": 100, "method": METHOD, "wall": wall,
                      "command": [sys.executable, "-B", "-c", code]})
    return cases


def assert_fault(observation, name):
    assert_execution_evidence(observation)
    if name == "stderr_separate":
        require(observation.get("returncode") == 0
                and observation.get("termination") is None
                and "unexpected nonempty stderr" in observation.get("error", "")
                and observation.get("result") is None, "nonempty stderr passed as success")
        require(observation.get("stderr_bytes") == len(b"handwritten stderr\n"),
                "stderr bytes not independently retained")
        require(observation.get("stderr_sha256") == hashlib.sha256(
            b"handwritten stderr\n").hexdigest(), "stderr evidence hash mismatch")
        require(base64.b64decode(observation["raw_stdout_base64"]) == b"{}",
                "stderr contaminated raw stdout")
    elif name == "malformed_json":
        require(observation.get("returncode") == 0 and bool(observation.get("error")),
                "malformed JSON passed decoding")
        require(not observation.get("result"), "malformed JSON produced a result")
    elif name == "nonzero_plausible_payload":
        require(observation.get("returncode") == 7, "nonzero exit code not preserved")
        require(observation.get("result") is None, "nonzero exit was decoded as success")
    elif name in ("stdout_bound", "stderr_bound"):
        stream = name.split("_")[0]
        expected = "output_limit" if stream == "stdout" else "stderr_limit"
        require(observation.get("termination") == expected,
                stream + " overflow was not classified")
        bound = STDOUT_BOUND if stream == "stdout" else STDERR_BOUND
        length_key = "raw_output_bytes" if stream == "stdout" else "stderr_bytes"
        require(0 < observation.get(length_key, 0) <= bound + 1,
                stream + " capture exceeded bound plus sentinel byte")
        require(observation.get("result") is None, "overflow produced a successful result")
    else:
        expected = "wall_timeout" if name == "timeout" else "wall_timeout_after_eof"
        require(observation.get("termination") == expected, "timeout classification")
        require(observation.get("result") is None, "timeout produced a successful result")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    parser.add_argument("--reviewed-runtime-sha256", required=True)
    parser.add_argument("--run-reviewed-manual", action="store_true", required=True)
    parser.add_argument("--cpu-budget", type=float, required=True)
    parser.add_argument("--wall-budget", type=float, required=True)
    args = parser.parse_args(argv)
    require(0 < args.cpu_budget <= 300 and 0 < args.wall_budget <= 600,
            "manual test budget outside approved-stage maximum")
    runtime_path = ROOT / "src" / "runtime.py"
    require(hashlib.sha256(runtime_path.read_bytes()).hexdigest()
            == args.reviewed_runtime_sha256, "reviewed runtime hash changed")
    from runtime import request
    checker = load_checker()
    args.output.mkdir(parents=True, exist_ok=False)
    resource.setrlimit(resource.RLIMIT_AS, (AS, AS))
    # Absolute process CPU limit supplements explicit accounted-cost reservations.
    ceiling = max(1, math.ceil(args.cpu_budget + time.process_time()))
    resource.setrlimit(resource.RLIMIT_CPU, (ceiling, ceiling))
    started, owncpu = time.monotonic(), time.process_time()
    before_children = resource.getrusage(resource.RUSAGE_CHILDREN)
    observations = []
    stop, failure = None, None
    cases = manual_cases()
    rows = [{"index": index, "name": case["name"], "status": "not_run"}
            for index, case in enumerate(cases)]
    try:
        save(args.output / "plan.json", {
            "scope": "handwritten operational validation only",
            "runtime_sha256": args.reviewed_runtime_sha256,
            "max_real_workers": len(cases), "benchmark_instances_solved": 0,
            "cpu_budget_seconds": args.cpu_budget,
            "wall_budget_seconds": args.wall_budget, "cases": cases,
        })
        for index, case in enumerate(cases):
            row = rows[index]
            if stop:
                continue
            worker_cpu = sum(o.get("worker_cpu_seconds", 0) for o in observations)
            if worker_cpu + time.process_time() - owncpu + CPU > args.cpu_budget:
                stop = "cpu_reservation"
                continue
            if time.monotonic() - started + case["wall"] + CLEANUP > args.wall_budget:
                stop = "wall_reservation"
                continue
            save(args.output / f"{index:02d}_{case['name']}_intent.json", {
                "meaning": "dispatch intent, not launch proof", "case": case,
                "elapsed_wall_seconds": time.monotonic() - started,
            })
            row["status"] = "dispatch_attempted"
            try:
                observation = request(case["items"], case["capacity"], METHOD,
                                      command=case.get("command"), wall=case["wall"])
                observations.append(observation)
                row["execution"] = observation
                save(args.output / f"{index:02d}_{case['name']}_observation.json", observation)
                if case["kind"] == "packing":
                    row["independent_check"] = assert_pack(observation, case, checker)
                else:
                    assert_fault(observation, case["name"])
                row["status"] = "passed"
            except Exception as exc:
                row.update(status="failed", error=type(exc).__name__ + ": " + str(exc))
                stop = "failed_manual_check"
                failure = traceback.format_exc()
            save(args.output / f"{index:02d}_{case['name']}_classification.json", row)
    except Exception:
        stop = "validation_or_persistence_failure"
        failure = traceback.format_exc()
    finally:
        for row in rows:
            if row["status"] == "not_run":
                row["not_run_reason"] = stop or "not_dispatched"
        after_children = resource.getrusage(resource.RUSAGE_CHILDREN)
        usage_cpu = (after_children.ru_utime + after_children.ru_stime
                     - before_children.ru_utime - before_children.ru_stime)
        saved_worker_cpu = sum(o.get("worker_cpu_seconds", 0) for o in observations)
        own = time.process_time() - owncpu
        wall = time.monotonic() - started
        attempted = sum(r["status"] != "not_run" for r in rows)
        complete = (len(observations) == attempted
                    and all(o.get("cpu_evidence_complete") is True for o in observations))
        summary = {
            "status": "passed" if stop is None and all(
                row["status"] == "passed" for row in rows) else "failed",
            "stop_reason": stop, "failure": failure, "planned_workers": len(cases),
            "attempted_requests": attempted, "returned_observations": len(observations),
            "passed_checks": sum(r["status"] == "passed" for r in rows),
            "benchmark_instances_solved": 0, "rows": rows,
            "worker_cpu_seconds": saved_worker_cpu,
            "RUSAGE_CHILDREN_delta_cpu_seconds": usage_cpu,
            "worker_cpu_evidence_complete": complete,
            "worker_cpu_sum_is_lower_bound_if_incomplete": not complete,
            "supervisor_cpu_seconds": own,
            "accounted_cpu_seconds": max(saved_worker_cpu, usage_cpu) + own,
            "wall_seconds": wall,
            "distinct_worker_pids": len({o["pid"] for o in observations if o.get("pid")}),
            "peak_worker_rss_kib": max((o.get("worker_peak_rss_kib") or 0
                                         for o in observations), default=0),
            "supervisor_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "effective_supervisor_limits": {
                "RLIMIT_AS": list(resource.getrlimit(resource.RLIMIT_AS)),
                "RLIMIT_CPU": list(resource.getrlimit(resource.RLIMIT_CPU)),
            },
            "accounting_note": "Measured before terminal summary publication; its bounded write/print is not claimed zero cost.",
        }
        if summary["accounted_cpu_seconds"] > args.cpu_budget or wall > args.wall_budget:
            summary.update(status="failed", stop_reason="observed_budget_exceeded")
        if not complete:
            summary.update(status="failed", stop_reason=stop or "incomplete_execution_evidence")
        try:
            save(args.output / "summary.json", summary)
        except Exception as exc:
            summary.update(status="failed", summary_persistence_error=str(exc))
        print(json.dumps(summary, indent=2, allow_nan=False), flush=True)
    return 0 if summary["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
