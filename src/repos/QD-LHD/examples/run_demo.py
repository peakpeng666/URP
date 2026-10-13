"""Minimal end-to-end demo of the QD-LHD pipeline.

Runs a short 20-generation evolution on synthetic CVRP instances using a mock
LLM (so no API key is needed), prints archive coverage and QD-score, and
demonstrates the online selector on a held-out instance.

Usage
-----
    python examples/run_demo.py
"""

from __future__ import annotations

import itertools

import numpy as np

from qd_lhd.archive import Archive
from qd_lhd.ast_features import extract_ast_features
from qd_lhd.evolution import QDLHDConfig, run_qdlhd
from qd_lhd.instance_features import CVRPInstance, extract_instance_features
from qd_lhd.llm_client import CallableLLMClient
from qd_lhd.selector import InstanceAdaptiveSelector


_HEURISTIC_TEMPLATES = [
    "def heuristic(inst):\n    nodes = sorted(range(len(inst.demands)))\n    return [[0] + nodes]\n",
    "def heuristic(inst):\n    route, cap = [0], inst.capacity\n    for i in range(1, len(inst.demands)):\n        if inst.demands[i] <= cap:\n            route.append(i); cap -= inst.demands[i]\n    return [route]\n",
    "def heuristic(inst):\n    def rec(i, cap, acc):\n        if i >= len(inst.demands):\n            return [acc]\n        return rec(i + 1, cap - inst.demands[i], acc + [i])\n    return rec(1, inst.capacity, [0])\n",
    "def heuristic(inst):\n    groups = {i: inst.demands[i] for i in range(len(inst.demands))}\n    return [sorted(groups, key=groups.get)]\n",
    "def heuristic(inst):\n    out = []\n    for i in range(len(inst.demands)):\n        for j in range(i + 1, len(inst.demands)):\n            if inst.demands[i] + inst.demands[j] <= inst.capacity:\n                out.append([0, i, j])\n    return out\n",
]


def _mock_llm():
    counter = itertools.count()

    def generate(_prompt: str) -> str:
        return _HEURISTIC_TEMPLATES[next(counter) % len(_HEURISTIC_TEMPLATES)]

    return CallableLLMClient(callable_=generate)


def _toy_evaluator(source: str) -> np.ndarray:
    """Heuristic proxy: objective values derived from code shape."""
    try:
        phi = extract_ast_features(source)
    except SyntaxError:
        return np.array([1.0, 1.0, 1.0], dtype=np.float32)
    quality = float(max(0.05, 0.8 - 0.03 * phi[3]))  # quality improves with loops
    runtime = float(0.01 + 0.02 * phi[4])            # runtime grows with nesting
    robustness = float(0.02 + 0.01 * phi[5])         # rob grows with branches
    return np.array([quality, runtime, robustness], dtype=np.float32)


def main() -> None:
    config = QDLHDConfig(
        d=2,
        bins=5,
        generations=25,
        seeds_per_persona=2,
        retrain_interval=10,
        random_seed=7,
    )
    client = _mock_llm()
    archive = run_qdlhd(client, _toy_evaluator, config)

    print(f"Archive coverage: {archive.coverage:.2%}")
    print(f"QD-score:         {archive.qd_score():.3f}")
    print(f"Occupied cells:   {len(archive.occupied_cells())}")

    # Attach affinity samples from synthetic training CVRP instances
    rng = np.random.default_rng(0)
    training_feats = []
    for cell in archive.occupied_cells():
        inst = CVRPInstance(
            coords=rng.uniform(0, 1, size=(10, 2)),
            demands=rng.uniform(1, 5, size=10),
            capacity=20.0,
            num_vehicles=3,
        )
        feat = extract_instance_features(inst)
        archive.record_affinity(cell.index, feat)
        training_feats.append(feat)

    selector = InstanceAdaptiveSelector(archive=archive).fit(np.stack(training_feats))
    unseen = CVRPInstance(
        coords=rng.uniform(0, 1, size=(10, 2)),
        demands=rng.uniform(1, 5, size=10),
        capacity=20.0,
        num_vehicles=3,
    )
    picked = selector.select(extract_instance_features(unseen))
    print(f"Selected cell:    {picked.index}")
    print("Retrieved source (first line):")
    print("    " + picked.source.splitlines()[0])


if __name__ == "__main__":
    main()
