# Fresh targeted initialization-policy development replication

This protocol is motivated by the completed and independently reviewed
initialization ablation. It is frozen before generating or inspecting these fresh
instances, and before any outcome is observed. It does not hunt for positive H 1,
claim independent algorithm families, or consume formal final holdouts.

## New data and unchanged methods

20 new n 200 instances: 10 uniform, then 10 clustered, generation seeds
2026100800..2026100819. Same existing generator, coordinate/demand laws and
capacity 30. A separate data_plan_freeze.json records generation fields and
source hashes before generation. No prior instance is replaced or reused as a
fresh case. Five paired solver seeds:11,29,47,71,97.

Three unchanged reviewed configurations: corrected multistart VND, PyVRP default
random initialization, and PyVRP savings warm-start. Reuse the exact accepted
initialization adapter and runtime; no solver code/parameter changes based on
fresh outcomes. VND retains 12 starts and 10 million-delta safety cap; PyVRP retains
1 million-iteration safety cap, scale 10^6 and scaled penalty bounds. Both CPU
ceilings 0.25/1.0 s retain 20 ms internal return margins; complete-worker wall caps
1/3 s. Warm construction, independent check and conversion stay inside solver CPU.
This tests end-to-end initialization policies, including skipped initial library
search and changed RNG consumption, not pure initial-route geometry.

Exactly 20 instances×5 seeds×3 methods×2 budgets=600 primary calls. Shuffle paired
instance/seed/budget blocks and method order with the frozen schedule seed.
Run methods sequentially and coordinate other CPU-sensitive work; whole-host
isolation is not claimed. Preserve all failures, overrun measurements and full
outputs. Independently feasible output is accepted; scoreability additionally
requires actual solver/process times within the declared ceilings. Report both
all-case counts and every incomplete/excluded base-instance pair.

## Predeclared limited replay, not double compute by default

Manifest index modulo 5 chooses a single replay solver seed for each instance.
Replay all three methods and both budgets for that chosen instance/seed pair:
20×3×2=120 timed calls. Thus every base instance appears and each solver seed is
selected for four instances, twice per distribution. Record exact primary call
indices before any primary solve. Do not choose replays based on errors, winners
or interesting outcomes. Save every selected replay's full routes/output.

The replay diagnoses paired timed-call variation only. It is NOT a second
five-seed primary aggregate and cannot establish exact repeatability of the 480
unreplayed calls. Recheck all 600 saved primary solutions regardless of replay
selection, including original-coordinate feasibility and integer/rounding checks.

Additionally predeclare 8 cheap fixed-work diagnostics: first generated instance
of each distribution×two PyVRP initialization modes×two repeats, solver seed 11,
100 ILS iterations,5 sCPU and 10 swall. Compare each of four repeated pairs for exact
routes/cost and completed iteration count. Keep these roomy-budget fixed-work
calls out of primary comparisons and separately record their cost. They check
seed/work determinism without pretending timed-stop determinism.

## Analysis and scientific stopping condition

At each CPU ceiling compare warm vs random, random vs VND and warm vs VND.
Average 5 solver seeds per base instance, then equally weight the 20 base instances,
reporting mean/median/range, wins/ties/losses and separate 10-instance distribution
cells. Secondary:1 s vs 0.25 s within each configuration. Any excluded pair and
all-case failure/nonconformance rate must be visible. Distinguish the previously
identified uniform-n 200 mechanism from the clustered stratum; no outcome-driven
change of thresholds, seeds, configurations or claimed family counts.

The goal is to learn whether the earlier observed initialization-related
crossover replicates under the same synthetic task definition with new seeds.
Weak, negative or heterogeneous results are valid and are retained. This is
fresh development evidence, not a preregistered formal final test, real-world
routing validation, selector benefit, generated-member benefit or H 1/H 2 proof.
Stop this batch after its 600 primary+120 selected replay+8 diagnostic calls; any
further change requires a separately stated scientific purpose/protocol.

## Integrity, objectives and costs

Preserve unrounded Euclidean scoring via independent checker, exact integer
capacity, all required clients, n available zero-fixed-cost vehicles, no duration
cost/reloads. PyVRP integer proxy and original-coordinate score are stored
separately with rounding bounds. Every warm start is independently checked and
its integer-cost incumbent bound retained. Official PyVRP 0.14.0 and dependency
wheel/source hashes remain pinned; binaries/venv/caches are not delivered.

Freeze all new inputs, source/dependency hashes, old artifact hashes, schedule,
selected replays and fixed-work diagnostics before primary solving. Original
studies remain unchanged. No overwritten raw or replacement primary outputs.

Report consumed solver CPU, complete-child wait 4 CPU including interpreter
startup/import/exit, parent CPU, process and batch wall, memory and stop reasons.
Warm subphase CPU is a subset of solver CPU, not additive again. Primary, selected
replays and fixed-work diagnostics have separate accounting. Setup/generation,
tests/freezing/final writes/analysis/reviewer and assistant/human/platform costs
are outside those clocks and are not free. No experimental model API or paid
calls, no final holdout access, no agricultural-constraint claim.
