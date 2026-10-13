"""Unit tests for :mod:`qd_lhd.operators` and :mod:`qd_lhd.prompts`."""

from __future__ import annotations

import numpy as np

from qd_lhd.llm_client import CallableLLMClient
from qd_lhd.operators import crossover, mutate, seed
from qd_lhd.prompts import PERSONA_GROUPS, verbalize_shap


FAKE_CODE = "def heuristic(inst):\n    return []\n"


def test_seed_returns_stripped_code_fences():
    client = CallableLLMClient(callable_=lambda _p: f"```python\n{FAKE_CODE}```")
    src = seed(client, PERSONA_GROUPS[0][1], "tiny CVRP", "def heuristic(inst): ...")
    assert src.startswith("def heuristic")


def test_mutate_includes_shap_feedback_in_prompt():
    captured: dict[str, str] = {}

    def capture(prompt: str) -> str:
        captured["prompt"] = prompt
        return FAKE_CODE

    client = CallableLLMClient(callable_=capture)
    shap_values = np.array([0.2, -0.15, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    out = mutate(client, FAKE_CODE, np.array([0.1, 0.2, 0.05]), shap_values)
    assert out.startswith("def heuristic")
    prompt = captured["prompt"]
    assert "SHAP" in prompt
    assert "ast_depth" in prompt
    assert "num_nodes" in prompt


def test_crossover_includes_target_niche():
    captured: dict[str, str] = {}

    def capture(prompt: str) -> str:
        captured["prompt"] = prompt
        return FAKE_CODE

    client = CallableLLMClient(callable_=capture)
    shap_a = np.full(11, 0.1)
    shap_b = np.full(11, -0.1)
    out = crossover(client, FAKE_CODE, FAKE_CODE, shap_a, shap_b, target_niche=(0.1, 0.5, 0.9))
    assert out.startswith("def heuristic")
    assert "Target niche" in captured["prompt"]


def test_verbalize_shap_picks_extreme_features():
    values = np.zeros(11)
    values[0] = 0.2
    values[3] = -0.15
    text = verbalize_shap(
        feature_names=tuple(f"f{i}" for i in range(11)),
        values=values,
        tau_pos=0.05,
        tau_neg=-0.05,
    )
    assert "f0" in text and "+0.200" in text
    assert "f3" in text and "-0.150" in text


def test_verbalize_shap_no_extreme_features():
    values = np.full(11, 0.01)
    text = verbalize_shap(
        feature_names=tuple(f"f{i}" for i in range(11)),
        values=values,
        tau_pos=0.05,
        tau_neg=-0.05,
    )
    assert "No feature" in text
