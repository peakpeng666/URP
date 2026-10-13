"""Unit tests for :mod:`qd_lhd.surrogate`."""

from __future__ import annotations

import numpy as np
import pytest

from qd_lhd.surrogate import PerformanceSurrogate


def _toy_dataset(n: int = 200, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    features = rng.normal(size=(n, 11)).astype(np.float32)
    # Target depends on a simple non-linear combination
    targets = (features[:, 0] ** 2 + 0.5 * features[:, 1] - features[:, 3]).astype(np.float32)
    return features, targets


def test_predict_without_fit_raises():
    model = PerformanceSurrogate()
    with pytest.raises(RuntimeError):
        model.predict(np.zeros((1, 11), dtype=np.float32))


def test_fit_and_predict_recovers_signal():
    features, targets = _toy_dataset()
    model = PerformanceSurrogate(n_estimators=50).fit(features, targets)
    preds = model.predict(features[:20])
    assert preds.shape == (20,)
    # Correlation should be positive on training data
    corr = np.corrcoef(preds, targets[:20])[0, 1]
    assert corr > 0.5


def test_fit_rejects_shape_mismatch():
    model = PerformanceSurrogate()
    with pytest.raises(ValueError):
        model.fit(np.zeros((10, 11)), np.zeros(5))
    with pytest.raises(ValueError):
        model.fit(np.zeros(10), np.zeros(10))
