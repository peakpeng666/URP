"""Fixed numerical EoH control; no source inputs, model calls or dynamic execution.

Preparation only: this module deliberately has no benchmark command-line entry.
MIT source attribution: ../published_eoh_formula_v1/LICENSE.source.
"""
from fractions import Fraction
from itertools import product
import numpy as np

ORIGINAL = (3, 0.8, 0.7)
GRID = tuple(product((2, 3, 4), (0.6, 0.8, 1.0), (0.4, 0.7, 1.0)))
# Original first, then lexicographic: deterministic tie preference without tuning.
ORDER = (ORIGINAL,) + tuple(p for p in GRID if p != ORIGINAL)


def score(item, bins, params=ORIGINAL):
    if params not in GRID:
        raise ValueError('parameters outside preregistered grid')
    if type(item) is not np.int64 or not 1 <= int(item) <= 100:
        raise ValueError('original unscaled int64 item in 1..100 required')
    if type(bins) is not np.ndarray or bins.dtype != np.dtype('int64') or bins.ndim != 1:
        raise ValueError('one-dimensional int64 bins required')
    if not 1 <= bins.size <= 10000 or np.any(bins < item) or np.any(bins > 500):
        raise ValueError('feasible residuals in item..500 required')
    threshold, large_add, exp_offset = params
    diff = bins - item
    exp = np.exp(diff)
    sqrt = np.sqrt(diff)
    ulti = 1 - diff / bins
    comb = ulti * sqrt
    adjust = np.where(diff > (item * threshold), comb + large_add, comb + 0.3)
    denominator = (exp + exp_offset) * exp
    hybrid_exp = bins / denominator
    scores = hybrid_exp + adjust
    if scores.dtype != np.dtype('float64') or not np.all(np.isfinite(scores)):
        raise ArithmeticError('nonfinite or non-binary64 final score')
    return scores


def pack(items, capacity, params=ORIGINAL):
    if capacity not in (100, 500) or type(capacity) is not int:
        raise ValueError('fixed capacities only')
    if type(items) is not list or not 1 <= len(items) <= 10000:
        raise ValueError('nonempty fixed-domain list required')
    if any(type(i) is not int or not 1 <= i <= 100 for i in items):
        raise ValueError('unscaled integer items required')
    residuals = np.full(len(items), capacity, dtype=np.int64)
    assignment = []
    for item in np.asarray(items, dtype=np.int64):
        ids = np.flatnonzero(residuals - item >= 0)
        chosen = int(ids[int(np.argmax(score(item, residuals[ids], params)))])
        residuals[chosen] -= item
        assignment.append(chosen)
    return {'used_bins': int(np.count_nonzero(residuals != capacity)),
            'assignment': assignment, 'residuals': residuals.tolist()}


def fitness(bounds, bins):
    if len(bounds) != 5 or len(bins) != 5:
        raise ValueError('exactly five design rows required')
    if any(type(a) is not int or type(b) is not int or not 0 < a <= b
           for a, b in zip(bounds, bins)):
        raise ValueError('positive integer valid L1/bin pairs required')
    return sum((Fraction(a, b) for a, b in zip(bounds, bins)), Fraction()) / 5


def select_winner(bounds, results):
    """All 27 complete candidates; exact rational primary score, fixed-order tie."""
    if set(results) != set(GRID):
        raise ValueError('incomplete grid cannot select a winner')
    scores = {p: fitness(bounds, results[p]) for p in ORDER}
    return max(ORDER, key=scores.__getitem__)
