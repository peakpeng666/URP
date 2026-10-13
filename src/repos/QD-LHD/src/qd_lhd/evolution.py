"""Algorithm 1: QD-LHD evolutionary loop.

Thin orchestration over the other modules; users plug in an :class:`LLMClient`,
an evaluator callable, and seed instances, and receive a populated archive.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import shap

from qd_lhd.archive import Archive
from qd_lhd.ast_features import extract_ast_features
from qd_lhd.llm_client import LLMClient
from qd_lhd.operators import crossover, mutate, seed
from qd_lhd.prompts import PERSONA_GROUPS
from qd_lhd.shap_descriptors import BehavioralDescriptorBuilder, to_cell_index
from qd_lhd.surrogate import PerformanceSurrogate


Evaluator = Callable[[str], np.ndarray]
"""A function mapping heuristic source to a 3-vector ``(f_qual, f_time, f_rob)``."""


@dataclass(slots=True)
class QDLHDConfig:
    d: int = 3
    bins: int = 10
    generations: int = 500
    seeds_per_persona: int = 10
    mutation_ratio: float = 0.7
    retrain_interval: int = 50
    weights: tuple[float, float, float] = (0.6, 0.2, 0.2)
    instance_profile: str = "design a construction heuristic for routing instances"
    signature: str = "def heuristic(instance):\n    ..."
    random_seed: int = 0


def _raw_ast_descriptor(features: np.ndarray, top_idx: np.ndarray) -> np.ndarray:
    """Seed-phase descriptor: min-max normalized slice of raw AST features."""
    selected = features[:, top_idx]
    mins = selected.min(axis=0)
    maxs = selected.max(axis=0)
    span = np.where(maxs - mins > 1e-12, maxs - mins, 1.0)
    return np.clip((selected - mins) / span, 0.0, 1.0)


def seed_phase(
    client: LLMClient,
    evaluator: Evaluator,
    config: QDLHDConfig,
) -> tuple[list[str], list[np.ndarray], list[np.ndarray]]:
    """Generate ``K_init`` seed heuristics across the five persona groups."""
    sources: list[str] = []
    features: list[np.ndarray] = []
    objectives: list[np.ndarray] = []
    for _, directive in PERSONA_GROUPS:
        for _ in range(config.seeds_per_persona):
            src = seed(client, directive, config.instance_profile, config.signature)
            try:
                phi = extract_ast_features(src)
            except SyntaxError:
                continue
            obj = evaluator(src)
            sources.append(src)
            features.append(phi)
            objectives.append(obj)
    return sources, features, objectives


def run_qdlhd(
    client: LLMClient,
    evaluator: Evaluator,
    config: QDLHDConfig,
) -> Archive:
    """Run the full loop and return the populated archive."""
    rng = random.Random(config.random_seed)
    np.random.seed(config.random_seed)

    archive = Archive(d=config.d, bins=config.bins, weights=config.weights)
    sources, features, objectives = seed_phase(client, evaluator, config)

    feat_matrix = np.stack(features)
    obj_matrix = np.stack(objectives)
    variances = feat_matrix.var(axis=0)
    top_idx = np.argsort(-variances)[: config.d]
    seed_descriptors = _raw_ast_descriptor(feat_matrix, top_idx)

    for src, phi, obj, desc in zip(sources, features, objectives, seed_descriptors):
        archive.insert(to_cell_index(desc, config.bins), src, phi, obj)

    surrogate = PerformanceSurrogate(random_state=config.random_seed)
    surrogate.fit(feat_matrix, obj_matrix[:, 0])
    descriptor_builder = BehavioralDescriptorBuilder(d=config.d)
    descriptor_builder.fit(surrogate, feat_matrix)

    explainer = shap.TreeExplainer(surrogate.model)

    for gen in range(1, config.generations + 1):
        occupied = archive.occupied_cells()
        if not occupied:
            break
        parent = rng.choice(occupied)
        assert parent.features is not None and parent.objectives is not None
        shap_parent = explainer.shap_values(parent.features[None, :])[0]

        if rng.random() < config.mutation_ratio or len(occupied) < 2:
            offspring_src = mutate(client, parent.source, parent.objectives, shap_parent)
        else:
            partner = rng.choice([c for c in occupied if c.index != parent.index])
            assert partner.features is not None
            shap_partner = explainer.shap_values(partner.features[None, :])[0]
            target = tuple(rng.random() for _ in range(config.d))
            offspring_src = crossover(
                client,
                parent.source,
                partner.source,
                shap_parent,
                shap_partner,
                target,
            )

        try:
            phi = extract_ast_features(offspring_src)
        except SyntaxError:
            continue
        obj = evaluator(offspring_src)

        feat_matrix = np.vstack([feat_matrix, phi])
        obj_matrix = np.vstack([obj_matrix, obj])

        desc = descriptor_builder.describe(phi)[0]
        archive.insert(to_cell_index(desc, config.bins), offspring_src, phi, obj)

        if gen % config.retrain_interval == 0:
            surrogate.fit(feat_matrix, obj_matrix[:, 0])
            descriptor_builder.fit(surrogate, feat_matrix)
            explainer = shap.TreeExplainer(surrogate.model)

    return archive
