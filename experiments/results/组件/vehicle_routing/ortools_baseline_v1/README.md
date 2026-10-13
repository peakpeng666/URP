# OR-Tools CVRP baseline v1

## Result

A third solver family is integrated: official Google OR-Tools Routing guided local search (GLS), version **9.15.6755**. This is the second mature external library alongside PyVRP, not three mature libraries. Both explicit OR-Tools initialization variants were feasible but were worse than savings-warm PyVRP on **all 24 base-instance means at both tested CPU ceilings**. No positive H1/complementarity or selector claim follows.

The 24 existing development instances cover uniform and clustered geometry, n=50/100/200, four cases per cell. Each configuration has three labels and two CPU ceilings; OR-Tools labels are timing repeats, not effective RNG seeds. The earlier frozen instances were reused deliberately: this is exploratory development, not a blind final test or new independent replication.

| Mean cost excess over savings-warm PyVRP | 0.25 s solver CPU ceiling | 1.0 s solver CPU ceiling |
|---|---:|---:|
| OR-Tools PATH_CHEAPEST_ARC + GLS | 5.1602% | 4.1588% |
| OR-Tools savings-warm + GLS | 1.7968% | 1.8286% |

Means first aggregate three calls per base instance, then weight each instance equally. All 24 pairs are complete; there are no failure exclusions. OR savings initialization reduces cost versus OR path construction by 3.1336%/2.1754% on average, with 21/19 wins and 3/5 losses respectively. Thus initialization remains consequential, but savings is not uniformly best on each case.

Against the transparent VND baseline, warm OR improves average cost by only 0.1181%/0.5506%, with win/tie/loss counts 15/1/8 and 18/1/5. Neither that descriptive crossing nor additional configurations of one library establish useful family complementarity. The bounded GLS configuration is not claimed to represent universally best OR-Tools performance.

## Validation and repeats

- Author preflight: **13/13 tests**, first attempt, including known/exhaustive micro optima, mandatory and zero-demand customers, coincident nodes, n-vehicle fleet equivalence, capacity arithmetic above 2^53, integer scaling/overflow, warm-start restoration, fixed-work repeat labels, n50/100/200 checkpoints and injected runtime failures
- Primary: **576/576 independently accepted and in budget**
- Frozen selected replays: **192/192 independently accepted and in budget**
- **169/192** replays reproduce identical routes and costs; all 23 differences remain saved. Exact counts by method: VND 48/48, PyVRP warm 43/48, OR path 34/48, OR warm 44/48. This is a timing-repeat study; bitwise replay is not asserted
- Both OR variants also lose to warm PyVRP on all 24 selected single-label replay cases at each ceiling. Replay means are separate from the three-label primary estimates
- Saved-output audit independently rechecks 576 integer objectives and 384 warm starts across primary/replay, with zero failures. Maximum original-versus-quantized discrepancy is **0.000011100690244347788** coordinate units, within the per-route bounds
- Source/snapshot, prior artifact and installed dependency hashes match; frozen order, selected replay scope, raw JSONL/CSV and recalculated summary checks pass

The independent reviewer separately checked three CPU clock-boundary probes and the official wheel/version/file provenance before execution. The independent final outcome audit is separate from the author's preflight suite.

## CPU and wall clocks

OR-Tools exposes wall-time stopping. Model building, quantization, savings construction, independent warm validation, assignment restore, search and extraction/scoring are charged inside solver CPU. Remaining CPU allowance less a 20 ms margin becomes a conservative backend wall allowance. Imports/startup/validation and serialization/exit remain in complete-process accounting. No equal-consumed-compute claim is made.

| Mean actual solver CPU, seconds | 0.25 s ceiling | 1.0 s ceiling |
|---|---:|---:|
| VND | 0.20659 | 0.70175 |
| PyVRP savings-warm | 0.23554 | 0.98550 |
| OR path | 0.23392 | 0.98400 |
| OR savings-warm | 0.23457 | 0.98410 |

The external supervisor monitors solver CPU relative to an explicit start marker, stops that monitoring at an explicit solver-finished marker, and separately enforces the whole-worker wall limit. Tick granularity and polling prevent an exact mathematical hard CPU boundary; final conformance uses unrounded returned process-time telemetry. Injected startup and post-solve CPU delays do not consume the solver-only allowance, while an injected solver spin is killed. This is trusted-code containment, not an adversarial sandbox.

Primary measured cost: **389.5657 s wall, 413.6002 s parent+complete-child CPU**, including 328.7506 s solver CPU. Selected replay: **130.1611 s wall, 138.2797 s parent+complete-child CPU**, including 109.7357 s solver CPU. Combined scoped loops: **519.7268 s wall, 551.8799 s CPU**. Installation, preflight, freezing, final writes, later arithmetic audits/review and assistant/human/platform labor are outside those loop clocks and are not assumed free. Zero experimental model/paid API calls.

## Task fidelity

The task specification/checker are unchanged: every customer exactly once, exact integer capacities, depot zero, unlimited identical vehicles, unrounded Euclidean final score. OR supplies n vehicles at zero fixed cost, mandatory nodes, zero capacity slack and only arc-distance cost. No dropping, route-count penalty, time/distance dimension or span term was introduced. OR/PyVRP optimize the integer proxy floor(10^6*d+0.5); library objective is checked against an independently summed edge proxy, and the independent checker recomputes original coordinates. The rounding bound is an approximation bound, not an optimality guarantee. Warm input routes and objectives are saved and independently validated; final integer incumbents cannot worsen them.

## Reproduction and artifacts

The new hidden `.venv` is independent of all previous experiments. `requirements.lock.txt`, `requirements.hashed.txt`, `install_report.json`, `pyvrp_install_report.json`, `dependency_provenance.json` and `licenses/` record 20 resolved packages, official wheel digests and 4,255 installed-file hashes. OR-Tools is Apache-2.0; each dependency's own license is preserved. Binaries, `.venv`, caches and temporary directories must be excluded from distributables.

- `PROTOCOL.md`, `protocol.json`: frozen design and stopping/accounting rules
- `API_EVIDENCE.md`, `default_search_parameters.txt`: official documentation and pinned defaults
- `adapter.py`, `runtime.py`, `experiment.py`, `test_adapter.py`: original integration and controls; existing trusted VND/PyVRP code imported unchanged
- `preflight_attempt1.log`, `preflight_hashes.json`: preflight evidence
- `runs/dev_20261004_01/freeze.json`: freeze SHA256 **81cc32496b9739d1e1b39b69e04c28cd92f6902513135e16e734c4e3194a9542**, timestamp 2026-10-04T11:57:48.567927Z
- `runs/dev_20261004_01/source_snapshot/`: frozen code/protocol copies
- `runs/dev_20261004_01/{raw.jsonl,raw.csv,results.json,summary.json}`: full primary outputs
- `runs/dev_20261004_01/{replay_raw.jsonl,verification.json}`: full selected replay outputs and artifact checks
- `runs/dev_20261004_01/{analyze_saved.py,analysis.json}`: separately identified post-freeze saved-output-only arithmetic audit

From the `vehicle_routing` directory, run preflight with `ortools_baseline_v1/.venv/bin/python -B -m unittest -v ortools_baseline_v1.test_adapter`. Runs refuse existing output directories and never replace prior primary observations. New runs require a separately identified development execution and coordinated timing window. No final holdout, credentials, desktop, paid API or Codex was used.
