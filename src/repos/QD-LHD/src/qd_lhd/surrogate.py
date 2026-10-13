"""XGBoost surrogate performance model.

Maps an AST feature vector phi(h) in R^p to a scalar prediction of the
quality objective f_qual. Retrained every Delta generations on all
accumulated (phi(h_i), f_qual(h_i, I)) pairs.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from xgboost import XGBRegressor


@dataclass(slots=True)
class PerformanceSurrogate:
    """Gradient-boosted tree surrogate over AST features.

    Parameters
    ----------
    n_estimators: int
        Number of boosting rounds (default 200, matching the manuscript).
    max_depth: int
        Max tree depth (default 6).
    learning_rate: float
        Shrinkage (default 0.1).
    random_state: int
        Reproducibility seed.
    """

    n_estimators: int = 200
    max_depth: int = 6
    learning_rate: float = 0.1
    random_state: int = 0
    _model: XGBRegressor | None = None
    _fitted: bool = False

    def fit(self, features: np.ndarray, targets: np.ndarray) -> "PerformanceSurrogate":
        """Fit on ``(N, p)`` feature matrix and ``(N,)`` target vector."""
        if features.ndim != 2:
            raise ValueError(f"features must be 2D, got shape {features.shape}")
        if targets.ndim != 1 or targets.shape[0] != features.shape[0]:
            raise ValueError("targets must be 1D with length matching features")
        self._model = XGBRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            random_state=self.random_state,
            tree_method="hist",
            verbosity=0,
        )
        self._model.fit(features, targets)
        self._fitted = True
        return self

    def predict(self, features: np.ndarray) -> np.ndarray:
        """Return predicted f_qual for each row of ``features``."""
        if not self._fitted or self._model is None:
            raise RuntimeError("surrogate has not been fitted yet")
        if features.ndim == 1:
            features = features[None, :]
        return self._model.predict(features)

    @property
    def fitted(self) -> bool:
        return self._fitted

    @property
    def model(self) -> XGBRegressor:
        """Access the underlying XGBRegressor (e.g. for Tree-SHAP)."""
        if self._model is None:
            raise RuntimeError("surrogate has not been fitted yet")
        return self._model
