"""End-to-end smoke test for :func:`qd_lhd.evolution.run_qdlhd`.

Uses a deterministic mock LLM and a toy evaluator so the full loop can run
in a few seconds without any API calls.
"""

from __future__ import annotations

import itertools
import textwrap

import numpy as np

from qd_lhd.evolution import QDLHDConfig, run_qdlhd
from qd_lhd.llm_client import CallableLLMClient


_TEMPLATES = [
    "def heuristic(inst):\n    return sorted(range(len(inst)))\n",
    "def heuristic(inst):\n    out = []\n    for i in range(len(inst)):\n        out.append(i)\n    return out\n",
    "def heuristic(inst):\n    out = []\n    for i in range(len(inst)):\n        for j in range(i, len(inst)):\n            if i != j:\n                out.append((i, j))\n    return out\n",
    "def heuristic(inst):\n    def rec(i):\n        if i >= len(inst):\n            return []\n        return [i] + rec(i + 1)\n    return rec(0)\n",
    "def heuristic(inst):\n    d = {i: inst[i] for i in range(len(inst))}\n    return sorted(d, key=d.get)\n",
]


def _mock_llm_factory():
    counter = itertools.count()

    def generate(_prompt: str) -> str:
        idx = next(counter)
        return _TEMPLATES[idx % len(_TEMPLATES)]

    return CallableLLMClient(callable_=generate)


def _toy_evaluator(source: str) -> np.ndarray:
    n_lines = len(source.splitlines())
    # Pretend quality improves with lines, runtime degrades with lines, robustness stable
    return np.array(
        [
            max(0.1, 1.0 - 0.05 * n_lines),
            0.02 * n_lines,
            0.05,
        ],
        dtype=np.float32,
    )


def test_run_qdlhd_populates_archive():
    client = _mock_llm_factory()
    config = QDLHDConfig(
        d=2,
        bins=4,
        generations=20,
        seeds_per_persona=2,
        retrain_interval=10,
        random_seed=1,
    )
    archive = run_qdlhd(client, _toy_evaluator, config)
    assert archive.coverage > 0.0
    # At least one cell should have been occupied by the seed phase
    assert len(archive.occupied_cells()) >= 1
    # QD-score is finite and non-negative
    assert archive.qd_score() >= 0.0
