# Reproducing the P2 response experiment

The delivery preserves the original experiment-relative paths under URP. The
machine-readable manifest records exact file sizes and SHA256 hashes. Its
ledger, events and 780 observations are original saved evidence, not rerun data.

## Dependencies and trusted build

Use a fresh Linux x86_64 workspace with host CPython 3.12.14. The official PyPI
wheel pins and hashes are in `requirements.lock.txt`; provenance, official
release metadata and licenses are in `provenance/`. No installed environment,
wheel, native cache or Wasm binary is included in this lightweight delivery.

From `URP/experiments/isolated_evaluator` in a fresh reproduction copy:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements.lock.txt
mkdir -p build logs results
.venv/bin/python -B src/clean_build.py --prepare
# Review the newly captured build inputs and configuration before continuing.
.venv/bin/python -B src/clean_build.py --execute
.venv/bin/python -B src/bounded_compile.py clean
```

Only the fixed trusted guest wrapper may enter this build. Generated source
must never be imported, componentized or used as a build input. The builder
explicitly selects its own venv site-packages and a clean environment; upstream
initialization can see source/stdlib mounts, so building is not the untrusted
execution boundary. Final components must have zero imports and match the exact
invoked scalar ABI before native caching. Default memory guards/reservations
must remain enabled; copied initialization is the recorded configuration.

The scripts retain write-once evidence. Do not overwrite the delivered inputs,
logs or observations. A fresh installation, host interpreter, toolchain or path
may produce different files and hashes. The historical 979-file freeze is tied
to the original environment, not a bit-for-bit portable or fully hermetic build
promise. Prepare and independently review a new freeze for any reproduction;
do not edit the old manifest merely to make a verification pass.

## Validation before any generated execution

Trusted handwritten validation sources cover the 60 valid-list fixtures,
malformed output, strict type comparisons, bounded input/output, effective
rlimits, fresh state and kill/reap paths. Preserve the existing 12 exclusions.
The public operational runner requires matching external authorization and
full input/dependency verification. An explicit local run authorization is
required for each new generated batch; these instructions do not start a run.

Every permitted generated request must remain runtime string data inside a
fresh import-free Wasm instance, with the exact reviewed resource limits.
The AST gate preserves the experiment's original source contract; it is not
the host-security sandbox. The independent host checker validates observable
response values only. Do not reuse these results as mutation, identity,
exception-type or complete Python correctness evidence.

## Evidence layout

- `proposed_p2_value_v2/`: frozen runner, configuration, source/fixture plan and tests
- `src/`: trusted guest, build/compile scripts, host checker and runtime configuration
- `provenance/` and `requirements.lock.txt`: official dependency and build provenance
- `runs/generated_batch_20261004_01/results/`: original initial/final ledger, events and observations
- `sorting_generation/fixtures/cases.json` and the two original JSONL files: all fixtures and exact raw/extracted source data
- `delivery_v2/source_hashes.json`: compact raw/extracted source-form hashes and the sole fixed alias
- `delivery_v2/summary.json`: reviewed results and measured costs, with public reproducibility metadata

The embedded CPython is the upstream componentize-py maintainer's WASI fork.
The provenance records the remaining fork-license and transitive/reproducibility
limitations. This lightweight package does not redistribute runtime binaries.
