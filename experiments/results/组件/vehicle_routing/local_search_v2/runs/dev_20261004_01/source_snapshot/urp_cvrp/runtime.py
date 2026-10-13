"""Bounded-process execution for trusted development solvers.

A child process and bounded JSON protect the evaluation harness from crashes,
malformed results and time overruns. This is NOT a security sandbox for
untrusted/generated code. CPU time is a cooperative solver limit; the hard
supervisor wall limit includes process startup, validation and result transfer.
"""

import json
import multiprocessing
import time
import traceback

from .baselines import ALGORITHMS
from .budget import Budget, BudgetExceeded
from .instance import from_dict

MAX_RESULT_BYTES = 2_000_000


def _fault(name, instance):
    if name == "__fault_exception":
        raise RuntimeError("injected failure")
    if name == "__fault_hang":
        while True:
            time.sleep(10)
    if name == "__fault_nan":
        return {"routes": [], "reported_cost": float("nan")}
    if name == "__fault_oversized":
        return {"routes": [], "reported_cost": 0, "junk": "x" * MAX_RESULT_BYTES}
    if name == "__fault_invalid_node":
        return {"routes": [[0, instance.n_customers + 1, 0]], "reported_cost": 0}
    raise KeyError(f"unknown fault: {name}")


def _worker(connection, raw_instance, algorithm, seed, cpu_budget, wall_budget, allow_faults):
    started_cpu, started_wall = time.process_time(), time.perf_counter()
    envelope = {"status": "worker_error", "output": None, "error": "uninitialized"}
    budget = None
    try:
        instance = from_dict(raw_instance)
        budget = Budget(cpu_budget, wall_budget)
        if algorithm in ALGORITHMS:
            output = ALGORITHMS[algorithm](instance, seed, budget)
        elif allow_faults and algorithm.startswith("__fault_"):
            output = _fault(algorithm, instance)
        else:
            raise ValueError("algorithm is not in the fixed allowlist")
        budget.check()
        envelope = {"status": "returned", "output": output, "error": ""}
    except BudgetExceeded as exc:
        envelope = {"status": "budget_exceeded", "output": None, "error": str(exc)}
    except Exception as exc:
        envelope = {"status": "solver_exception", "output": None,
                    "error": f"{type(exc).__name__}: {str(exc)[:300]}"}
    finally:
        envelope["worker_cpu_seconds"] = time.process_time() - started_cpu
        envelope["worker_wall_seconds"] = time.perf_counter() - started_wall
        envelope["solver_cpu_seconds"] = time.process_time() - budget.start_cpu if budget else None
        envelope["solver_wall_seconds"] = time.perf_counter() - budget.start_wall if budget else None
        envelope["budget_checks"] = budget.checks if budget else 0
        try:
            import resource
            envelope["worker_peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        except ImportError:
            envelope["worker_peak_rss_kib"] = None
        try:
            encoded = json.dumps(envelope, allow_nan=False).encode()
            if len(encoded) > MAX_RESULT_BYTES:
                envelope.update(status="output_too_large", output=None, error="result byte limit exceeded")
                encoded = json.dumps(envelope, allow_nan=False).encode()
        except (TypeError, ValueError, OverflowError):
            envelope.update(status="invalid_serialization", output=None,
                            error="output is not finite strict JSON")
            encoded = json.dumps(envelope, allow_nan=False).encode()
        try:
            connection.send_bytes(encoded)
        finally:
            connection.close()


def run_isolated(instance, algorithm, seed, cpu_budget_seconds=0.25,
                 wall_budget_seconds=1.0, allow_faults=False):
    """Return status and telemetry even on timeout, crash or invalid output."""
    # Validate before launching; the same strict contract is checked in child.
    from_dict(instance.to_dict())
    Budget(cpu_budget_seconds, wall_budget_seconds)
    if type(seed) is not int or seed < 0:
        raise ValueError("solver seed must be a nonnegative integer")
    if algorithm not in ALGORITHMS and not (allow_faults and algorithm.startswith("__fault_")):
        raise ValueError("algorithm is not in the fixed allowlist")
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_worker, args=(sender, instance.to_dict(), algorithm, seed,
                                                   cpu_budget_seconds, wall_budget_seconds, allow_faults))
    start = time.perf_counter()
    result = None
    try:
        process.start()
        sender.close()
        remaining = max(0.0, wall_budget_seconds - (time.perf_counter() - start))
        if receiver.poll(remaining):
            try:
                result = json.loads(receiver.recv_bytes(maxlength=MAX_RESULT_BYTES))
            except (EOFError, OSError, ValueError):
                result = {"status": "worker_transport_error", "output": None,
                          "error": "worker closed or sent an invalid result"}
        else:
            result = {"status": "hard_wall_timeout", "output": None,
                      "error": "hard wall deadline, including process startup, exceeded"}
    finally:
        if process.pid is not None:
            process.join(timeout=0.05)
            if process.is_alive():
                process.terminate()
                process.join(timeout=0.5)
            if process.is_alive():
                process.kill()
                process.join(timeout=0.5)
        receiver.close()
        sender.close()
    result["total_wall_seconds"] = time.perf_counter() - start
    result["worker_exit_code"] = process.exitcode
    result["cpu_budget_seconds"] = cpu_budget_seconds
    result["wall_budget_seconds"] = wall_budget_seconds
    for key in ("solver_cpu_seconds", "solver_wall_seconds", "worker_cpu_seconds",
                "worker_wall_seconds", "worker_peak_rss_kib", "budget_checks"):
        result.setdefault(key, None)
    return result
