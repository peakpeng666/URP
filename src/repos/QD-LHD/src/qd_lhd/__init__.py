"""QD-LHD: Quality-Diversity LLM-Driven Heuristic Design.

Reference implementation accompanying the IEEE TEVC manuscript
"Illuminating Heuristic Design: Language-Model-Driven Quality-Diversity
Evolution for Combinatorial Optimization".

Public modules:
    ast_features       Table 2 AST feature extraction.
    surrogate          XGBoost surrogate over (phi(h), f_qual) pairs.
    shap_descriptors   Tree-SHAP attribution + top-d behavioral descriptors.
    archive            MAP-Elites archive data structure.
    selector           Online instance-adaptive selector (Eq. 29).
    instance_features  Six-feature instance extractor (Sec. III-E).
    evolution          Full QD-LHD loop (Algorithm 1).
    operators          LLM mutation / crossover operators.
    prompts            Seed, mutation, crossover prompt templates.
    llm_client         Abstract LLM client interface.
"""

from qd_lhd.archive import Archive, Cell
from qd_lhd.ast_features import AST_FEATURE_NAMES, extract_ast_features
from qd_lhd.instance_features import extract_instance_features
from qd_lhd.selector import InstanceAdaptiveSelector
from qd_lhd.shap_descriptors import BehavioralDescriptorBuilder
from qd_lhd.surrogate import PerformanceSurrogate

__all__ = [
    "AST_FEATURE_NAMES",
    "Archive",
    "BehavioralDescriptorBuilder",
    "Cell",
    "InstanceAdaptiveSelector",
    "PerformanceSurrogate",
    "extract_ast_features",
    "extract_instance_features",
]

__version__ = "1.0.0"
