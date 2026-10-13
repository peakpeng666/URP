"""Which stopping statistic, and which default threshold, `adaptive_shifts` should ship with.

`Decider(adaptive_shifts=True)` stops reading cyclic shifts once every rotation read agrees on the
winner **and** the running marginal's top-1 minus top-2 *probability* clears `adaptive_margin`
(default 0.1, hand-set and never measured). Turning the option on by default means the default has to
carry a stated guarantee, and the only guarantee that costs no labels is **agreement with the full-K
answer** -- our own readout at full strength, not ground truth.

Two things are being chosen here, and the first matters more:

  the statistic   a probability gap saturates at 1, so once the marginal is peaked it stops
                  discriminating -- precisely in the regime where the rule has to decide. The
                  log-odds margin (top-1 minus top-2 of the running log-mean) does not saturate.
  the threshold   picked as the smallest value whose disagreement with the full-K answer stays under
                  the target on *every* cell, so one shipped number is defensible everywhere.

Four rules are compared at a matched guarantee: each statistic, with and without the unanimity
condition. The column that decides is mean shifts at the target.

    python -m bench.layout.margin_default "bench/results_layout/2026-09-27/pp_*.npz"

Research log entry 24.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys

import numpy as np

from anyjev.calibrate.permute import spread_order
from bench.layout.position_prior import cp_upper, stop_rule

GRIDS = {"prob": [round(v, 3) for v in np.concatenate([np.arange(0, 0.9, 0.05),
                                                      np.arange(0.9, 1.0, 0.005)])],
         "logit": [round(v, 2) for v in np.arange(0.0, 14.01, 0.25)]}
RULES = [("prob", True, "probability gap + unanimity (shipped today)"),
         ("prob", False, "probability gap alone"),
         ("logit", True, "log-odds margin + unanimity"),
         ("logit", False, "log-odds margin alone")]


def load(paths):
    out = []
    for path in paths:
        d = np.load(path, allow_pickle=True)
        logp, perms, y = d["logp"], d["perms"], d["y"]
        order = spread_order(logp.shape[2])
        full_used, full_pred = stop_rule(logp, perms, order, threshold=np.inf)
        assert (full_used == logp.shape[1]).all(), "the reference must read every rotation"
        out.append({"path": path, "model": str(d["model"]), "task": str(d["task"]),
                    "logp": logp, "perms": perms, "y": y, "order": order,
                    "K": int(logp.shape[2]), "full_pred": full_pred,
                    "full_acc": float(np.mean(full_pred == y))})
    return out


def sweep(cells, stat, unanimous, min_shifts, target):
    """The smallest threshold in the grid whose worst-cell disagreement clears the target."""
    for thr in GRIDS[stat]:
        rows = []
        for c in cells:
            used, pred = stop_rule(c["logp"], c["perms"], c["order"], thr, min_shifts, stat,
                                   unanimous)
            rows.append({"model": c["model"], "task": c["task"], "K": c["K"],
                         "mean_shifts": float(used.mean()),
                         "disagree": float(np.mean(pred != c["full_pred"])),
                         "acc": float(np.mean(pred == c["y"])), "full_acc": c["full_acc"]})
        if max(r["disagree"] for r in rows) <= target:
            return {"threshold": thr, "rows": rows}
    return None


def per_cell(cell, stat, unanimous, min_shifts, target, frac=1 / 3):
    """Calibrate the threshold on the first `frac` of items against *their own* full-K answers, then
    measure on the rest. No labels anywhere: the reference is our own full-strength readout.

    This is the shipped path -- `Decider.calibrate_adaptive()` does exactly this on whatever
    unlabelled states a deployment has -- so it is the fair way to compare the statistics."""
    n = cell["logp"].shape[0]
    cut = int(n * frac)
    cal, tst = slice(0, cut), slice(cut, n)
    pick = None
    for thr in GRIDS[stat]:
        used, pred = stop_rule(cell["logp"][cal], cell["perms"], cell["order"], thr, min_shifts,
                               stat, unanimous)
        k = int(np.sum(pred != cell["full_pred"][cal]))
        if cp_upper(k, cut) <= target:          # a 95% upper bound, not the point estimate
            pick = thr
            break
    if pick is None:
        return None
    used, pred = stop_rule(cell["logp"][tst], cell["perms"], cell["order"], pick, min_shifts, stat,
                           unanimous)
    return {"model": cell["model"], "task": cell["task"], "K": cell["K"], "threshold": pick,
            "mean_shifts": float(used.mean()), "vs_K": cell["K"] / float(used.mean()),
            "disagree": float(np.mean(pred != cell["full_pred"][tst])),
            "acc": float(np.mean(pred == cell["y"][tst])),
            "full_acc": float(np.mean(cell["full_pred"][tst] == cell["y"][tst]))}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("npz", nargs="+")
    ap.add_argument("--min-shifts", type=int, default=2)
    ap.add_argument("--target", type=float, default=0.01)
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)

    cells = load(sorted({p for pat in args.npz for p in glob.glob(pat)}))
    print(f"{len(cells)} cells, {cells[0]['logp'].shape[0]} items each, "
          f"min_shifts={args.min_shifts}, target disagreement {args.target:.0%}\n")

    results = {}
    head = (f"{'rule':>42}{'threshold':>11}{'mean shifts: worst / mean':>27}"
            f"{'worst disagree':>16}")
    print(head)
    print("-" * len(head))
    for stat, unanimous, label in RULES:
        got = sweep(cells, stat, unanimous, args.min_shifts, args.target)
        results[label] = got
        if got is None:
            print(f"{label:>42}{'--':>11}{'never clears the target':>27}{'':>16}")
            continue
        shifts = [r["mean_shifts"] for r in got["rows"]]
        print(f"{label:>42}{got['threshold']:>11.3f}"
              f"{max(shifts):>14.2f} / {np.mean(shifts):>8.2f}"
              f"{max(r['disagree'] for r in got['rows']):>16.3f}")

    best = min((k for k, v in results.items() if v),
               key=lambda k: max(r["mean_shifts"] for r in results[k]["rows"]), default=None)
    print(f"\ncheapest rule at a {args.target:.0%} guarantee: {best}")
    if best:
        print(f"{'':>4}{'model':>26}{'task':>15}{'K':>4}{'mean shifts':>13}{'vs K':>8}"
              f"{'disagree':>10}{'accuracy':>10}{'full-K':>9}")
        for r in results[best]["rows"]:
            print(f"{'':>4}{r['model'].split('/')[-1]:>26}{r['task']:>15}{r['K']:>4}"
                  f"{r['mean_shifts']:>13.2f}{r['K'] / r['mean_shifts']:>7.1f}x"
                  f"{r['disagree']:>10.3f}{r['acc']:>10.3f}{r['full_acc']:>9.3f}")

    # the same four rules, but with the threshold calibrated per cell -- the shipped path
    print(f"\nthreshold calibrated per (model, task) on a third of the items, measured on the rest "
          f"(target {args.target:.0%})")
    head2 = (f"{'rule':>42}{'mean shifts: worst / mean':>27}{'vs K: worst / mean':>21}"
             f"{'worst disagree':>16}")
    print(head2)
    print("-" * len(head2))
    per = {}
    for stat, unanimous, label in RULES:
        got = [per_cell(c, stat, unanimous, args.min_shifts, args.target) for c in cells]
        got = [g for g in got if g]
        per[label] = got
        if not got:
            print(f"{label:>42}{'never clears the target':>27}")
            continue
        sh = [g["mean_shifts"] for g in got]
        vs = [g["vs_K"] for g in got]
        print(f"{label:>42}{max(sh):>14.2f} / {np.mean(sh):>8.2f}"
              f"{min(vs):>10.1f}x / {np.mean(vs):>6.1f}x"
              f"{max(g['disagree'] for g in got):>16.3f}")
    complete = {k: v for k, v in per.items() if len(v) == len(cells)}
    best_per = min(complete, key=lambda k: np.mean([g["mean_shifts"] for g in complete[k]]),
                   default=None)
    for k, v in per.items():
        if len(v) < len(cells):
            print(f"  ({k}: cleared only {len(v)} of {len(cells)} cells, so not a candidate)")
    print(f"\ncheapest under per-question calibration: {best_per}")
    if best_per:
        print(f"{'':>4}{'model':>26}{'task':>15}{'K':>4}{'threshold':>11}{'mean shifts':>13}"
              f"{'vs K':>8}{'disagree':>10}{'accuracy':>10}{'full-K':>9}")
        for g in per[best_per]:
            print(f"{'':>4}{g['model'].split('/')[-1]:>26}{g['task']:>15}{g['K']:>4}"
                  f"{g['threshold']:>11.3f}{g['mean_shifts']:>13.2f}{g['vs_K']:>7.1f}x"
                  f"{g['disagree']:>10.3f}{g['acc']:>10.3f}{g['full_acc']:>9.3f}")

    rows01 = []
    for c in cells:
        used, pred = stop_rule(c["logp"], c["perms"], c["order"], 0.1, args.min_shifts, "prob", True)
        rows01.append((float(used.mean()), float(np.mean(pred != c["full_pred"]))))
    print(f"\nfor reference, today's default (probability gap 0.1 + unanimity): "
          f"mean shifts {max(r[0] for r in rows01):.2f} worst, "
          f"disagreement {max(r[1] for r in rows01):.3f} worst -- "
          f"a real operating point, just not a measured one")

    if args.out:
        with open(args.out, "w") as fh:
            json.dump({"min_shifts": args.min_shifts, "target": args.target, "cheapest": best,
                       "rules_global_threshold": {
                           k: (v and {"threshold": v["threshold"], "rows": v["rows"]})
                           for k, v in results.items()},
                       "cheapest_per_question": best_per,
                       "rules_per_question": per,
                       "shipped_default_0.1": [{"mean_shifts": a, "disagree": b}
                                               for a, b in rows01]}, fh, indent=1)
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
