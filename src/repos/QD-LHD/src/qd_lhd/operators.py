"""LLM-driven mutation and crossover operators.

The operators wrap an :class:`LLMClient` and a SHAP-feedback verbalizer,
producing a candidate heuristic source string that downstream code evaluates,
parses for AST features, and inserts into the archive.
"""

from __future__ import annotations

import re

import numpy as np

from qd_lhd.ast_features import AST_FEATURE_NAMES
from qd_lhd.llm_client import LLMClient
from qd_lhd.prompts import (
    crossover_prompt,
    mutation_prompt,
    seed_prompt,
    verbalize_shap,
)


_CODE_FENCE_RE = re.compile(r"```(?:python)?\n?(.*?)```", re.DOTALL)


def _strip_code_fences(text: str) -> str:
    """Return the last fenced code block if present, else ``text`` unchanged."""
    matches = _CODE_FENCE_RE.findall(text)
    return matches[-1].strip() if matches else text.strip()


def seed(
    client: LLMClient,
    persona_directive: str,
    instance_profile: str,
    signature: str,
) -> str:
    prompt = seed_prompt(persona_directive, instance_profile, signature)
    return _strip_code_fences(client.generate(prompt))


def mutate(
    client: LLMClient,
    parent_source: str,
    objectives: np.ndarray,
    shap_values: np.ndarray,
    *,
    tau_pos: float = 0.05,
    tau_neg: float = -0.05,
    target_niche: tuple[float, ...] | None = None,
) -> str:
    feedback = verbalize_shap(AST_FEATURE_NAMES, shap_values, tau_pos, tau_neg)
    prompt = mutation_prompt(parent_source, objectives, feedback, target_niche)
    return _strip_code_fences(client.generate(prompt))


def crossover(
    client: LLMClient,
    source_a: str,
    source_b: str,
    shap_a: np.ndarray,
    shap_b: np.ndarray,
    target_niche: tuple[float, ...],
    *,
    tau_pos: float = 0.05,
    tau_neg: float = -0.05,
) -> str:
    feedback_a = verbalize_shap(AST_FEATURE_NAMES, shap_a, tau_pos, tau_neg)
    feedback_b = verbalize_shap(AST_FEATURE_NAMES, shap_b, tau_pos, tau_neg)
    comparison = f"Parent A:\n{feedback_a}\n\nParent B:\n{feedback_b}"
    prompt = crossover_prompt(source_a, source_b, comparison, target_niche)
    return _strip_code_fences(client.generate(prompt))
