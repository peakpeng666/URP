"""Trusted handwritten transcription of the fixed published EoH formula.

This is reimplementation rescoring, not execution of downloaded author bytes.
Source SHA256 f3d50f0e81ca061a0377b9fb61b75cf16ecde9f091876db0d8baca8323655995.
The original MIT notice is retained in ../LICENSE.source. No source is accepted.
"""
import numpy as np


def score_trace(item, bins):
    """Fixed domain only: np.int32 item1..100; int64 feasible bins1..500."""
    if type(item) is not np.int32 or not 1 <= int(item) <= 100:
        raise ValueError('item must be np.int32 in1..100')
    if type(bins) is not np.ndarray or bins.dtype != np.dtype('int64') or bins.ndim != 1:
        raise ValueError('bins must be one-dimensional int64 ndarray')
    if not 1 <= bins.size <= 10000 or np.any(bins < item) or np.any(bins > 500):
        raise ValueError('nonempty feasible bin domain/size')
    # Original source lines4..10, same operation order and NumPy dtypes.
    diff = bins - item
    exp = np.exp(diff)
    sqrt = np.sqrt(diff)
    ulti = 1 - diff / bins
    comb = ulti * sqrt
    adjust = np.where(diff > (item * 3), comb + 0.8, comb + 0.3)
    # Original line11 split once to expose its existing intermediate, not recompute it.
    denominator = (exp + 0.7) * exp
    hybrid_exp = bins / denominator
    # Original line13. No algebraic simplification, clipping or exact-fit shortcut.
    scores = hybrid_exp + adjust
    if scores.dtype != np.dtype('float64') or not np.all(np.isfinite(scores)):
        raise ArithmeticError('nonfinite or non-binary64 final score')
    return {'diff': diff, 'exp': exp, 'sqrt': sqrt, 'ulti': ulti,
            'comb': comb, 'adjust': adjust, 'denominator': denominator,
            'hybrid_exp': hybrid_exp, 'scores': scores}


def score(item, bins):
    return score_trace(item, bins)['scores']
