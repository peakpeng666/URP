"""Prompt templates for seed generation, mutation, and crossover.

Five persona groups of ten seeds, matching the manuscript (Section III-C-1).
"""

from __future__ import annotations

import numpy as np

PERSONA_GROUPS: tuple[tuple[str, str], ...] = (
    ("greedy", "an algorithm designer who favors greedy construction"),
    ("local_search", "an algorithm designer who favors local search with neighborhood exploration"),
    ("lns", "an algorithm designer who favors large-neighborhood destroy-and-repair"),
    ("constraint_first", "an algorithm designer who favors constraint-first decomposition"),
    ("hybrid", "an algorithm designer who combines greedy construction with local refinement"),
)


def seed_prompt(persona_directive: str, instance_profile: str, signature: str) -> str:
    """Three-block seed prompt (Section III-C-1): persona + profile + signature."""
    return (
        f"You are {persona_directive}.\n\n"
        f"Target instance profile: {instance_profile}\n\n"
        "Return a Python function with the following signature (no explanation, "
        "code only):\n"
        f"{signature}\n"
    )


def mutation_prompt(
    parent_source: str,
    objectives: np.ndarray,
    shap_feedback: str,
    target_niche: tuple[float, ...] | None = None,
) -> str:
    """Four-component mutation prompt (Section III-C-2)."""
    parts = [
        "Refine the following heuristic. Keep the function signature unchanged.",
        "",
        "# Parent source",
        parent_source.strip(),
        "",
        f"# Parent performance: f_qual={objectives[0]:.4f}, f_time={objectives[1]:.4f}, f_rob={objectives[2]:.4f}",
        "",
        f"# Structural feedback\n{shap_feedback}",
    ]
    if target_niche is not None:
        parts.extend(["", f"# Target behavioral niche: descriptor coordinates {tuple(round(x, 3) for x in target_niche)}"])
    parts.extend(["", "Return only the modified function body, no commentary."])
    return "\n".join(parts)


def crossover_prompt(
    source_a: str,
    source_b: str,
    shap_comparison: str,
    target_niche: tuple[float, ...],
) -> str:
    """Crossover prompt merging two parents (Section III-C-3)."""
    return (
        "Merge the complementary strengths of the two heuristics below into one "
        "offspring, targeting the specified behavioral niche. Keep the function "
        "signature unchanged.\n\n"
        "# Parent A\n"
        f"{source_a.strip()}\n\n"
        "# Parent B\n"
        f"{source_b.strip()}\n\n"
        f"# Structural comparison\n{shap_comparison}\n\n"
        f"# Target niche: descriptor coordinates {tuple(round(x, 3) for x in target_niche)}\n\n"
        "Return only the merged function body, no commentary."
    )


def verbalize_shap(feature_names: tuple[str, ...], values: np.ndarray, tau_pos: float, tau_neg: float) -> str:
    """Turn a SHAP attribution vector into the natural-language feedback block."""
    lines: list[str] = []
    for name, value in zip(feature_names, values):
        v = float(value)
        if v > tau_pos:
            lines.append(f"(+) `{name}` (SHAP = +{v:.3f}) contributes positively; preserve the pattern.")
        elif v < tau_neg:
            lines.append(f"(-) `{name}` (SHAP = {v:.3f}) degrades performance; simplify this part.")
    if not lines:
        lines.append("No feature is above the +0.05 or below the -0.05 attribution threshold.")
    return "\n".join(lines)
