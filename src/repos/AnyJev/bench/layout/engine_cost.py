"""Does the rotation budget survive a real engine, and how wide should a wave be.

On the transformers backend a saved cyclic shift is a saved chunk of one forward, and
`bench/layout/serve_cost.py` prices it directly. On a vLLM server the arithmetic is the same -- the
shifts of one state share the `[state][question]` prefix and the server's prefix cache keeps it -- but
the accounting is not: every shift is an HTTP request, and `adaptive_shifts` reads them in rounds, so
each round is a barrier the whole batch waits on. Reading K shifts in one round can therefore beat
reading four shifts in four rounds even though it computes far more.

`adaptive_wave` is the knob for that: it asks for w shifts per round, giving up a little precision in
where the rule stops in exchange for K/w rounds instead of K. This measures where the trade lands, with
the threshold calibrated the label-free way first, so every row is serving the same guarantee.

    vllm serve Qwen/Qwen2.5-7B-Instruct --host 127.0.0.1 --port 8137 --enable-prefix-caching
    python -m bench.layout.engine_cost --backend vllm --base-url http://127.0.0.1:8137 --n 300
    python -m bench.layout.engine_cost --backend hf --n 300     # same table, local transformers

`requests/decision` is the count the engine actually saw. `agree` is against the full-cycle readout on
the same states, which is what the stopping rule promises to reproduce.

Research log entry 24.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import numpy as np

from anyjev import Decider
from bench.tasks import get_task


def counted(backend):
    """Wrap the backend so every prompt it is asked to score is counted.

    Idempotent: the local backend is loaded once and shared by every row, so wrapping it again per
    row would nest the counters and multiply the count by the number of rows."""
    if getattr(backend, "_counting", False):
        backend.n_requests = 0
        return backend
    backend.n_requests = 0
    backend._counting = True
    inner = backend.next_token_logprobs

    def counting(prompts, token_ids):
        backend.n_requests += len(prompts)
        return inner(prompts, token_ids)

    backend.next_token_logprobs = counting
    return backend


def run(tag, dec, states, labels, q, level, reference=None):
    dec.backend.n_requests = 0
    t0 = time.perf_counter()
    out = dec.decide_batch(list(states), q, level=level)
    dt = time.perf_counter() - t0
    pred = [o.argmax for o in out]
    shifts = [o.diagnostics.get("shifts_used", q.k) for o in out]
    row = {"readout": tag, "level": out[0].level, "seconds": dt,
           "decisions_per_s": len(states) / dt,
           "requests_per_decision": dec.backend.n_requests / len(states),
           "mean_shifts": float(np.mean(shifts)),
           "accuracy": float(np.mean([p == q.options[y] for p, y in zip(pred, labels)])),
           "agree": (1.0 if reference is None
                     else float(np.mean([a == b for a, b in zip(pred, reference)])))}
    return row, pred


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backend", default="vllm", choices=["vllm", "hf"])
    ap.add_argument("--base-url", default="http://127.0.0.1:8137")
    ap.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--task", default="massive_route")
    ap.add_argument("--n", type=int, default=300, help="test states")
    ap.add_argument("--calib", type=int, default=300, help="states for the label-free certificate")
    ap.add_argument("--waves", default="1,2,4,6")
    ap.add_argument("--target", type=float, default=0.01)
    ap.add_argument("--workers", type=int, default=64,
                    help="client-side fan-out; large enough that the server's batching is the limit")
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)

    task = get_task(args.task)
    test, calib = task.split(args.n, args.calib, 0)
    q = task.question
    states = [s for s, _ in test]
    labels = [y for _, y in test]
    where = args.base_url if args.backend == "vllm" else "local transformers"
    print(f"{args.model} on {args.backend} ({where}) | {args.task} K={q.k} | "
          f"{len(states)} test states, {len(calib)} for calibration")

    if args.backend == "vllm":
        from anyjev.backends.vllm import VLLMBackend

        def make():
            return VLLMBackend(args.base_url, args.model, workers=args.workers)
    else:
        from anyjev.backends.hf import HFBackend

        shared = HFBackend(args.model)          # one load, reused by every row

        def make():
            return shared

    def decider(**kw):
        return Decider(counted(make()), **kw)

    # the reference: every shift, every time
    full = decider(adaptive_shifts=False)
    ref_row, reference = run(f"L0, all {q.k} shifts (reference)", full, states, labels, q, "L0")
    rows = [ref_row]

    # the certificate, paid once on unlabelled states
    cal = decider()
    t0 = time.perf_counter()
    cert = cal.calibrate_adaptive(q, [s for s, _ in calib], target=args.target)
    cal_time, cal_reqs = time.perf_counter() - t0, cal.backend.n_requests
    print(f"certificate: threshold {cert['threshold']}, bound {cert.get('bound')}, "
          f"{cert.get('mean_shifts')} mean shifts on the calibration states "
          f"({cal_reqs} requests, {cal_time:.1f}s, no labels)")
    if cert["threshold"] is None:
        print("nothing could be certified at this target; every row below would read every shift")

    for w in [int(x) for x in args.waves.split(",")]:
        dec = decider(adaptive_wave=w)
        dec._stop[q.key] = cert
        row, _ = run(f"L0, adaptive, wave {w}", dec, states, labels, q, "L0", reference)
        rows.append(row)

    # L1 costs the same shifts plus one scalar; measured once to show the temperature is free
    best = int(max(rows[1:], key=lambda r: r["decisions_per_s"])["readout"].split()[-1])
    l1 = decider(adaptive_wave=best)
    l1._stop[q.key] = cert
    l1.calibrate(q, [s for s, _ in calib], [y for _, y in calib], level="L1")
    row, _ = run(f"L1, adaptive, wave {best}", l1, states, labels, q, "L1", reference)
    rows.append(row)

    head = (f"{'readout':>34}{'lvl':>5}{'req/dec':>9}{'shifts':>8}{'sec':>8}"
            f"{'dec/s':>8}{'vs ref':>8}{'agree':>7}{'acc':>7}")
    print()
    print(head)
    print("-" * len(head))
    base = rows[0]["decisions_per_s"]
    for r in rows:
        print(f"{r['readout']:>34}{r['level']:>5}{r['requests_per_decision']:>9.2f}"
              f"{r['mean_shifts']:>8.2f}{r['seconds']:>8.1f}{r['decisions_per_s']:>8.2f}"
              f"{r['decisions_per_s'] / base:>7.2f}x{r['agree']:>7.3f}{r['accuracy']:>7.3f}")
    print("\nrequests/decision is what the engine saw; dec/s is wall clock on the client. A wide wave "
          "reads more shifts than it needs but waits on fewer rounds, so the two columns move apart.")

    if args.out:
        with open(args.out, "w") as fh:
            json.dump({"model": args.model, "task": args.task, "K": q.k, "engine": args.backend,
                       "base_url": args.base_url if args.backend == "vllm" else None,
                       "n_test": len(states), "n_calib": len(calib),
                       "target": args.target, "certificate": cert,
                       "calibration_requests": cal_reqs, "calibration_seconds": cal_time,
                       "rows": rows}, fh, indent=1)
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
