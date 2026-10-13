"""MAP-Elites archive with multi-objective cell competition.

Implements Definition 2 (archive), Definition 3 (Pareto dominance), and the
two-stage competition rule of Section III-D of the manuscript.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(slots=True)
class Cell:
    """A single archive cell, storing the elite heuristic if occupied."""

    index: tuple[int, ...]
    source: str = ""
    features: np.ndarray | None = None  # AST features phi(h)
    objectives: np.ndarray | None = None  # (f_qual, f_time, f_rob)
    affinity_samples: list[np.ndarray] = field(default_factory=list)

    @property
    def occupied(self) -> bool:
        return self.source != ""

    def affinity_centroid(self) -> np.ndarray | None:
        if not self.affinity_samples:
            return None
        return np.mean(np.stack(self.affinity_samples), axis=0)


def _dominates(a: np.ndarray, b: np.ndarray) -> bool:
    """Pareto dominance on minimization objectives."""
    return bool(np.all(a <= b) and np.any(a < b))


@dataclass(slots=True)
class Archive:
    """MAP-Elites archive over a uniform grid in ``[0, 1]^d``.

    Parameters
    ----------
    d: int
        Number of behavioral dimensions.
    bins: int
        Number of bins per dimension; ``K = bins^d`` cells in total.
    weights: tuple[float, float, float]
        Scalarization weights ``(w1, w2, w3)`` for stage-2 cell competition.
    """

    d: int
    bins: int
    weights: tuple[float, float, float] = (0.6, 0.2, 0.2)
    _cells: dict[tuple[int, ...], Cell] = field(default_factory=dict)

    @property
    def num_cells(self) -> int:
        return self.bins**self.d

    @property
    def coverage(self) -> float:
        """Fraction of occupied cells."""
        return len(self._cells) / self.num_cells

    def occupied_cells(self) -> list[Cell]:
        return [c for c in self._cells.values() if c.occupied]

    def scalarize(self, objectives: np.ndarray) -> float:
        w = np.asarray(self.weights, dtype=float)
        return float(np.dot(w, objectives))

    def insert(
        self,
        cell_index: tuple[int, ...],
        source: str,
        features: np.ndarray,
        objectives: np.ndarray,
    ) -> bool:
        """Propose a candidate for ``cell_index``; return ``True`` if it wins.

        The two-stage rule (Section III-D) is applied:
            1. If the cell is empty, the candidate is inserted unconditionally.
            2. Else, Pareto dominance is checked; the dominator wins.
            3. Else, the candidate with the lower weighted scalarization wins.
        """
        if len(cell_index) != self.d:
            raise ValueError(f"cell_index must have length {self.d}, got {len(cell_index)}")
        if objectives.shape != (3,):
            raise ValueError(f"objectives must be shape (3,), got {objectives.shape}")

        cell = self._cells.get(cell_index)
        if cell is None or not cell.occupied:
            self._cells[cell_index] = Cell(
                index=cell_index,
                source=source,
                features=features,
                objectives=objectives,
            )
            return True

        incumbent = cell.objectives
        assert incumbent is not None  # for mypy

        if _dominates(objectives, incumbent):
            cell.source = source
            cell.features = features
            cell.objectives = objectives
            return True
        if _dominates(incumbent, objectives):
            return False
        if self.scalarize(objectives) < self.scalarize(incumbent):
            cell.source = source
            cell.features = features
            cell.objectives = objectives
            return True
        return False

    def qd_score(self) -> float:
        """Sum over occupied cells of ``max(0, 1 - f_qual)`` (Eq. 4)."""
        total = 0.0
        for cell in self.occupied_cells():
            assert cell.objectives is not None
            f_qual = float(cell.objectives[0])
            total += max(0.0, 1.0 - f_qual)
        return total

    def record_affinity(self, cell_index: tuple[int, ...], instance_feature: np.ndarray) -> None:
        """Attach an instance-feature sample to the occupied cell's affinity list."""
        cell = self._cells.get(cell_index)
        if cell is None or not cell.occupied:
            raise KeyError(f"cell {cell_index} is not occupied")
        cell.affinity_samples.append(instance_feature.copy())
