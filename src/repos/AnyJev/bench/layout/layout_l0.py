"""Where should the state sit in a decision prompt, and what does each choice let a cache keep?

  state-first     [P][State][Question][Options]   what AnyJev does today. Only P is a prefix, so the
                  K cyclic shifts share the state within a request and nothing is shared across them.
  question-first  [P][Question][Options][State]   the whole fixed block becomes a prefix, cached once
                  for every request the endpoint ever serves; the state is re-encoded once per shift.
  middle-state    [P][Question][State][Options]   [P][Question] is cached across requests and the
                  state is encoded once and shared by the K shifts.

With a prefix cache that is on -- the only honest baseline -- the tokens that must really go through
the model per request are |S| + K(|Q|+|O|), K(|S|+1) and |S| + K|O| respectively, so which layout wins
is a function of the state length and K and there is a crossover. Scored at L0 (cyclic-shift
marginalisation), because raw carries the position bias that L0 exists to remove, and with thinking
disabled, because a reasoning model left in thinking mode puts the answer somewhere else entirely.

    python -m bench.layout.layout_l0 --model Qwen/Qwen2.5-7B-Instruct --task massive_route

Research log entry 20. Results in bench/results_layout/2026-09-26/r_l0_*.json.
"""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from anyjev.readout import DEFAULT_SYSTEM, label_ids_for_perm, map_label_tokens, resolve_labels
from bench.layout._splice import ece
from bench.tasks import get_task

LAYOUTS = ("state-first", "question-first", "middle-state")


def render(tok, state, q, perm, labels, layout):
    """The same content in three orders. Everything else -- system prompt, wording, the trailing
    instruction, the assistant header -- is held fixed so the only variable is where the state sits."""
    options = "\n".join(f"{labels[j]}. {q.options[perm[j]]}" for j in range(q.k))
    block_state = f"State:\n{state if state else '(empty)'}"
    block_q = f"Question: {q.text}"
    if q.kind == "noul":
        block_o, tail = f"Answer {labels[perm[0]]} or {labels[perm[1]]}.", ""
    else:
        block_o, tail = "Options:\n" + options, "Answer with the letter only."
    user = {"state-first": f"{block_state}\n\n{block_q}\n{block_o}\n{tail}",
            "question-first": f"{block_q}\n{block_o}\n\n{block_state}\n{tail}",
            "middle-state": f"{block_q}\n\n{block_state}\n\n{block_o}\n{tail}"}[layout]
    messages = [{"role": "system", "content": DEFAULT_SYSTEM}, {"role": "user", "content": user}]
    try:
        return tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True,
                                       enable_thinking=False)
    except TypeError:
        return tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)


def log_probs(model, tok, items, q, labels, label_ids, layout, perm, batch_size):
    """Label log-probabilities in *position* order for this permutation."""
    read_ids = label_ids_for_perm(q, label_ids, perm)   # positional for choice, by word for noul
    out = []
    for i in range(0, len(items), batch_size):
        prompts = [render(tok, s, q, perm, labels, layout) for s, _ in items[i:i + batch_size]]
        enc = tok(prompts, return_tensors="pt", padding=True, add_special_tokens=False).to("cuda")
        with torch.no_grad():
            logits = model(**enc).logits[:, -1, :].float()
        take = torch.as_tensor(read_ids, device="cuda")
        out.append(torch.log_softmax(logits, -1)[:, take].cpu().numpy())
    return np.concatenate(out)


def normalise(log_p):
    p = np.exp(log_p - log_p.max(1, keepdims=True))
    return p / p.sum(1, keepdims=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--task", default="massive_route")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--dtype", default="bfloat16")
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)

    tok = AutoTokenizer.from_pretrained(args.model)
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        args.model, torch_dtype=getattr(torch, args.dtype)).to("cuda").eval()

    task = get_task(args.task)
    test, _ = task.split(args.n, 4, 0)
    q = task.question
    labels, _ = resolve_labels(tok, q)
    label_ids = list(map_label_tokens(tok, labels))
    y = np.asarray([label for _, label in test])
    K = q.k

    n_tok = lambda text: len(tok.encode(text, add_special_tokens=False))   # noqa: E731
    lens = {"state": int(np.mean([n_tok(f"State:\n{s}") for s, _ in test])),
            "question": n_tok(f"Question: {q.text}"),
            "options": n_tok("Options:\n" + "\n".join(f"{labels[j]}. {q.options[j]}"
                                                      for j in range(K)))}
    print(f"{args.model} ({args.dtype}) | {args.task} K={K} n={len(test)} | L0 over {K} cyclic shifts")
    print(f"mean token lengths: state {lens['state']}, question {lens['question']}, "
          f"options {lens['options']}")

    results = {}
    for layout in LAYOUTS:
        per_shift = []
        for shift in range(K):
            perm = [(j + shift) % K for j in range(K)]      # the option shown at slot j
            lp = log_probs(model, tok, test, q, labels, label_ids, layout, perm, args.batch_size)
            back = np.empty_like(lp)
            back[:, perm] = lp                              # back to option order
            per_shift.append(back)
        raw = normalise(per_shift[0])
        marginal = normalise(np.mean(per_shift, 0))          # log-space mean = geometric mean
        reversed_ = per_shift[K // 2] if K > 1 else per_shift[0]
        results[layout] = {"raw_acc": float(np.mean(raw.argmax(1) == y)), "raw_ece": ece(raw, y),
                           "flip": float(np.mean(per_shift[0].argmax(1) != reversed_.argmax(1))),
                           "l0_acc": float(np.mean(marginal.argmax(1) == y)),
                           "l0_ece": ece(marginal, y), "l0_pred": marginal.argmax(1).tolist()}
        r = results[layout]
        print(f"  {layout:<15} raw acc {r['raw_acc']:.3f} ece {r['raw_ece']:.3f} "
              f"flip {r['flip']:.3f}  |  L0 acc {r['l0_acc']:.3f} ece {r['l0_ece']:.3f}")

    base = np.asarray(results["state-first"]["l0_pred"]) == y
    draws = np.random.RandomState(0).randint(0, len(y), (1000, len(y)))
    for layout in LAYOUTS[1:]:
        cur = np.asarray(results[layout]["l0_pred"]) == y
        diffs = [float(np.mean(cur[i].astype(float) - base[i].astype(float))) for i in draws]
        lo, hi = np.percentile(diffs, [2.5, 97.5])
        results[layout]["l0_delta"] = [float(np.mean(diffs)), float(lo), float(hi)]
        verdict = "no worse" if lo > -0.02 else ("WORSE" if hi < 0 else "inconclusive")
        print(f"  L0: {layout} minus state-first {np.mean(diffs):+.3f}  "
              f"95% CI [{lo:+.3f}, {hi:+.3f}]  -> {verdict}")

    s, qn, on = lens["state"], lens["question"], lens["options"]
    plans = {"state-first": s + K * (qn + on), "question-first": K * (s + 1),
             "middle-state": s + K * on}
    print(f"\ntokens through the model per request with the prefix cache ON, K={K}:")
    for name, value in plans.items():
        print(f"  {name:<15} {value:>7}   ({plans['state-first'] / value:>5.1f}x vs state-first)")
    print("  crossover as the state grows:")
    for length in (20, 50, 200, 1000, 4000):
        grown = {"state-first": length + K * (qn + on), "question-first": K * (length + 1),
                 "middle-state": length + K * on}
        best = min(grown, key=grown.get)
        print(f"    state {length:>5} tok -> cheapest {best:<15} {grown[best]:>7} tokens "
              f"({grown['state-first'] / grown[best]:.1f}x vs state-first)")

    if args.out:
        with open(args.out, "w") as fh:
            json.dump({"model": args.model, "task": args.task, "n": len(test), "K": K,
                       "dtype": args.dtype, "lens": lens, "plans": plans, "res": results}, fh)
        print(f"wrote {args.out}")


if __name__ == "__main__":
    sys.exit(main())
