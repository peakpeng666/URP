"""Unit tests for :mod:`qd_lhd.instance_features`."""

from __future__ import annotations

import numpy as np
import pytest

from qd_lhd.instance_features import (
    CVRPInstance,
    JSSPInstance,
    TSPInstance,
    extract_instance_features,
)


def test_cvrp_density_matches_formula():
    rng = np.random.default_rng(42)
    coords = rng.uniform(0, 1, size=(20, 2))
    demands = rng.uniform(1, 10, size=20)
    inst = CVRPInstance(coords=coords, demands=demands, capacity=20.0, num_vehicles=5)
    feats = extract_instance_features(inst)
    assert feats.shape == (6,)
    expected_density = float(demands.sum() / (5 * 20.0))
    assert feats[1] == pytest.approx(expected_density, rel=1e-5)
    assert feats[0] == 20  # size


def test_tsp_sets_density_to_one_and_demand_cv_to_zero():
    rng = np.random.default_rng(0)
    coords = rng.uniform(0, 1, size=(15, 2))
    feats = extract_instance_features(TSPInstance(coords=coords))
    assert feats[1] == 1.0
    assert feats[2] == 0.0


def test_jssp_size_is_jobs_times_machines():
    processing = np.array([[3, 2, 5], [1, 4, 6], [7, 3, 2]], dtype=float)
    inst = JSSPInstance(processing=processing)
    feats = extract_instance_features(inst)
    assert feats[0] == 9  # 3 jobs * 3 machines
    assert feats[2] > 0  # CV over processing times should be positive


def test_unsupported_instance_type_raises():
    with pytest.raises(TypeError):
        extract_instance_features("not an instance")  # type: ignore[arg-type]
