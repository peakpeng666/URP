"""What a rotation actually costs, so a saved rotation can be converted into saved seconds.

`position_prior.py` shows that a K-way decision does not need K rotations: a sequential rule that
stops on the running top-1 margin returns full-L0's own answer on 99% of items for a mean of about
four rotations instead of K. That is a saving in *forwards*, and forwards are not what a card charges
for. The K rotations share the `[state][question]` prefix, so the tokens a decision actually computes
are

    P + R * B          P = prefix tokens, B = option-block tokens, R = rotations read

and cutting R from K to 4 buys K/4 only when P is negligible. On a router reading one utterance it
nearly is; in an agentic loop with a 2000-token context it is not. The ratio is the deliverable, not a
single number, so this measures R in {1, 2, 4, K} against the state length.

The packed path (research log entry 22) is measured alongside as the control: it computes the same
tokens in one kernel launch and, as entry 22 found, wins nothing on time because the workload is
already feed-forward-bound.

    python -m bench.layout.serve_cost --model Qwen/Qwen2.5-7B-Instruct --task massive_route

Research log entry 23.
"""
from __future__ import annotations

import argparse
import json
import sys

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from anyjev.calibrate.permute import spread_order
from anyjev.readout import map_label_tokens, resolve_labels
from bench.layout.throughput import FILLER, measure, one_decision, packed_mask, packed_path, shared_path
from bench.tasks import get_task


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--task", default="massive_route")
    ap.add_argument("--state-tokens", default="0,200,600,1500",
                    help="0 means the task's own states, untouched")
    ap.add_argument("--rotations", default="1,2,4",
                    help="rotation budgets to price against the full K")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--dtype", default="bfloat16")
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)

    dtype = getattr(torch, args.dtype)
    tok = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=dtype,
                                                 attn_implementation="sdpa").to("cuda").eval()
    task = get_task(args.task)
    items, _ = task.split(4, 0, 0)
    q = task.question
    labels, _ = resolve_labels(tok, q)
    map_label_tokens(tok, labels)                 # fail early if a label is not a single token
    K = q.k
    perms = [[(j + s) % K for j in range(K)] for s in range(K)]
    order = spread_order(K)
    budgets = [int(x) for x in args.rotations.split(",")]
    M = args.concurrency

    print(f"{args.model} ({args.dtype}, sdpa) | {args.task} K={K} | {M} decisions in flight")
    print("rows are state length; each budget shows ms per batch and the speedup over full K\n")
    cols = "".join(f"{f'R={r}':>18}" for r in budgets)
    head = f"{'state':>7}{'prefix':>8}{'block':>7}{'K ms':>9}{'packed':>9}{cols}"
    print(head)
    print("-" * len(head))
    rows = []
    for want in [int(x) for x in args.state_tokens.split(",")]:
        state = str(items[0][0])
        while want and len(tok.encode(state, add_special_tokens=False)) < want:
            state += FILLER
        prefix, branches = one_decision(tok, state, q, labels, perms)
        P, B = len(prefix), max(len(b) for b in branches)
        mask_1 = packed_mask(prefix, branches, model.device, dtype)
        full, _ = measure(lambda: shared_path(model, prefix, branches, M))
        pack, _ = measure(lambda: packed_path(model, prefix, branches, M, mask_1))
        row = {"state_tokens": want or len(tok.encode(state, add_special_tokens=False)),
               "prefix": P, "block": B, "full_ms": 1000 * full, "packed_ms": 1000 * pack,
               "full_dps": M / full, "budgets": {}}
        cells = ""
        for r in budgets:
            sub = [branches[s] for s in order[:r]]
            t, _ = measure(lambda: shared_path(model, prefix, sub, M))
            row["budgets"][r] = {"ms": 1000 * t, "dps": M / t, "speedup": full / t,
                                 "token_ratio": (P + K * B) / (P + r * B)}
            cells += f"{1000 * t:>9.1f}{full / t:>8.2f}x"
        rows.append(row)
        print(f"{row['state_tokens']:>7}{P:>8}{B:>7}{1000 * full:>9.1f}{1000 * pack:>9.1f}{cells}")
    print("\nthe arithmetic ceiling for budget R is (P + K*B) / (P + R*B):")
    for row in rows:
        ratios = "  ".join(f"R={r}: {row['budgets'][r]['token_ratio']:.2f}x" for r in budgets)
        print(f"  state {row['state_tokens']:>5} tok, prefix {row['prefix']:>5}   {ratios}")
    if args.out:
        with open(args.out, "w") as fh:
            json.dump({"model": args.model, "task": args.task, "K": K, "dtype": args.dtype,
                       "concurrency": M, "spread_order": list(order), "rows": rows}, fh, indent=1)
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
