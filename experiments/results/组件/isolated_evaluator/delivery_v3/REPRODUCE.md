# Reproducing the limited-language v3 experiment

The public manifest uses paths relative to URP. It contains original saved
ledgers, events and observations, exact source-form hashes, trusted evaluator
and runner sources, protocol and build provenance. v2 remains a separately
identified antecedent experiment. The installed environment, wheels and Wasm/
native binary caches are deliberately omitted and must be rebuilt locally.

## Environment and trusted build

The historical host was Linux x86_64, CPython 3.12.14. Official PyPI pins and
wheel hashes are in `requirements.lock.txt`; release metadata, licenses and
provenance are in `provenance/`. The embedded guest is CPython 3.14.0 from the
componentize-py upstream maintainer's WASI branch. The provenance records the
remaining fork-license and complete-transitive-reproducibility limitations.
This delivery does not redistribute runtime binaries.

Use a **fresh reproduction copy**, preserving the delivered historical evidence.
From `URP/experiments/isolated_evaluator`, create a new venv with the pinned
requirements:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements.lock.txt
```

The fixed v3 guest is in `limited_semantics_v3/src/guest/`: the WIT interface,
closed AST validator, isolated semantic evaluator and scalar transport wrapper.
Only these trusted files may be imported during componentization. Generated
programs must never enter the build or any host Python import/exec/eval path.

The historical build commands were:

```sh
.venv/bin/python -B limited_semantics_v3/src/clean_build.py --prepare
# Inspect the captured explicit source/venv inventory and clean environment.
.venv/bin/python -B limited_semantics_v3/src/clean_build.py --execute
.venv/bin/python -B limited_semantics_v3/src/bounded_compile.py clean
```

These scripts use write-once execution logs. Existing delivered evidence must
not be overwritten to run the commands. Prepare separate empty output/log/
provenance locations in a fresh reproduction workspace. A new workspace path,
interpreter or installation changes captured inputs and may change binary hashes;
a new reviewed deployment freeze is required. Do not alter historical hashes to
make a new build appear identical. The old freeze is environment-specific, not a
promise of a portable bit-identical or hermetic build.

Before caching, verify the **final component has zero imports**, retain the exact
host-invoked scalar ABI (`run`, `output-byte`), and use an empty linker. The upstream
`exports` metadata namespace also contains an initialization export which the
runtime never invokes. Keep Wasmtime's default guard/reservation protections.
The recorded `memory_init_cow=False` chooses copied initialization under FSIZE=0;
it does not justify removing bounds or guards. Only hash-verified bytes from a
locally trusted native cache may be deserialized.

## Validation and local run approval

The preserved handwritten controls cover all 72 fixture types, grammar rejection,
spoofing/rebinding/reflection rejection, exact measurements, bounded flat results,
resource outcomes and kill/reap behavior. The original fuel-test assertion failure
and its explicit predicate correction are retained; no artifact change was used
to hide the failed assertion. A mutation-and-restoration control intentionally
passes, documenting the final-state limitation.

The operational implementation adds bounded authorization input, immutable approved
manifest identity on each recheck, complete initial ledgers, streaming observations,
conservative infrastructure/resource categories and deterministic budget accounting.
The implementation was tested with 79 handwritten Wasm requests, two real pre-entry
rejections, two no-dispatch cases and 22 deterministic tests before the generated run.

A separately approved local batch is required. Its approval must match the new
operational and prototype freeze, state the exact source scope, and carry a fresh
one-use batch identifier. Passing tests or possessing this package does not itself
start a run. The entrypoint is:

```sh
.venv/bin/python -B operational_v3/batch_runner.py \
  --approved-batch <explicit-local-authorization.json> \
  --output <new-result-directory>
```

Never repair generated programs, loosen grammar, reduce late-request limits, or
silently retry to complete a ledger. Preserve every started request and any
unattempted/unknown rows. A changed frozen input stops the run and invalidates
certification until revalidation.

## Interpreting evidence

The raw32 and existing extracted10 forms are separate descriptive populations.
All 42 forms keep all 72 fixture IDs. Structural/grammar rejection is distinct
from an executed semantic counterexample. An admitted form passes only if all72
required cases complete cleanly and conform. Resource/budget/infrastructure gaps
are unknown, not functional failures.

The measured contract includes value/type, original-object identity, final input
state and exact TypeError on invalid fixtures within the closed language. It does
not prove absence of transient mutation, arbitrary Python correctness, a formal
integrity theorem, or the original 256 MiB hard total RSS constraint.

No generated replay was performed during saved-output verification. Retained
observations, events and source/input hashes are the evidence for this one batch.
