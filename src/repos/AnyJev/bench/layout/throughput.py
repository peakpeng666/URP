"""Decisions per GPU-second, and how many fit at once.

Single-request latency is the wrong question for a decision endpoint: what a deployment cares about
is how many decisions a card retires per second, and that is set by how many fit in memory at once.
The two ways of running L0's K cyclic shifts differ in exactly that:

  shared prefix, K sequences   the prefix KV is replicated once per branch, so M decisions hold
                               M x K copies of it. This is what `score_shared` and an engine prefix
                               cache do today.
  packed, one forward          the prefix KV is stored once per decision, so M decisions hold M
                               copies, and the branches attend into it through a block mask.

Both compute the same thing -- `packed.py --check` shows the readouts agree to fp noise -- so this
measures only the cost. Concurrency M is swept until the card refuses, and the columns to read are
decisions per second and the M it died at.

    python -m bench.layout.throughput --model Qwen/Qwen2.5-7B-Instruct --state-tokens 600

Research log entry 22.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.cache_utils import DynamicCache

from anyjev.readout import DEFAULT_SYSTEM, build_prompt, map_label_tokens, render_chat, resolve_labels
from bench.layout._splice import common_affixes
from bench.tasks import get_task

FILLER = (" The customer also mentioned an earlier ticket about the same order and asked for a "
          "written confirmation once the refund clears.")


def one_decision(tok, state, q, labels, perms):
    ids = [tok.encode(render_chat(tok, build_prompt(state, q, p, DEFAULT_SYSTEM, labels)),
                      add_special_tokens=False) for p in perms]
    shared = min(common_affixes(ids[0], other)[0] for other in ids[1:])
    return ids[0][:shared], [seq[shared:] for seq in ids]


def shared_path(model, prefix, branches, M):
    """M decisions, each carried as K sequences against its own replicated prefix KV."""
    device = model.device
    P, K, W = len(prefix), len(branches), max(len(b) for b in branches)
    pre = torch.as_tensor(prefix, device=device)[None].expand(M, -1).contiguous()
    with torch.no_grad():
        first = model(input_ids=pre, position_ids=torch.arange(P, device=device)[None].expand(M, -1),
                      use_cache=True)
    wide = DynamicCache()
    for i, layer in enumerate(first.past_key_values.layers):
        wide.update(layer.keys.repeat_interleave(K, 0), layer.values.repeat_interleave(K, 0), i)
    toks = torch.zeros((M * K, W), dtype=torch.long, device=device)
    keep = torch.zeros((M * K, W), dtype=torch.long, device=device)
    for m in range(M):
        for k, b in enumerate(branches):
            toks[m * K + k, : len(b)] = torch.as_tensor(b, device=device)
            keep[m * K + k, : len(b)] = 1
    full = torch.cat([torch.ones((M * K, P), dtype=torch.long, device=device), keep], 1)
    pos = torch.arange(P, P + W, device=device)[None].expand(M * K, -1)
    with torch.no_grad():
        model(input_ids=toks, position_ids=pos, attention_mask=full, past_key_values=wide,
              use_cache=True)


def packed_path(model, prefix, branches, M, mask_1):
    """M decisions, each one packed sequence: the prefix once, the K branches behind a block mask."""
    device = model.device
    ids_1, pos_1 = packed_ids(prefix, branches, device)
    ids = ids_1.expand(M, -1).contiguous()
    pos = pos_1.expand(M, -1).contiguous()
    mask = mask_1.expand(M, -1, -1, -1)
    with torch.no_grad():
        model(input_ids=ids, position_ids=pos, attention_mask=mask)


def packed_ids(prefix, branches, device):
    ids = list(prefix)
    pos = list(range(len(prefix)))
    for b in branches:
        ids += list(b)
        pos += list(range(len(prefix), len(prefix) + len(b)))
    return (torch.as_tensor(ids, device=device)[None], torch.as_tensor(pos, device=device)[None])


def packed_mask(prefix, branches, device, dtype):
    n = len(prefix) + sum(len(b) for b in branches)
    p = len(prefix)
    causal = torch.tril(torch.ones((n, n), dtype=torch.bool, device=device))
    allow = torch.zeros((n, n), dtype=torch.bool, device=device)
    allow[:p, :p] = causal[:p, :p]
    at = p
    for b in branches:
        allow[at:at + len(b), :p] = True
        allow[at:at + len(b), at:at + len(b)] = causal[at:at + len(b), at:at + len(b)]
        at += len(b)
    neg = torch.finfo(dtype).min
    return torch.where(allow, torch.zeros((), dtype=dtype, device=device),
                       torch.full((), neg, dtype=dtype, device=device))[None, None]


def measure(fn, repeats=3):
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    try:
        fn()                                       # warm up / allocate
    except torch.cuda.OutOfMemoryError:
        torch.cuda.empty_cache()
        return None, None
    torch.cuda.synchronize()
    ts = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        torch.cuda.synchronize()
        ts.append(time.perf_counter() - t0)
    return float(np.median(ts)), torch.cuda.max_memory_allocated() / 2 ** 30


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--task", default="massive_route")
    ap.add_argument("--state-tokens", type=int, default=600)
    ap.add_argument("--concurrency", default="1,2,4,8,16,32")
    ap.add_argument("--dtype", default="bfloat16")
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)

    dtype = getattr(torch, args.dtype)
    tok = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=dtype,
                                                 attn_implementation="sdpa").to("cuda").eval()
    task = get_task(args.task)
    test, _ = task.split(4, 0, 0)
    q = task.question
    labels, _ = resolve_labels(tok, q)
    map_label_tokens(tok, labels)                  # fail early if the labels are not single tokens
    K = q.k
    perms = [[(j + s) % K for j in range(K)] for s in range(K)]

    state = str(test[0][0])
    while len(tok.encode(state, add_special_tokens=False)) < args.state_tokens:
        state += FILLER
    prefix, branches = one_decision(tok, state, q, labels, perms)
    n_packed = len(prefix) + sum(len(b) for b in branches)
    print(f"{args.model} ({args.dtype}, sdpa) | {args.task} K={K}")
    print(f"one decision: prefix {len(prefix)} tok, {K} branches x {len(branches[0])} tok "
          f"-> packed sequence {n_packed} tok")
    print(f"prefix KV held per decision: shared path {K}x, packed path 1x\n")

    mask_1 = packed_mask(prefix, branches, model.device, dtype)
    rows = []
    header = (f"{'M':>4}{'shared ms':>11}{'shared GiB':>12}{'shared dec/s':>14}"
              f"{'packed ms':>11}{'packed GiB':>12}{'packed dec/s':>14}{'speedup':>9}")
    print(header)
    print("-" * len(header))
    for M in [int(x) for x in args.concurrency.split(",")]:
        st, sg = measure(lambda: shared_path(model, prefix, branches, M))
        pt, pg = measure(lambda: packed_path(model, prefix, branches, M, mask_1))
        row = {"M": M, "shared_ms": st and 1000 * st, "shared_gib": sg,
               "packed_ms": pt and 1000 * pt, "packed_gib": pg,
               "shared_dps": st and M / st, "packed_dps": pt and M / pt}
        rows.append(row)
        fmt = lambda v, w, p: (f"{v:>{w}.{p}f}" if v is not None else f"{'OOM':>{w}}")  # noqa: E731
        sp = (f"{row['packed_dps'] / row['shared_dps']:>8.2f}x"
              if st and pt else f"{'-':>9}")
        print(f"{M:>4}{fmt(row['shared_ms'],11,1)}{fmt(sg,12,2)}{fmt(row['shared_dps'],14,1)}"
              f"{fmt(row['packed_ms'],11,1)}{fmt(pg,12,2)}{fmt(row['packed_dps'],14,1)}{sp}")
        if st is None and pt is None:
            break
    if args.out:
        with open(args.out, "w") as fh:
            json.dump({"model": args.model, "task": args.task, "K": K, "dtype": args.dtype,
                       "state_tokens": args.state_tokens, "prefix": len(prefix),
                       "branch": len(branches[0]), "packed_len": n_packed, "rows": rows}, fh)
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
