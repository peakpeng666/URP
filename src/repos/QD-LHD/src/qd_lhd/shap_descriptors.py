"""SHAP-derived behavioral descriptor construction.

Implements the descriptor mechanism of Section III-B of the manuscript:

    1. Tree-SHAP attributes the surrogate's prediction to each AST feature.
    2. The d features with the largest mean |SHAP| across the archive are selected
       as behavioral dimensions.
    3. Each heuristic's descriptor b(h) is the min-max normalized slice of its
       SHAP attribution vector over those d features.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import shap

from qd_lhd.surrogate import PerformanceSurrogate


@dataclass(slots=True)
class BehavioralDescriptorBuilder:
    """SHAP-based behavioral descriptor construction.

    Parameters
    ----------
    d: int
        Number of behavioral dimensions (default 3).
    """

    d: int = 3
    _top_features: np.ndarray | None = None
    _mins: np.ndarray | None = None
    _maxs: np.ndarray | None = None
    _explainer: shap.TreeExplainer | None = None

    def fit(self, surrogate: PerformanceSurrogate, features: np.ndarray) -> "BehavioralDescriptorBuilder":
        """Compute top-d AST features and store normalization statistics.

        Parameters
        ----------
        surrogate: PerformanceSurrogate
            Fitted surrogate model.
        features: numpy.ndarray, shape (N, p)
            AST feature matrix of currently-evaluated heuristics.
        """
        if features.ndim != 2:
            raise ValueError(f"features must be 2D, got shape {features.shape}")
        if features.shape[0] == 0:
            raise ValueError("features matrix is empty")

        self._explainer = shap.TreeExplainer(surrogate.model)
        shap_values = self._explainer.shap_values(features)  # (N, p)
        mean_abs = np.abs(shap_values).mean(axis=0)
        self._top_features = np.argsort(-mean_abs)[: self.d]
        selected = shap_values[:, self._top_features]
        self._mins = selected.min(axis=0)
        self._maxs = selected.max(axis=0)
        return self

    def describe(self, features: np.ndarray) -> np.ndarray:
        """Return the ``(M, d)`` descriptor matrix for ``features``.

        Descriptor coordinates are min-max normalized to ``[0, 1]`` using the
        statistics recorded at the last ``fit``; coordinates are clipped to the
        training support at test time.
        """
        if self._explainer is None or self._top_features is None:
            raise RuntimeError("builder has not been fitted yet")
        if features.ndim == 1:
            features = features[None, :]
        shap_values = self._explainer.shap_values(features)[:, self._top_features]
        span = np.where(self._maxs - self._mins > 1e-12, self._maxs - self._mins, 1.0)
        normalized = (shap_values - self._mins) / span
        return np.clip(normalized, 0.0, 1.0)

    @property
    def top_features(self) -> np.ndarray:
        if self._top_features is None:
            raise RuntimeError("builder has not been fitted yet")
        return self._top_features.copy()


def to_cell_index(descriptor: np.ndarray, bins: int) -> tuple[int, ...]:
    """Map a descriptor vector to its grid cell index.

    Each coordinate is partitioned into ``bins`` equal-width bins on ``[0, 1]``.
    """
    if descriptor.ndim != 1:
        raise ValueError(f"descriptor must be 1D, got shape {descriptor.shape}")
    idx = np.floor(descriptor * bins).astype(int)
    return tuple(np.clip(idx, 0, bins - 1).tolist())
