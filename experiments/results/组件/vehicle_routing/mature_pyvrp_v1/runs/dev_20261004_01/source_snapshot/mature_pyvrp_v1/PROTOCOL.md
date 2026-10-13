# Pinned PyVRP development integration protocol, v1

Fixed before the development batch. Prior local-search development results are
known; this is an explicitly exploratory development comparison, not blind final
testing. PyVRP 0.14.0 was installed with user authorization from official PyPI in
an isolated project venv. Dependency versions, wheel URLs/hash digests, installed
PyVRP source/binary hashes, and license notices are recorded. The distributable
excludes the venv, vendor binaries and caches; the adapter copies no vendor code.

## Objective and fleet adaptation

The original contract stays unchanged: score the sum of original unrounded
Euclidean distances, with capacity-exact feasibility checked independently.
PyVRP optimizes an integer proxy: q(i,j)=floor(S*d(i,j)+0.5). Primary S=10^6;
S=10^9 is a separate sensitivity configuration, not another algorithm family.
For every output, independently sum integer edge costs and compare to the library,
then independently re-evaluate original coordinates. Store quantized objective,
original objective, signed discrepancy, edge count, maximum matrix edge error,
and route error bound. For m traversed edges, |C-Q/S| <= m*max_edge_error plus
floating summation slack. The analytic bound is m/(2S) plus floating-point slack;
since nonempty routes <= n, m=n+r<=2n. At n=40 the primary analytic bound is 4e-5
coordinate units. This is an objective-approximation bound, NOT a heuristic
optimality gap or proof of equivalent minimizers. Never score Q/S as exact C.

Clients are all required. Supply n vehicles (n customers), enough for every
feasible nonempty-route solution, with capacity Q, fixed cost zero, unit distance
cost one, unit duration cost zero, no reloads and depot zero. Thus no artificial
fleet shortage or vehicle-count priority is added. Client indexing in v0.14
excludes depot; map client activity idx k to original node k+1. Reject unknown
activity types. Empty instances are a documented zero-cost no-backend special
case in tests, not part of the 24-instance experiment.

PyVRP 0.14 uses iterated local search, NOT the older HGS implementation. Use its
default SolveParams except PenaltyParams min/max are respectively 0.1*S and
100000*S, so penalty bounds retain the same normalized cost units across scales.
Without this rescaling a large precision factor would silently change the
capacity-penalty behavior. Public library source and license are unmodified.

## Methods, budget and schedule

All 24 existing dev instances, seeds 11/29/47, seven configurations: the three
original constructors, corrected savings_vnd and multistart_vnd, primary PyVRP
and sensitivity PyVRP. Exactly 504 primary calls, one attempt each. Cases and
method order are shuffled by the frozen schedule seed. Two VND configurations
remain one family; two scales remain one PyVRP ILS family.

All methods receive the same 0.25-second cooperative solver CPU ceiling and
1-second full-worker wall deadline. For PyVRP, solver CPU includes model building,
quantization, solver initialization, ILS and extraction/recomputation. Package
imports happen before solver timing but are captured in complete-child wait4
CPU and total wall. Baselines use the SAME venv interpreter without importing
unused PyVRP, so their whole-process overhead is not artificially inflated.

PyVRP uses a fixed 1,000-iteration ceiling and a 5 ms solver-CPU return margin;
stop callbacks also observe a 50 ms solver-wall return margin. It may stop early
at either margin. Initial construction can occur before the first stop callback,
and a C++ iteration is not preempted by CPU checks: actual overshoot must be
reported, not hidden or called a strict OS CPU limit. The 1-second external wall
kill remains authoritative. The existing VND work ceiling remains 100,000 deltas
shared over all starts. Unused budget is not padded. No parallel methods or GPUs.
Coordinate timing-sensitive batches with the separate NAS experiment; the cloud
host is not dedicated, and other tenants are uncontrolled.

## Tests, freeze and verification

Before any dev batch, pass known micro optima, independent 5-customer exhaustive
oracle comparisons, activity-index coverage, forced singleton fleet, zero-demand
and coincident nodes, matrix rounding, overflow guards, penalty scales, iteration
replay, stop behavior and complete-process telemetry. These tests use other
synthetic seeds or existing unit fixtures, not final holdouts.

Freeze code (including imported trusted local-search source), protocol, lockfile,
dependency provenance, all 24 input hashes, old pilot hashes and full call order
before solving. Verify installed PyVRP file hashes before and after. Raw JSONL
flushes each call. Output directories and verification reports refuse overwrite.
Recheck every saved route with the independent checker and replay all calls.
Time-stopped runs may vary across replays; preserve and report such differences,
never silently replace a primary result. Preserve all old pilot and VND evidence.

## Analysis and cost boundaries

Primary: PyVRP S=10^6 vs corrected multistart VND. Secondary: S=10^9 vs S=10^6.
Aggregate three solver seeds to an instance mean, then report equally weighted
percent reductions across 24 base instances, medians, ranges, paired win/tie/loss
counts and six distribution/size groups. Baseline comparisons are retained as
cross-checks. Report failures and incomplete pairs explicitly, no infeasible cost
is scored. Report solver CPU, complete-child CPU, parent CPU, wall, peak RSS,
stop reasons, integer/unrounded discrepancy and scale sensitivity. Repeated seeds
and scale variants are not new independent tasks or families.

wait4 accounts for child start/import/validation/solve/serialization/exit, including
killed children. Batch CPU adds nonoverlapping parent and complete-child CPU.
Installation, tests, freezing, final aggregate writes, replays, analysis and
assistant/human/platform labor are outside the batch clock and must be described
separately, not assumed free. No experimental LLM or paid/model API is used.

This develops mature-solver integration on small synthetic CVRP only. It does not
establish that this limited budget/configuration is a universally strong library,
H1 stable complementarity, selector net benefit, H2 generated-member gain, final
holdout performance or agricultural/robot feasibility. P3/P5 remain planned.
