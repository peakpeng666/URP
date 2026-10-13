"""Unit tests for :mod:`qd_lhd.archive`."""

from __future__ import annotations

import numpy as np
import pytest

from qd_lhd.archive import Archive


def _phi(dim: int = 11) -> np.ndarray:
    return np.zeros(dim, dtype=np.float32)


def test_insert_into_empty_cell_is_accepted():
    archive = Archive(d=2, bins=5)
    assert archive.insert((0, 0), "src", _phi(), np.array([0.5, 0.5, 0.5]))
    assert archive.coverage == 1 / 25


def test_dominating_offspring_replaces_incumbent():
    archive = Archive(d=2, bins=5)
    archive.insert((0, 0), "parent", _phi(), np.array([0.5, 0.5, 0.5]))
    assert archive.insert((0, 0), "better", _phi(), np.array([0.4, 0.4, 0.4]))
    cell = archive._cells[(0, 0)]
    assert cell.source == "better"


def test_dominated_offspring_is_rejected():
    archive = Archive(d=2, bins=5)
    archive.insert((0, 0), "parent", _phi(), np.array([0.4, 0.4, 0.4]))
    assert not archive.insert((0, 0), "worse", _phi(), np.array([0.5, 0.5, 0.5]))
    assert archive._cells[(0, 0)].source == "parent"


def test_non_dominated_uses_scalarization():
    archive = Archive(d=2, bins=5, weights=(0.6, 0.2, 0.2))
    archive.insert((0, 0), "parent", _phi(), np.array([0.5, 0.1, 0.1]))
    # parent scalar score = 0.6*0.5 + 0.2*0.1 + 0.2*0.1 = 0.34
    # tradeoff scalar score = 0.6*0.4 + 0.2*0.6 + 0.2*0.1 = 0.38
    # Neither dominates the other (tradeoff better on quality, worse on time).
    # Parent has lower score so tradeoff should lose.
    assert archive.insert((0, 0), "tradeoff", _phi(), np.array([0.4, 0.6, 0.1])) is False
    assert archive._cells[(0, 0)].source == "parent"

    # Flip the weights so tradeoff wins: heavy weight on quality.
    archive2 = Archive(d=2, bins=5, weights=(0.95, 0.025, 0.025))
    archive2.insert((0, 0), "parent", _phi(), np.array([0.5, 0.1, 0.1]))
    # parent score = 0.95*0.5 + 0.025*0.1 + 0.025*0.1 = 0.480
    # tradeoff score = 0.95*0.4 + 0.025*0.6 + 0.025*0.1 = 0.3975
    assert archive2.insert((0, 0), "tradeoff", _phi(), np.array([0.4, 0.6, 0.1])) is True
    assert archive2._cells[(0, 0)].source == "tradeoff"


def test_qd_score_sums_over_occupied_cells():
    archive = Archive(d=1, bins=3)
    archive.insert((0,), "a", _phi(), np.array([0.3, 0, 0]))
    archive.insert((1,), "b", _phi(), np.array([0.7, 0, 0]))
    # Expected QD = (1-0.3) + (1-0.7) = 1.0
    assert archive.qd_score() == pytest.approx(1.0)


def test_record_affinity_requires_occupied_cell():
    archive = Archive(d=1, bins=3)
    with pytest.raises(KeyError):
        archive.record_affinity((0,), np.array([0.5]))
