# Fresh development scale/budget study, version 1

Fixed before this batch; earlier n=8/20/40 results are known. This is new
exploratory development work. No holdout is read, generated or used for choices.
Twenty-four fresh instances: uniform/clustered × 50/100/200 customers × 4
replicates. Instance seeds 2026100500..2026100523, solver seeds 11/29/47. The
unchanged original generator supplies coordinates/demands with capacity 30; a new
manifest wrapper accurately labels its new namespace. Existing inputs untouched.

## Three methods, two ceilings

Savings, corrected multistart VND and official PyVRP 0.14 ILS at S=10^6, paired
across 0.25 and 1.0 solver-CPU-second ceilings. Full worker wall deadlines are
1.0 and 3.0 seconds respectively and include process startup, imports, validation,
solve, serialization, teardown. 432 primary calls, then one full 432-call replay.
No method parallelism; coordinate CPU-sensitive windows with NAS and other work.
Host tenancy still not fully controlled.

VND retains 12 starts, but its move-evaluation safety ceiling rises from 100,000
to 10,000,000. PyVRP's iteration safety ceiling rises from 1,000 to 1,000,000.
These fixed changes permit the time ceilings to matter. This is a new
configuration, NOT a one-factor size comparison against the old experiments and
NOT new algorithm families. Work/iteration limits, local completion, CPU-margin
stops and process timeout must remain distinct. A budget is permission to compute,
not proof the algorithm actually used that amount; always show consumed CPU.

## Incumbents and matched return margins

A new MarginBudget preserves cpu_seconds=the declared ceiling. Its cooperative
check triggers 20 ms before that ceiling. The unchanged PyVRP callback subtracts
the same config value once; no reduced cpu_seconds is passed, so the margin is
not doubled. Both algorithms retain their best completed feasible incumbent.
VND never installs a partially scanned or partially applied candidate. PyVRP
returns its library incumbent on a stop callback. Initial model construction and
C++ local-search iterations cannot be interrupted by cooperative CPU checks;
initialization or one iteration may still overrun, which is recorded honestly.
A full worker wall timeout kills the process and records missing output/failure.
This is trusted-code process containment, not an adversarial security sandbox.

An independently feasible output is recorded as accepted even if it overran CPU.
It is scoreable only if solver CPU <= declared ceiling AND process wall <= its
ceiling. All-case feasibility/nonconformance rates remain in the report. Paired
quality requires all three seeds on both sides scoreable; list every excluded
base instance and the resulting pair count. Never hide difficult failures via
successful-only means. Budget comparisons use the same rule.

## Task and objective stay explicit

Original unrounded Euclidean scoring, exact integer capacity, required clients,
unlimited identical fleet implemented with n zero-fixed-cost vehicles, no duration
cost or reloads. PyVRP optimizes floor(10^6*d+0.5), rescales penalty min/max with
that factor, and reports both objectives and a route error bound. Independent
checker recomputes from original coordinates; integer proxy is never silently
scored as exact unrounded distance. At n=200 the worst theoretical rounding bound
is at most 0.0002 coordinate units plus float slack, not an optimality guarantee.
Pinned package/wheel hashes and license provenance are reused unchanged from the
mature study; binaries/venv/caches are excluded from deliverables.

## Freeze, tests and output retention

Preflight uses separate test seeds and includes: equal/non-doubled margin trigger,
mid-search VND incumbent preservation, PyVRP pre-first-callback incumbent,
50/100/200-customer checkpoint feasibility, complete-process accounting,
nonconformance visibility and explicit pair exclusions. Freeze source, imported
solver dependencies, package provenance, parameters, all new input hashes and
complete shuffled schedule before the first primary call. Old experimental
source and raw artifacts are hash-checked before/after.

Each primary and replay call saves complete output/routes as JSONL. Frozen source
snapshots, JSON/CSV records, full replay outcomes, and independent checks remain.
No failure retries, post-hoc primary replacement or overwrites. Budget-triggered
replays can differ even with the same seed; report route/cost differences and
separate replay aggregates. Fixed-work diagnostics may explain differences but
cannot replace timed observations or be counted as extra independent instances.

## Predeclared analysis and costs

At each ceiling: PyVRP vs multistart VND primary; VND vs savings secondary.
Within each method: 1.0 vs 0.25 ceiling. Mean over three seeds per base instance,
then equal-weight relative distance reductions over complete base-instance pairs,
with mean/median/range, wins/ties/losses and six family/size cells. All-case
failure and budget-conformance counts accompany every result. No p-values or
strong generalization conclusions from four instances per cell.

Report solver CPU, complete-child user+system CPU, supervisor CPU, total wall,
peak RSS, stopping reasons, paired quality and rounding checks. OS wait4 includes
child interpreter startup and exit, even killed children. Nonoverlapping parent
and child CPU are additive for the scoped batch loop; replay is separately
accounted. Setup/generation/freezing/tests/final artifact writing, later audits,
assistant/human/platform labor remain outside that batch clock, not free.

There is no experimental model API, paid call, trained selector or generated
member. This can improve the mature-baseline evidence at larger synthetic sizes;
it cannot establish H1/H2, final holdout performance or agricultural feasibility.
