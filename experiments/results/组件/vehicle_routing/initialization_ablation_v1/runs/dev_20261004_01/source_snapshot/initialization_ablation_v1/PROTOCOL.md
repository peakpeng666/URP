# Exploratory initialization ablation: PyVRP random vs savings warm-start

Motivation, fixed before this batch: the completed scale/budget development
study showed PyVRP default initialization losing to savings-initialized VND on
four uniform n200 base instances at 0.25 s, with ranking reversing at 1 s.
This follow-up is explicitly motivated by those observations, not an independent
confirmation or a final-test study. Reuse the exact 24 frozen scale-study inputs
and their hashes; do not generate new instances or touch holdouts.

## Two configurations of one public solver

Official pinned PyVRP 0.14.0 ILS, distance scale 10^6, default algorithm parameters
except the already declared scale-adjusted penalty bounds. Two arms:

1. `pyvrp_ils_random`: initial_solution=None, using library default random
   initialization and its normal initialization search
2. `pyvrp_ils_savings_warm`: build the unchanged savings solution, independently
   verify it with the original-coordinate checker, convert original customer
   node k to zero-based PyVRP client k-1, and supply it as a public Solution

Both use public Model.data(), Solution(data, list_of_client_index_lists) and
pyvrp.solve(..., initial_solution=...). No private or upstream internals are
patched. Fixed-work unit regressions compare the new random dispatcher against
the previous public Model.solve path to rule out incidental behavior changes.

Pair solver seeds 11/29/47, but do not claim identical subsequent random streams:
random initialization consumes RNG values and performs initialization search,
whereas the warm-start path skips that work. The ablation measures the complete
initialization-mode choice, including resulting trajectories and overhead; it
does not isolate only the geometric quality of the initial route. These are
configurations of the SAME family, not two novel methods.

## Budget and charging

Same 0.25/1.0 s declared solver CPU ceilings, 1/3 s complete-worker wall ceilings,
20 ms common internal CPU return margin, and 1,000,000 ILS iteration safety cap
as the scale study. Six instance/seed/budget blocks per instance, two methods,
for exactly 288 primary calls and 288 full-output replays. Shuffle blocks and
method order with the frozen schedule seed. Coordinate timing windows with
other work; methods remain sequential and single-threaded.

Savings construction, independent warm validation, model building, conversion
to library Solution, ILS and output recomputation ALL occur inside solver CPU.
Record warm construction/validation CPU as subphases; never add them again to
solver CPU totals. Import overhead remains in complete-child wait4 CPU and wall.
If construction cannot finish within the cooperative cap, retain the failure;
do not fabricate a valid warm start. Model/initial search can overrun a callback
boundary; record actual ceiling nonconformance and preserve any returned routes.

Every accepted warm incumbent must have integer proxy cost no worse than its
validated initial solution. A zero-iteration warm solve must return that feasible
initial incumbent. The final original Euclidean cost is independently checked;
integer non-worsening does not imply exact original-objective non-worsening
below the explicit quantization bound. Warm-start routes and both costs are
saved in every warm record, including replay. Invalid warm starts are rejected
before entering the library.

## Integrity and comparison

Preserve the unlimited-fleet equivalent n zero-fixed-cost vehicles, required
clients, exact capacity, no duration/reload objective and distance/penalty scales.
The existing adapter integer-overflow guards and original-coordinate checker
remain. Freeze protocol/source/dependency hashes/24 input hashes/full order before
primary calls; retain original studies unchanged. New raw, CSV and full replay
JSONL are append-only and never replace old observations.

Accepted means independently feasible/cost-consistent. In-budget scoreable adds
actual solver CPU <= declared ceiling and complete-process wall <= declared wall.
Report all-case success and nonconformance rates, then explicitly enumerate
complete base-instance pairs used in quality comparisons. No silent exclusion of
hard cases. Time-stopped replays may differ; keep their full outputs and separate
aggregates rather than forcing exact reproducibility.

Primary: warm versus random separately at each ceiling, mean over three seeds
per base instance, then equal-weight percent reductions over 24 complete pairs,
with median/range, wins/ties/losses and six family/size cells. Secondary: 1 s vs
0.25 s within each initialization. A comparison to the previously saved VND
quality is historical context only, not a contemporaneous runtime comparison.
Pay special attention to whether all four prior n200 reversals persist; this
question is explicitly chosen after the earlier development result.

No significance/generalization/selector/H1/H2 claim follows from these 24 reused
instances. If the result is informative, independent fresh-development replication
must be separately frozen before feedback. No experimental LLM/API generation,
paid calls, final holdout or agricultural feasibility experiment occurs here.

Report batch and replay CPU/wall separately, with parent plus complete child CPU
nonoverlapping and additive. Installation/tests/freezing/final writes/analysis,
independent reviewer and assistant/human/platform costs lie outside that scope
and are not assumed free. Binaries/venv/cache are excluded from deliverables.
