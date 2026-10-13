"""What the K cyclic shifts actually buy, and whether one forward can buy the same thing.

A K-way choice at L0 is asked K times with the option list rotated, and the K readouts are averaged
in log space. `docs/levels.md` states the product precisely: if the position bias is additive in
logit space,

    logit(option i shown at position j)  =  c_i + b_j ,

a full cycle gives every option every position, the b term becomes a constant the softmax drops, and
"the result no longer depends on how you listed the options". That is an invariance guarantee, and it
costs K forwards -- K copies of the option block through every feed-forward block, which is where a
decision's FLOPs go (attention is 2-7% of a prefill at these lengths, so no attention-side trick can
reach it: research log entries 21 and 22).

This script prices that guarantee and tests three ways of getting it, or something near it, for one
forward instead of K:

  the position prior   estimate b once per (model, question) from the mean log-prob at each position
                       over *unlabelled* states, subtract it, serve one rotation. Needs no labels;
                       the repo's own prior study already noted that a position-profile prior equals
                       permutation-only under a full cycle.
  the batch prior      the label-prior correction AnyJev already ships, estimated from one rotation
                       instead of K.
  pick the rotation    if one fixed arrangement is as good as the average, canonicalising the option
                       order gives the invariance by construction and the only question left is which
                       arrangement to fix. The per-rotation accuracy spread says whether that is a
                       free choice or a lottery.

The first table is the one that decides: if the K-rotation average sits inside the spread of the
individual rotations, the K forwards are buying invariance and not accuracy, and invariance is
available for one forward by fixing the order before the model ever sees it.

Collection and analysis are separate. One GPU pass records the label log-probs of every rotation of
every item; everything after that is a numpy replay, so a new variant costs nothing.

    python -m bench.layout.position_prior --model Qwen/Qwen2.5-7B-Instruct --task massive_route \
        --n 900 --dump bench/results_layout/2026-09-27/pp_q25_massive.npz
    python -m bench.layout.position_prior --replay bench/results_layout/2026-09-27/pp_q25_massive.npz

Columns. `fwd` is forwards per decision at serve time. `agree` is how often the readout returns what
full L0 returns -- the drop-in-replacement number. `flip` is how often the answer changes under a
different rotation, which measures the bias a single rotation leaves behind. `ECE` is label-free;
`ECE_T` additionally fits one temperature on the calibration labels, which is what L1 does.

Research log entry 23.
"""
from __future__ import annotations

import argparse
import json
import sys
from math import lgamma

import numpy as np

from anyjev.calibrate.permute import spread_order

PRIOR_STRENGTH = 0.75          # the shipped default for the batch prior (anyjev/calibrate)


# ---------------------------------------------------------------- collection (GPU)
def collect(args):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from anyjev.readout import (
        DEFAULT_SYSTEM,
        build_prompt,
        label_ids_for_perm,
        map_label_tokens,
        render_chat,
        resolve_labels,
    )
    from bench.tasks import get_task

    tok = AutoTokenizer.from_pretrained(args.model)
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        args.model, torch_dtype=getattr(torch, args.dtype)).to("cuda").eval()
    task = get_task(args.task)
    items, _ = task.split(args.n, 0, 0)               # shuffled; the replay splits calib / test
    q = task.question
    labels, _ = resolve_labels(tok, q)
    label_ids = list(map_label_tokens(tok, labels))
    K = q.k

    out = np.zeros((len(items), K, K), dtype=np.float32)          # [item, rotation, position]
    for s in range(K):
        perm = [(j + s) % K for j in range(K)]
        read = torch.as_tensor(label_ids_for_perm(q, label_ids, perm), device="cuda")
        rows = []
        for i in range(0, len(items), args.batch_size):
            prompts = [render_chat(tok, build_prompt(st, q, perm, DEFAULT_SYSTEM, labels))
                       for st, _ in items[i:i + args.batch_size]]
            enc = tok(prompts, return_tensors="pt", padding=True,
                      add_special_tokens=False).to("cuda")
            with torch.no_grad():
                logits = model(**enc).logits[:, -1, :].float()
            rows.append(torch.log_softmax(logits, -1)[:, read].cpu().numpy())
        out[:, s, :] = np.concatenate(rows)
        print(f"  rotation {s + 1}/{K} done", flush=True)
    perms = np.asarray([[(j + s) % K for j in range(K)] for s in range(K)], dtype=np.int64)
    np.savez_compressed(args.dump, logp=out, y=np.asarray([lab for _, lab in items]),
                        perms=perms, model=args.model, task=args.task)
    print(f"wrote {args.dump}  [{out.shape[0]} items x {K} rotations x {K} positions]")


# ---------------------------------------------------------------- analysis (CPU)
def score(logp, perms, shifts, b_pos=None, b_opt=None):
    """Mean log-prob per *option* over the given rotations.

    logp is indexed by position and perms[s][j] is the option shown at position j under rotation s,
    so the assignment below is the un-permutation. `b_pos` is subtracted in position space (a position
    prior), `b_opt` in option space (a label prior). Averaging in log space is what L0 does."""
    shifts = list(shifts)
    total = np.zeros((logp.shape[0], logp.shape[2]), dtype=np.float64)
    for s in shifts:
        z = logp[:, s, :].astype(np.float64)
        if b_pos is not None:
            z = z - b_pos
        back = np.empty_like(z)
        back[:, perms[s]] = z
        total += back
    total /= len(shifts)
    return total if b_opt is None else total - PRIOR_STRENGTH * b_opt


def softmax(s, T=1.0):
    e = np.exp((s - s.max(-1, keepdims=True)) / T)
    return e / e.sum(-1, keepdims=True)


def nll(s, y, T):
    p = softmax(s, T)
    return float(-np.log(np.clip(p[np.arange(len(y)), y], 1e-12, None)).mean())


def fit_temperature(s, y, lo=0.2, hi=20.0, iters=60):
    """Golden-section on NLL, the same one-parameter fit L1 ships."""
    g = (np.sqrt(5) - 1) / 2
    a, b = lo, hi
    c, d = b - g * (b - a), a + g * (b - a)
    for _ in range(iters):
        if nll(s, y, c) < nll(s, y, d):
            b, d, c = d, c, b - g * (d - a)
        else:
            a, c, d = c, d, a + g * (b - c)
    return float((a + b) / 2)


def ece(P, y, bins=15):
    """Equal-mass binning, the pooled definition bench/run_typed uses."""
    conf, ok = P.max(1), (P.argmax(1) == y).astype(float)
    total = 0.0
    for chunk in np.array_split(np.argsort(conf), bins):
        if len(chunk):
            total += len(chunk) / len(y) * abs(ok[chunk].mean() - conf[chunk].mean())
    return float(total)


def paired_ci(hit, ref_hit, rounds=2000, seed=0):
    """95% CI of the accuracy difference on the same items -- the only way a one-point gap at these
    sample sizes means anything."""
    rng = np.random.default_rng(seed)
    d = hit.astype(float) - ref_hit.astype(float)
    return tuple(float(v) for v in np.quantile(
        d[rng.integers(0, len(d), (rounds, len(d)))].mean(1), [0.025, 0.975]))


# ---------------------------------------------------------------- sequential rotation
def running(logp, perms, order):
    """[N, P, K]: the L0 log-mean over the first P rotations of `order`, for every P.

    Reading rotations one at a time and keeping the running mean is what makes stopping possible:
    the value after P rotations is already a valid L0 readout over a subset."""
    total = np.zeros((logp.shape[0], logp.shape[2]), dtype=np.float64)
    out = np.empty((logp.shape[0], len(order), logp.shape[2]), dtype=np.float64)
    for p, s in enumerate(order):
        z = logp[:, s, :].astype(np.float64)
        back = np.empty_like(z)
        back[:, perms[s]] = z
        total += back
        out[:, p, :] = total / (p + 1)
    return out


def margins(run):
    """Top-1 minus top-2 of the running readout, in log units: how safe the current leader is."""
    part = np.partition(run, -2, axis=-1)
    return part[..., -1] - part[..., -2]


def stop_at(m, tau):
    """First P (0-indexed) whose margin clears tau, else the full budget. One scalar threshold, so
    the rule has exactly one knob and nothing to overfit."""
    ok = m >= tau
    return np.where(ok.any(1), ok.argmax(1), m.shape[1] - 1)


def binom_cdf(k, n, p):
    """P[X <= k] for X ~ Binomial(n, p), summed in log space. numpy plus `math.lgamma`, because CI
    runs on numpy alone."""
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 1.0 if k >= n else 0.0
    ks = np.arange(0, k + 1)
    logc = (lgamma(n + 1) - np.asarray([lgamma(int(i) + 1) for i in ks])
            - np.asarray([lgamma(n - int(i) + 1) for i in ks]))
    terms = logc + ks * np.log(p) + (n - ks) * np.log1p(-p)
    top = terms.max()
    return float(np.exp(top) * np.exp(terms - top).sum())


def cp_upper(k, n, delta=0.05, iters=60):
    """Clopper-Pearson upper confidence bound on a failure rate: the largest p consistent with
    having seen k failures in n draws at confidence 1 - delta.

    A threshold picked on the *point estimate* of the disagreement rate does not hold out -- with 300
    calibration states a 1% target allows three disagreements, and fitting to exactly three overfits.
    Requiring this bound to clear the target is what turns the calibration into a certificate."""
    if k >= n:
        return 1.0
    lo, hi = k / n, 1.0
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if binom_cdf(k, n, mid) > delta:
            lo = mid
        else:
            hi = mid
    return float(hi)


def stop_rule(logp, perms, order, threshold, min_shifts=2, stat="logit",
              require_unanimous=True):
    """Simulate a sequential stopping rule over the rotations, exactly as the runtime would run it.

    `stat` is the statistic the threshold applies to, and the choice matters more than the threshold:

      "prob"   top-1 minus top-2 of the running marginal's *probabilities*. This is what
               `Decider(adaptive_margin=...)` compares today. It saturates at 1, so once the marginal
               is peaked it carries no information -- which is exactly the regime where one wants to
               decide whether to stop.
      "logit"  top-1 minus top-2 of the running log-mean, i.e. the log-odds margin. Unbounded, so it
               keeps separating "decided" from "overwhelmingly decided".

    `require_unanimous` adds the runtime's other condition: every rotation read so far picked the same
    winner on its own.

    Returns (shifts_used, prediction) per item.
    """
    N, S, K = logp.shape
    by_option = np.empty((N, S, K), dtype=np.float64)
    for p, s in enumerate(order):
        z = logp[:, s, :].astype(np.float64)
        back = np.empty_like(z)
        back[:, perms[s]] = z
        by_option[:, p, :] = back
    cum = np.cumsum(by_option, axis=1) / np.arange(1, S + 1)[None, :, None]
    scores = softmax(cum) if stat == "prob" else cum
    part = np.partition(scores, -2, axis=2)
    gap = part[..., -1] - part[..., -2]                       # [N, step] after step+1 rotations
    ok = gap >= threshold
    if require_unanimous:
        winner = by_option.argmax(2)
        same = np.ones((N, S), dtype=bool)
        for p in range(1, S):
            same[:, p] = same[:, p - 1] & (winner[:, p] == winner[:, 0])
        ok = ok & same
    ok[:, :max(0, min_shifts - 1)] = False                    # min_shifts must be read first
    used = np.where(ok.any(1), ok.argmax(1) + 1, S)
    return used, cum[np.arange(N), used - 1].argmax(1)


def sequential(run_cal, m_cal, ref_cal, run_tst, m_tst, ref_tst, y_tst, alphas):
    """Calibrate one threshold per target disagreement rate, then measure it on the test split.

    The target is agreement with the full-K answer, not accuracy, so the calibration needs **no
    labels** -- only the full-K readout on unlabelled states, paid once. That is what makes this a
    certificate a deployment can actually hold: the user asks for "the same decision full L0 would
    have made, 99% of the time", and gets a mean rotation count instead of K."""
    grid = np.quantile(m_cal, np.linspace(0, 1, 201))
    rows = []
    for a in alphas:
        pick = None
        for tau in grid:                                   # ascending: the first that qualifies is
            at = stop_at(m_cal, tau)                       # also the cheapest
            pred = run_cal[np.arange(len(at)), at].argmax(1)
            if float(np.mean(pred != ref_cal)) <= a:
                pick = float(tau)
                break
        if pick is None:
            continue
        at = stop_at(m_tst, pick)
        pred = run_tst[np.arange(len(at)), at].argmax(1)
        used = float((at + 1).mean())
        counts = np.bincount(at + 1, minlength=run_tst.shape[1] + 1)[1:]
        rows.append({"alpha": a, "tau": pick, "mean_forwards": used,
                     "speedup": run_tst.shape[1] / used,
                     "agree": float(np.mean(pred == ref_tst)),
                     "acc": float(np.mean(pred == y_tst)),
                     # how many items stopped after 1, 2, ... K rotations. The shape is the mechanism:
                     # most decisions are settled immediately and a minority genuinely need the full
                     # cycle, which is what makes a per-item budget worth more than a uniform one.
                     "stop_histogram": [int(c) for c in counts]})
    return rows


def replay(path, out_path=""):
    d = np.load(path, allow_pickle=True)
    logp, y, perms = d["logp"], d["y"], d["perms"]
    N, S, K = logp.shape
    model, task = str(d["model"]), str(d["task"])
    n_cal = N // 3
    cal, tst = slice(0, n_cal), slice(n_cal, N)
    yc, yt = y[cal], y[tst]
    print(f"{model} | {task}  K={K}  {N} items -> {n_cal} calibration, {N - n_cal} test\n")

    # ---- the priors, all estimated on the calibration split and none of them using its labels.
    # In position space, averaged over rotations as well as items so that it is a property of the
    # position and not of whichever option happened to sit there.
    b_pos = logp[cal].mean(axis=(0, 1))
    b_pos = b_pos - b_pos.mean()
    b_pos_held = logp[tst].mean(axis=(0, 1))
    b_pos_held = b_pos_held - b_pos_held.mean()
    # In option space from a single rotation: this is the batch prior AnyJev already ships, made
    # K times cheaper to estimate. It carries the position bias of that rotation with it.
    b_opt1 = score(logp[cal], perms, [0]).mean(0)
    b_opt1 = b_opt1 - b_opt1.mean()
    # In option space from the full cycle, where the position bias has already cancelled.
    b_optK = score(logp[cal], perms, range(K)).mean(0)
    b_optK = b_optK - b_optK.mean()

    # ---- part one: what the K rotations buy.
    per_rot = np.asarray([float(np.mean(score(logp[tst], perms, [s]).argmax(1) == yt))
                          for s in range(S)])
    ref_scores = score(logp[tst], perms, range(K))
    ref_pred = ref_scores.argmax(1)
    ref_hit = ref_pred == yt
    ref_acc = float(ref_hit.mean())
    inside = float(np.mean(per_rot <= ref_acc))
    print("what the K rotations buy")
    print(f"  accuracy of each single fixed rotation: min {per_rot.min():.3f}  "
          f"mean {per_rot.mean():.3f}  max {per_rot.max():.3f}  (sd {per_rot.std():.3f})")
    print(f"  accuracy of the full {K}-rotation average:  {ref_acc:.3f}  "
          f"-- above {inside:.0%} of the single rotations")
    print(f"  position bias b_j, log units: spread {b_pos.max() - b_pos.min():.2f}, so position "
          f"{int(b_pos.argmax())} carries {np.exp(b_pos.max() - b_pos.min()):.0f}x the prior weight "
          f"of position {int(b_pos.argmin())}")
    print(f"  b_j is a stable quantity: corr(calibration, held-out) "
          f"{np.corrcoef(b_pos, b_pos_held)[0, 1]:.3f}, "
          f"max |difference| {np.abs(b_pos - b_pos_held).max():.2f} log units\n")

    # ---- part two: the readouts.
    rows = []

    def add(name, fwd, shifts, b_pos_=None, b_opt_=None, alt=None):
        shifts = list(shifts)
        s_t = score(logp[tst], perms, shifts, b_pos_, b_opt_)
        s_c = score(logp[cal], perms, shifts, b_pos_, b_opt_)
        pred = s_t.argmax(1)
        hit = pred == yt
        T = fit_temperature(s_c, yc)
        flip = (float(np.mean(score(logp[tst], perms, alt, b_pos_, b_opt_).argmax(1) != pred))
                if alt is not None else 0.0)
        rows.append({"readout": name, "fwd": fwd, "acc": float(hit.mean()),
                     "ci": paired_ci(hit, ref_hit), "agree": float(np.mean(pred == ref_pred)),
                     "flip": flip, "ece": ece(softmax(s_t), yt),
                     "ece_T": ece(softmax(s_t, T), yt), "T": T})

    half = K // 2
    best = int(np.argmax([np.mean(score(logp[cal], perms, [s]).argmax(1) == yc) for s in range(S)]))
    spread = spread_order(K)
    add("one rotation, as listed", 1, [0], alt=[half])
    add("one rotation + position prior", 1, [0], b_pos, alt=[half])
    add("one rotation + batch prior", 1, [0], None, b_opt1, alt=[half])
    add("one rotation + both priors", 1, [0], b_pos, b_optK, alt=[half])
    add(f"rotation {best}, chosen on calibration", 1, [best],
        alt=[(best + half) % K])
    add("the worst rotation (the lottery's floor)", 1, [int(np.argmin(per_rot))])
    for p in sorted({2, 4, max(2, K // 3)}):
        if 2 * p <= S:
            # adjacent rotations are what max_permutations truncates to today; spread_order is
            # written in anyjev/calibrate/permute.py for exactly this and is not wired in.
            add(f"L0-perm, {p} adjacent rotations (max_permutations)", p, range(p),
                alt=range(p, 2 * p))
            add(f"L0-perm, {p} spread rotations (spread_order)", p, spread[:p],
                alt=spread[p:2 * p])
    add(f"L0-perm, all {K} rotations (reference)", K, range(K))
    add(f"L0-perm, all {K} + batch prior (shipped L0)", K, range(K), None, b_optK)

    head = (f"{'readout':>42}{'fwd':>5}{'acc':>7}{'vs ref':>8}{'95% CI':>18}"
            f"{'agree':>7}{'flip':>7}{'ECE':>7}{'ECE_T':>7}")
    print("readouts, all priors estimated on the calibration split without its labels")
    print(head)
    print("-" * len(head))
    for r in rows:
        ref = r["readout"].endswith("(reference)")
        delta = "" if ref else f"{r['acc'] - ref_acc:+.3f}"
        ci = "" if ref else f"[{r['ci'][0]:+.3f}, {r['ci'][1]:+.3f}]"
        flip = "  --  " if r["flip"] == 0.0 and r["fwd"] >= K else f"{r['flip']:.3f}"
        print(f"{r['readout']:>42}{r['fwd']:>5}{r['acc']:>7.3f}{delta:>8}{ci:>18}"
              f"{r['agree']:>7.3f}{flip:>7}{r['ece']:>7.3f}{r['ece_T']:>7.3f}")
    print(f"\nA row whose CI covers 0 is indistinguishable from the {K}-forward reference on "
          f"accuracy. Whether it can replace it also depends on `agree`, and on the invariance "
          f"argument: a fixed rotation is only order-invariant if the option order is canonicalised "
          f"before the prompt is built.\n")

    # ---- part three: spend rotations per item instead of per question.
    run_c, run_t = running(logp[cal], perms, spread), running(logp[tst], perms, spread)
    m_c, m_t = margins(run_c), margins(run_t)
    ref_cal = score(logp[cal], perms, range(K)).argmax(1)
    seq = sequential(run_c, m_c, ref_cal, run_t, m_t, ref_pred, yt, [0.10, 0.05, 0.02, 0.01])
    print("sequential rotation, spread order, one threshold on the running top-1 margin")
    print("the threshold is calibrated against the full-K answer on unlabelled states, so the "
          "guarantee costs no labels")
    head2 = (f"{'target disagreement':>21}{'margin tau':>12}{'mean fwd':>10}{'speedup':>9}"
             f"{'agree':>8}{'acc':>7}{'uniform-P agree':>17}")
    print(head2)
    print("-" * len(head2))
    for r in seq:
        p_equiv = max(1, min(K, int(round(r["mean_forwards"]))))
        uni = float(np.mean(score(logp[tst], perms, spread[:p_equiv]).argmax(1) == ref_pred))
        r["uniform_equal_budget_agree"] = uni
        print(f"{r['alpha']:>20.0%}{r['tau']:>12.2f}{r['mean_forwards']:>10.2f}"
              f"{r['speedup']:>8.1f}x{r['agree']:>8.3f}{r['acc']:>7.3f}{uni:>17.3f}")
    print("the last column spends the same mean budget uniformly on every item; the gap is what "
          "spending it per item buys")

    result = {"model": model, "task": task, "K": int(K), "n": int(N), "n_calib": int(n_cal),
              "prior_strength": PRIOR_STRENGTH, "ref_acc": ref_acc,
              "per_rotation_acc": per_rot.tolist(), "best_rotation_on_calib": best,
              "spread_order": list(spread),
              "b_pos": b_pos.tolist(), "b_pos_heldout": b_pos_held.tolist(),
              "b_opt_1rot": b_opt1.tolist(), "b_opt_Krot": b_optK.tolist(),
              "b_pos_stability_corr": float(np.corrcoef(b_pos, b_pos_held)[0, 1]),
              "rows": rows, "sequential": seq}
    if out_path:
        with open(out_path, "w") as fh:
            json.dump(result, fh, indent=1)
        print(f"wrote {out_path}")
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--task", default="massive_route")
    ap.add_argument("--n", type=int, default=900)
    ap.add_argument("--dtype", default="bfloat16")
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--dump", default="")
    ap.add_argument("--replay", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)

    if args.replay:
        replay(args.replay, args.out)
        return 0
    if not args.dump:
        ap.error("give --dump to collect, or --replay to analyse")
    collect(args)
    replay(args.dump, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
