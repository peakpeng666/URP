"""Online instance-adaptive selector (Eq. 29).

At deployment, given an unseen instance, return the archive cell whose
affinity centroid is closest in the (normalized and clipped) instance-feature
space. A distance-threshold fallback is applied for out-of-support instances.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.spatial import cKDTree

from qd_lhd.archive import Archive, Cell


@dataclass(slots=True)
class InstanceAdaptiveSelector:
    """Nearest-cell selector over instance-feature centroids.

    Parameters
    ----------
    archive: Archive
        Fully built MAP-Elites archive.
    delta: float
        Distance threshold beyond which the fallback rule triggers.
    """

    archive: Archive
    delta: float = 0.5
    _mins: np.ndarray | None = None
    _maxs: np.ndarray | None = None
    _centroids: np.ndarray | None = None
    _tree: cKDTree | None = None
    _cells: list[Cell] = field(default_factory=list)

    def fit(self, training_features: np.ndarray) -> "InstanceAdaptiveSelector":
        """Fit normalization statistics and build the KD-tree of centroids."""
        if training_features.ndim != 2:
            raise ValueError("training_features must be 2D")
        self._mins = training_features.min(axis=0)
        self._maxs = training_features.max(axis=0)
        span = np.where(self._maxs - self._mins > 1e-12, self._maxs - self._mins, 1.0)
        self._cells = []
        centroids: list[np.ndarray] = []
        for cell in self.archive.occupied_cells():
            centroid_raw = cell.affinity_centroid()
            if centroid_raw is None:
                continue
            centroids.append(np.clip((centroid_raw - self._mins) / span, 0.0, 1.0))
            self._cells.append(cell)
        if not centroids:
            raise RuntimeError("no occupied cells with recorded affinity samples")
        self._centroids = np.stack(centroids)
        self._tree = cKDTree(self._centroids)
        return self

    def select(self, instance_feature: np.ndarray) -> Cell:
        """Return the elite cell for ``instance_feature``."""
        if self._tree is None or self._mins is None or self._maxs is None:
            raise RuntimeError("selector has not been fitted yet")
        span = np.where(self._maxs - self._mins > 1e-12, self._maxs - self._mins, 1.0)
        query = np.clip((instance_feature - self._mins) / span, 0.0, 1.0)
        dist, idx = self._tree.query(query, k=1)
        if dist <= self.delta:
            return self._cells[int(idx)]
        # Fallback: among the 3 nearest occupied cells, pick the one with the
        # lowest weighted scalarization on its recorded samples.
        k = min(3, len(self._cells))
        _, nearest = self._tree.query(query, k=k)
        if np.isscalar(nearest):
            nearest = [int(nearest)]
        best_score = np.inf
        best_cell = self._cells[int(nearest[0])]
        for j in np.atleast_1d(nearest):
            cell = self._cells[int(j)]
            assert cell.objectives is not None
            score = self.archive.scalarize(cell.objectives)
            if score < best_score:
                best_score = score
                best_cell = cell
        return best_cell
