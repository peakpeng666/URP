# QD-LHD: Reference Implementation

Reproduction package for **"Illuminating Heuristic Design: Language-Model-Driven
Quality-Diversity Evolution for Combinatorial Optimization"** (IEEE TEVC).

## What is here

| Module                         | Role                                                                    |
| ------------------------------ | ----------------------------------------------------------------------- |
| `qd_lhd.ast_features`          | Eleven AST-based code features (Table 2 of the paper).                  |
| `qd_lhd.surrogate`             | XGBoost surrogate trained on `(phi(h), f_qual(h, I))` pairs.            |
| `qd_lhd.shap_descriptors`      | Tree-SHAP-derived top-d behavioral descriptor construction.             |
| `qd_lhd.archive`               | MAP-Elites archive with two-stage Pareto-then-scalarization cell competition. |
| `qd_lhd.instance_features`     | Six-feature instance extractor for CVRP, TSP, and JSSP (Section III-E). |
| `qd_lhd.selector`              | Online instance-adaptive selector (Eq. 29) with KD-tree nearest-cell lookup. |
| `qd_lhd.operators`             | LLM-driven mutation and crossover operators.                            |
| `qd_lhd.prompts`               | Seed, mutation, and crossover prompt templates plus SHAP verbalizer.    |
| `qd_lhd.llm_client`            | Minimal `LLMClient` protocol (wrap any `prompt -> completion` callable). |
| `qd_lhd.evolution`             | `run_qdlhd(...)`: Algorithm 1 orchestration from seeds to final archive. |

All eleven AST features, the three Propositions of Section IV (coverage,
descriptor drift, cell-decomposed robustness), and the deployment-time
selector of Eq. 29 have corresponding code in one of the modules above.

## Install

```bash
python -m pip install -e .[dev]
```

Requires Python >= 3.10. Core dependencies: `numpy`, `scipy`, `networkx`,
`xgboost`, `shap`.

## One-command reproduction (smoke demo)

No LLM API key required: the demo uses a deterministic mock LLM so the full
pipeline runs in seconds and exercises every module end-to-end.

```bash
python examples/run_demo.py
```

Expected stdout (order-of-magnitude; exact numbers depend on the random seed):

```
Archive coverage: 28.00%
QD-score:         1.123
Occupied cells:   7
Selected cell:    (2, 3)
Retrieved source (first line):
    def heuristic(inst):
```

## Running with a real LLM backend

```python
from qd_lhd.evolution import QDLHDConfig, run_qdlhd
from qd_lhd.llm_client import CallableLLMClient

def generate(prompt: str) -> str:
    # Replace with an OpenAI / Anthropic / Qwen / vLLM call.
    return call_your_llm(prompt)

client = CallableLLMClient(callable_=generate)
archive = run_qdlhd(client, your_evaluator, QDLHDConfig())
```

The `evaluator` is a user-supplied callable mapping a heuristic source string
to a 3-vector `(f_qual, f_time, f_rob)` (Eqs. 1--3 of the paper).

## Tests

```bash
python -m pytest
```

The suite (~40 tests) covers AST parsing, surrogate fit/predict, SHAP
descriptor extraction, archive cell competition and QD-score, instance
feature formulas, selector nearest-neighbor lookup, operator prompt
assembly, and an end-to-end 20-generation smoke run of `run_qdlhd`.

## Layout

```
LLM_CO/
├── README.md
├── pyproject.toml
├── src/qd_lhd/
│   ├── archive.py
│   ├── ast_features.py
│   ├── evolution.py
│   ├── instance_features.py
│   ├── llm_client.py
│   ├── operators.py
│   ├── prompts.py
│   ├── selector.py
│   ├── shap_descriptors.py
│   └── surrogate.py
├── tests/
│   ├── test_archive.py
│   ├── test_ast_features.py
│   ├── test_evolution_smoke.py
│   ├── test_instance_features.py
│   ├── test_operators.py
│   ├── test_selector.py
│   ├── test_shap_descriptors.py
│   └── test_surrogate.py
└── examples/
    └── run_demo.py
```

## License

MIT.
