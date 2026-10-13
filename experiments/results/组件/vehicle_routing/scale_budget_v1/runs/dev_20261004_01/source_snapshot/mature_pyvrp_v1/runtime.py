"""Trusted, serial subprocess runner with per-child Linux wait4 accounting.

wait4 captures interpreter startup, imports, validation, solver, serialization,
and teardown CPU, including killed children. This is NOT an adversarial sandbox.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

from urp_cvrp.budget import Budget, BudgetExceeded
from urp_cvrp.instance import from_dict
from mature_pyvrp_v1.adapter import solve, prepare

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 2_000_000


def worker(payload):
    entered = time.process_time()
    instance = from_dict(payload["instance"])
    config = payload["config"]
    prepare(payload["algorithm"])
    budget = Budget(config["cpu_budget_seconds"], config["wall_budget_seconds"])
    envelope = {"status": "returned", "output": None, "error": None}
    try:
        algorithm = payload["algorithm"]
        if payload.get("allow_faults") and algorithm == "__spin":
            while True:
                pass
        elif payload.get("allow_faults") and algorithm == "__sleep":
            time.sleep(10)
        elif payload.get("allow_faults") and algorithm == "__exception":
            raise RuntimeError("injected")
        elif payload.get("allow_faults") and algorithm == "__nan":
            envelope["output"] = {"routes": [], "reported_cost": float("nan")}
        else:
            envelope["output"] = solve(instance, algorithm, payload["seed"], budget, config)
    except BudgetExceeded as exc:
        envelope.update(status="budget_exceeded", error=str(exc))
    except Exception as exc:
        envelope.update(status="solver_exception", error=f"{type(exc).__name__}: {str(exc)[:500]}")
    envelope.update(solver_cpu_seconds=time.process_time() - budget.start_cpu,
                    solver_wall_seconds=time.perf_counter() - budget.start_wall,
                    worker_cpu_seconds=time.process_time() - entered,
                    budget_checks=budget.checks)
    try:
        encoded = json.dumps(envelope, allow_nan=False)
        if len(encoded.encode()) > MAX_BYTES:
            raise ValueError("result too large")
    except (ValueError, TypeError, OverflowError) as exc:
        envelope.update(status="invalid_serialization", output=None, error=str(exc))
        encoded = json.dumps(envelope, allow_nan=False)
    print(encoded)


def run(instance, algorithm, seed, config, allow_faults=False):
    if not hasattr(os, "wait4"):
        raise RuntimeError("This experiment requires Linux/POSIX wait4 accounting")
    if algorithm not in config["algorithms"] and not (allow_faults and algorithm.startswith("__")):
        raise ValueError("algorithm outside frozen allowlist")
    if type(seed) is not int or seed < 0:
        raise ValueError("invalid solver seed")
    overall_wall, parent_cpu = time.perf_counter(), time.process_time()
    with tempfile.TemporaryDirectory(prefix="cvrp-vnd-") as tmp:
        tmp = Path(tmp)
        payload = {"instance": instance.to_dict(), "algorithm": algorithm,
                   "seed": seed, "config": config, "allow_faults": allow_faults}
        input_path = tmp / "input.json"
        input_path.write_text(json.dumps(payload, allow_nan=False))
        launched = time.perf_counter()
        timed_out = False
        with (tmp / "stdout").open("wb") as stdout, (tmp / "stderr").open("wb") as stderr:
            process = subprocess.Popen([sys.executable, "-m", "mature_pyvrp_v1.runtime", str(input_path)],
                                       cwd=ROOT, stdout=stdout, stderr=stderr,
                                       env={**os.environ, "PYTHONHASHSEED": "0", "OMP_NUM_THREADS": "1",
                                            "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
            while True:
                pid, status, usage = os.wait4(process.pid, os.WNOHANG)
                if pid:
                    break
                if time.perf_counter() - launched >= config["wall_budget_seconds"]:
                    timed_out = True
                    os.kill(process.pid, signal.SIGKILL)
                    _, status, usage = os.wait4(process.pid, 0)
                    break
                time.sleep(0.001)
            process.returncode = os.waitstatus_to_exitcode(status)
        process_wall = time.perf_counter() - launched
        result = {"status": "hard_wall_timeout" if timed_out else "transport_error", "output": None,
                  "error": "hard wall deadline exceeded" if timed_out else "invalid/missing worker output"}
        path = tmp / "stdout"
        if not timed_out and path.stat().st_size <= MAX_BYTES:
            try:
                result = json.loads(path.read_text(), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
            except (ValueError, UnicodeError):
                pass
        stderr_path = tmp / "stderr"
        with stderr_path.open("rb") as handle:
            error_excerpt = handle.read(1000).decode(errors="replace")
        result.update(child_user_cpu_seconds=usage.ru_utime, child_system_cpu_seconds=usage.ru_stime,
                      child_total_cpu_seconds=usage.ru_utime + usage.ru_stime,
                      child_peak_rss_kib=usage.ru_maxrss, child_exit_code=process.returncode,
                      process_wall_seconds=process_wall, stderr_excerpt=error_excerpt,
                      cpu_budget_seconds=config["cpu_budget_seconds"],
                      wall_budget_seconds=config["wall_budget_seconds"])
    result.update(total_wall_seconds=time.perf_counter() - overall_wall,
                  supervisor_cpu_seconds=time.process_time() - parent_cpu)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    args = parser.parse_args()
    worker(json.loads(Path(args.input).read_text()))
