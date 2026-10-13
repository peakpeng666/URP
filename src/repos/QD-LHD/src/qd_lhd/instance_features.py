"""Six-dimensional instance feature extractor used by the online selector.

Implements the per-problem feature formulas of Section III-E of the manuscript:
problem size, constraint density, demand/weight variability, cost-matrix mean,
cost-matrix CV, and K-nearest-neighbor graph clustering coefficient.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np


@dataclass(frozen=True, slots=True)
class CVRPInstance:
    coords: np.ndarray  # (n, 2)
    demands: np.ndarray  # (n,)
    capacity: float
    num_vehicles: int


@dataclass(frozen=True, slots=True)
class TSPInstance:
    coords: np.ndarray  # (n, 2)


@dataclass(frozen=True, slots=True)
class JSSPInstance:
    processing: np.ndarray  # (n_jobs, n_machines)


Instance = CVRPInstance | TSPInstance | JSSPInstance


def _pairwise_euclidean(coords: np.ndarray) -> np.ndarray:
    diff = coords[:, None, :] - coords[None, :, :]
    return np.sqrt((diff**2).sum(axis=-1))


def _knn_clustering(coords: np.ndarray, k: int) -> float:
    n = coords.shape[0]
    if n <= k + 1:
        return 0.0
    dist = _pairwise_euclidean(coords)
    np.fill_diagonal(dist, np.inf)
    neighbors = np.argsort(dist, axis=1)[:, :k]
    g = nx.Graph()
    g.add_nodes_from(range(n))
    for i in range(n):
        for j in neighbors[i]:
            g.add_edge(i, int(j))
    return float(nx.average_clustering(g))


def _cv(values: np.ndarray) -> float:
    mean = float(values.mean())
    if mean == 0.0:
        return 0.0
    return float(values.std() / mean)


def extract_instance_features(instance: Instance, k: int = 5) -> np.ndarray:
    """Return the six-dimensional raw instance feature vector.

    The features are (size, density, demand/weight CV, cost mean, cost CV,
    clustering). The caller is responsible for downstream normalization.
    """
    if isinstance(instance, CVRPInstance):
        return _cvrp_features(instance, k)
    if isinstance(instance, TSPInstance):
        return _tsp_features(instance, k)
    if isinstance(instance, JSSPInstance):
        return _jssp_features(instance)
    raise TypeError(f"unsupported instance type: {type(instance).__name__}")


def _cvrp_features(inst: CVRPInstance, k: int) -> np.ndarray:
    n = inst.coords.shape[0]
    density = float(inst.demands.sum() / (inst.num_vehicles * inst.capacity))
    cv_demand = _cv(inst.demands)
    dist = _pairwise_euclidean(inst.coords)
    upper = dist[np.triu_indices_from(dist, k=1)]
    cost_mean = float(upper.mean())
    cost_cv = _cv(upper)
    cluster = _knn_clustering(inst.coords, k)
    return np.array([n, density, cv_demand, cost_mean, cost_cv, cluster], dtype=np.float32)


def _tsp_features(inst: TSPInstance, k: int) -> np.ndarray:
    n = inst.coords.shape[0]
    density = 1.0
    cv_demand = 0.0
    dist = _pairwise_euclidean(inst.coords)
    upper = dist[np.triu_indices_from(dist, k=1)]
    cost_mean = float(upper.mean())
    cost_cv = _cv(upper)
    cluster = _knn_clustering(inst.coords, k)
    return np.array([n, density, cv_demand, cost_mean, cost_cv, cluster], dtype=np.float32)


def _jssp_features(inst: JSSPInstance) -> np.ndarray:
    n_jobs, n_machines = inst.processing.shape
    size = n_jobs * n_machines
    total = float(inst.processing.sum())
    lb = float(np.max(inst.processing.sum(axis=1)))  # lower bound: longest total job
    density = total / (n_machines * lb) if lb > 0 else 0.0
    flat = inst.processing.flatten()
    cv_proc = _cv(flat)
    cost_mean = float(flat.mean())
    cost_cv = _cv(flat)
    # Clustering on job-machine bipartite projection over non-zero processing
    adj = (inst.processing > 0).astype(int)
    jm = adj @ adj.T  # (n_jobs, n_jobs) co-machine count
    np.fill_diagonal(jm, 0)
    g = nx.from_numpy_array(jm)
    cluster = float(nx.average_clustering(g)) if g.number_of_edges() > 0 else 0.0
    return np.array([size, density, cv_proc, cost_mean, cost_cv, cluster], dtype=np.float32)
