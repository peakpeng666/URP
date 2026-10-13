# Handwritten controls, not generated candidates

These files are source-only teaching-interpreter controls. No file in this
directory records a test run, a model call, candidate generation, an evolutionary
search result, a benchmark result, or permission to start numerical execution.
The controls were hand-authored from the explicit math-DAG contract.

`programs/published_eoh.json` is a transcription of the fixed published formula,
with exactly fifteen operation rows and five typed constants. Author source is
read-only evidence; do not import, compile, `exec`, or otherwise execute it.
When execution is separately allowed, compare against the reviewed handwritten
`../../published_eoh_formula_v1/src/formula.py` implementation.

Source identity:

- Repository: FeiLiu36/EoH
- Commit: `472545785c936dcfc863d2bc0d6109cf23c7ce62`
- Source: `examples/bp_online/evaluation/heuristic_original_EoH_paper.py`
- Source SHA256: `f3d50f0e81ca061a0377b9fb61b75cf16ecde9f091876db0d8baca8323655995`
- Git blob: `5a7970a80551d5e124234348d449d15ddf369a0e`
- Source evidence: `../../published_eoh_readiness/source_provenance.json`
- MIT notice: `../../published_eoh_readiness/upstream/LICENSE`

The graph's source correspondence is recorded in `published_formula_mapping.json`.
`evaluation_cases.json` holds prospective expectations, not observed outcomes.
`validation_cases.json` describes named, handwritten invalid mutations and raw
payloads. Mutation recipes are adversarial test inputs, never synthesized
algorithm candidates. The test plan states exact boundary and resource checks.

Do not deduplicate or discard intermediate warnings, skip dead rows, lazily
evaluate `where`, simplify the published formula, clip values, or add an
exact-fit preference. All rows execute once in listed order, including rows after
`return_node`. Only the final root must be finite; an intermediate NaN/Inf can be
permitted if its warning is retained and the finite-root condition still holds.

Preparation status: files only; numerical, parser, import, syntax-check, and
test execution have not been performed by this fixture-preparation worker.
