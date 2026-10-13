"""Unit tests for :mod:`qd_lhd.selector`."""

from __future__ import annotations

import numpy as np
import pytest

from qd_lhd.archive import Archive
from qd_lhd.selector import InstanceAdaptiveSelector


def _build_two_cell_archive() -> Archive:
    archive = Archive(d=2, bins=5)
    archive.insert((0, 0), "heur_A", np.zeros(11, dtype=np.float32), np.array([0.3, 0.1, 0.05]))
    archive.insert((4, 4), "heur_B", np.zeros(11, dtype=np.float32), np.array([0.4, 0.2, 0.10]))
    archive.record_affinity((0, 0), np.array([10.0, 0.2, 0.1, 1.0, 0.1, 0.05]))
    archive.record_affinity((4, 4), np.array([100.0, 0.8, 0.5, 5.0, 0.4, 0.30]))
    return archive


def test_select_returns_nearest_cell():
    archive = _build_two_cell_archive()
    selector = InstanceAdaptiveSelector(archive=archive).fit(
        training_features=np.array(
            [[10.0, 0.2, 0.1, 1.0, 0.1, 0.05], [100.0, 0.8, 0.5, 5.0, 0.4, 0.30]]
        )
    )
    cell = selector.select(np.array([12.0, 0.25, 0.15, 1.2, 0.12, 0.06]))
    assert cell.source == "heur_A"
    cell = selector.select(np.array([90.0, 0.75, 0.45, 4.8, 0.38, 0.28]))
    assert cell.source == "heur_B"


def test_fit_requires_affinity_samples():
    archive = Archive(d=2, bins=5)
    archive.insert((0, 0), "heur_A", np.zeros(11, dtype=np.float32), np.array([0.3, 0.1, 0.05]))
    selector = InstanceAdaptiveSelector(archive=archive)
    with pytest.raises(RuntimeError):
        selector.fit(training_features=np.array([[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]]))


def test_select_before_fit_raises():
    archive = _build_two_cell_archive()
    selector = InstanceAdaptiveSelector(archive=archive)
    with pytest.raises(RuntimeError):
        selector.select(np.zeros(6))
