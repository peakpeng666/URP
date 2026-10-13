"""Unit tests for :mod:`qd_lhd.shap_descriptors`."""

from __future__ import annotations

import numpy as np
import pytest

from qd_lhd.shap_descriptors import BehavioralDescriptorBuilder, to_cell_index
from qd_lhd.surrogate import PerformanceSurrogate


def _fit_toy_surrogate(n: int = 200, seed: int = 0) -> tuple[PerformanceSurrogate, np.ndarray]:
    rng = np.random.default_rng(seed)
    features = rng.normal(size=(n, 11)).astype(np.float32)
    targets = (features[:, 0] + 0.5 * features[:, 3] - features[:, 5]).astype(np.float32)
    return PerformanceSurrogate(n_estimators=50).fit(features, targets), features


def test_describe_returns_normalized_descriptors():
    surrogate, features = _fit_toy_surrogate()
    builder = BehavioralDescriptorBuilder(d=3).fit(surrogate, features)
    descriptors = builder.describe(features[:10])
    assert descriptors.shape == (10, 3)
    assert descriptors.min() >= 0.0 - 1e-6
    assert descriptors.max() <= 1.0 + 1e-6


def test_top_features_picks_predictive_axes():
    surrogate, features = _fit_toy_surrogate()
    builder = BehavioralDescriptorBuilder(d=3).fit(surrogate, features)
    top = set(int(i) for i in builder.top_features)
    # Target depends on features 0, 3, 5 — those should appear in the top set
    assert top & {0, 3, 5}


def test_describe_without_fit_raises():
    builder = BehavioralDescriptorBuilder(d=3)
    with pytest.raises(RuntimeError):
        builder.describe(np.zeros((1, 11), dtype=np.float32))


def test_to_cell_index_maps_to_grid():
    idx = to_cell_index(np.array([0.0, 0.5, 1.0]), bins=10)
    assert idx == (0, 5, 9)


def test_to_cell_index_clips_out_of_range():
    idx = to_cell_index(np.array([-0.1, 1.2, 0.3]), bins=10)
    assert idx == (0, 9, 3)
