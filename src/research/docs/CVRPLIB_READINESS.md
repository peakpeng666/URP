# Genuine CVRPLIB runner: readiness, not formal results

Run ID: `20261014T084727Z`. Base repository commit: `f110f039854f7314e36632ce7d3ee977cd0de0fc`.

This standalone path operates on original CVRPLIB coordinates and integer per-edge EUC_2D distances. It does not replace or relabel the historical synthetic `cvrp-selection-crc` module, its 253 PASS record, or frozen reports. No formal 53-case × seed comparison or paid model call was run.

## Offline setup

Python 3.12 and Linux x86_64 are required. From the delivered project root, first restore archive-backed wheels when using the GitHub tree (expanded Drive packages already contain them):

```sh
python3 runtime/cvrplib/restore_wheels.py
```

This checks the original r1 ZIP and all 14 member hashes and restores the canonical `runtime/cvrplib/wheels` directory without network access. See `runtime/cvrplib/WHEEL_ARCHIVE_MAP.json` and its tested restoration receipt. Then:

```sh
python3.12 -m venv .venv-cvrplib
.venv-cvrplib/bin/python -m pip install --no-index --require-hashes --find-links runtime/cvrplib/wheels -r runtime/cvrplib/requirements.lock
.venv-cvrplib/bin/python src/research/scripts/cvrplib.py --help
.venv-cvrplib/bin/python src/research/scripts/test.py
```

The 14 wheels are byte-identical to the pinned PREEXEC archive, verified against its `WHEELS.json` and pip hashes. PyVRP is exactly 0.14.0, with its real default ILS search, not HGS. The alternate archive-restoration script accepts the known final-r1 or PREEXEC archive hashes through `--archive` and does not use a network registry.

## One acceptance call

```sh
.venv-cvrplib/bin/python src/research/scripts/cvrplib.py run-one --instance data/benchmarks/CVRPLIB/instances/P-n19-k2.vrp --algorithm pyvrp --seed 0 --budget 1 --output experiments/runs/my-new-acceptance --run-registry experiments/runs/cvrplib-run-registry
.venv-cvrplib/bin/python src/research/scripts/cvrplib.py score --repo . --result experiments/runs/my-new-acceptance/result.json --output experiments/runs/my-new-acceptance/evaluation.json
```

The existing entry `src/research/scripts/urp.py cvrplib ...` also works. `run-one` exposes no batch or model-call option. Five recovered arms are `savings`, `T`, `TRS`, `TSR`, and `pyvrp`; classical move bodies and the original PyVRP model/extractor remain hash-pinned under `frozen/`. The adapter changes accounting/checkpoint plumbing and supplies the shared integer-edge contract, not a new claimed historical algorithm. Seeds have no randomizing effect on the deterministic classical arms.

A project-wide atomic run registry rejects a repeated key comprising instance hash, algorithm, seed, budget, fleet contract, and solver-source digest, even under a new output name. Failed attempts keep their claim. Choosing an explicit new registry creates a separately named experiment, not permission to silently rerun/select results. Output directories are also exclusive. Direct `run_payload` is a low-level fault-testing API without persistent key claims; published experiments must use the CLI/registry.

## Budget and acceptance semantics

- The wall clock starts before request serialization and subprocess launch. All interpreter and algorithm imports, model construction, initial solution, search, serialization, and checkpoint delivery consume it. This is intentionally stricter than the archived solver-loop-only MaxRuntime measurement.
- The supervisor receives newline-delimited checkpoints and independently enforces `start <= emitted <= received <= deadline`. A forged earlier timestamp cannot make a late received result eligible. No optimum/BKS stopping is used.
- PyVRP's supported ILS callbacks publish initial and improving feasible solutions without changing default search operators/parameters. The parent kills the process group at the deadline and only retains already-received, independently checked solutions. A late final result is never accepted. `TIMEOUT_WITH_FEASIBLE_INCUMBENT` is expected for a time-budget search; it is not mislabeled normal completion.
- A crash, resource failure, malformed event, invalid route, or false cost cannot masquerade as a successful candidate. `NO_SOLUTION` and `INVALID_SOLUTION` never claim mathematical infeasibility.
- CPU is separately reported using `wait4` worker user+system time; adopted descendant CPU is separately listed. Process wall includes cleanup, while checker CPU/wall and cleanup wall are explicit audit overheads. These are not substituted for search time.
- Linux subreaper state is process-global, so concurrent calls in one supervisor are explicitly rejected. Process-group descendants are killed/reaped. Reviewed workers prohibit Python file/network/process creation after imports, including fork. This is not a syscall sandbox for hostile native code or escaped new sessions; do not run unreviewed generated code through it.

Workers receive only coordinates, demands, capacity, K, algorithm, seed and budget. Names, comments, reference routes, BKS and paths stay outside. X uses at most one available vehicle per customer with fixed cost zero (unlimited fleet semantics), never the filename K. Non-X contracts are audited and fixed at their verified K; the demand lower bound equals K. Capped-X is a separately labeled derived problem, never mixed into standard-X results.

Post-run scoring verifies original/reference hashes, result instance and payload identities, contract, budget/timing evidence, matching received checkpoint, route coverage/capacity/count, and exact cost before allowing a reference gap. These consistency checks are not a cryptographic signature; preserve and hash the complete evidence bundle.

## Actual acceptance evidence

`acceptance/20261014T084727Z/` contains fresh logs, all fault results, runtime/source versions and smoke commands. The recovered incomplete 44/50 fixture grid is historical recovery evidence only, not this final acceptance.

- Core regression: 99 tests (73 legacy plus 26 CVRPLIB), all passed on the repaired source.
- Ten invented tiny-fixture calls: all five arms, budgets 1s and 5s, seed 0. All feasible and no cost below the exhaustive independently computed fixture optimum. This is acceptance, not statistical comparison.
- Seven public calls: P-n19-k2 on all five arms; A-n32-k5 on PyVRP at 1s; X-n101-k25 on PyVRP at 5s. Every output separately independently scored. The three PyVRP costs were 212, 784 and 27597 respectively. These are smoke observations, not superiority claims.
- The independent data audit compares all 53 original/reference pairs and 1,350,504 directed integer-distance cells; it performs no optimization.

Before any scientific batch: separately authorize the formal schedule, freeze its source/data/runtime/contract hashes and run-key registry, retain every failure/unstarted denominator, and predefine budget/seed/aggregation decisions. Do not treat this acceptance as the missing formal experiment.

### Provenance and wider-test limitations

PyVRP archive/wheels were independently rehashed in this run. On 2026-10-14 the original VND ZIP was retrieved and independently verified: archive size/hash and all 10 declared members match delivered source byte for byte. See `audits/cvrplib/vnd_original/`; the original source bytes and earlier logs remain unchanged. The earlier release's pending statement records its historical preparation state, not the current provenance status. `configs/cvrplib_algorithms.json` states each arm's operator order and seed role.

The optional legacy execution-supervisor suite initially had one timing-sensitive injected-error assertion fail (24/25 passed). The exact isolated test subsequently passed without source changes. Original and rerun logs are retained, rather than deleting the failed attempt. This suite exercises the pre-existing supervisor, not the new CVRPLIB runner; its broader result must be read separately from the 99-test core PASS. The generator's 12 tests passed unchanged.

### Test-harness hardening after root review

A fresh root rerun initially returned 98/99: the malformed-output fixture's 0.2s process allowance expired before its expected schema behavior was observed. The failed log is retained under `acceptance/20261014T085915Z-test-hardening/`. The production supervisor and solver budgets were not changed, and the test still requires exactly `API_ERROR`, never an alternative timeout status. Non-timing fault fixtures now have a 5s startup allowance and exit immediately. Dedicated timeout probes retain explicit cutoffs; the initialization probe must emit `INITIALIZATION_ENTERED` before its deliberate delay, and the checkpoint probe still requires receipt by the actual deadline. Local elapsed-time guards are diagnostics, not guarantees about OS scheduling latency. Three full-suite repetitions are recorded after these fixture-only changes; see that directory's final logs and updated source manifest. Earlier source manifests describe their earlier snapshots rather than the current test harness.
