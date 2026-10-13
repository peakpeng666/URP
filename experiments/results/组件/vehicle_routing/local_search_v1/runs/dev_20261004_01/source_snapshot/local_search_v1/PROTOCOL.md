# Frozen development local-search strengthening protocol

Version: feasible-vnd-v1. Status before execution: protocol fixed; no batch output
observed. Exactly the 24 existing dev instances are paired across five methods
and solver seeds 11/29/47 (360 calls). No final holdout is opened or generated.
The source and this protocol are frozen before the first batch solve. Tests use
separate synthetic and known micro instances; no tuning is done on batch results.

## Methods and meaning

Three original constructors are rerun with their unchanged source. `savings_vnd`
starts from parallel savings and uses best-improvement variable-neighborhood
descent in this order: intra-route 2-opt, intra/inter-route one-node relocate,
inter-route one-node swap, and inter-route tail exchange (2-opt*). An improvement
restarts at the first neighborhood; a full unsuccessful cycle certifies a local
optimum only in these declared neighborhoods. A complete candidate objective is
recomputed before each acceptance. Capacity remains feasible with exact integer
arithmetic; no penalty or vehicle-count objective is introduced.

`multistart_vnd` repeats the same local search from savings, nearest neighbor,
and ten seeded sweep starts. It is a second configuration of ONE search family,
not an independent algorithm family. Seed determines the ten sweep starts. Both
configurations share a limit of 100,000 feasible move-delta evaluations per call,
including all starts. An interrupted search returns the best complete feasible
incumbent observed so far; it does not declare local optimality. VND is original
standard-library code, not a reproduction of PyVRP or a novel generated member.

## Budgets, order, reproducibility

Every method gets the same 0.25-second cooperative solver CPU ceiling and a
1-second wall deadline covering interpreter start, imports, input validation,
solve, serialization, and teardown. A cooperative check can overshoot by the
cost of one unchecked operation; output packaging also costs CPU and is counted.
Every call's actual CPU and overshoot are recorded. Unused time is not padded.
No algorithm runs in parallel in this runner. Other tenants of this cloud host
are not controlled; single-thread environment variables are fixed.

All 72 instance/seed blocks are shuffled with the frozen schedule seed. Each
block shuffles method order using the same deterministic PRNG stream. Existing
constructors still ignore seeds where documented; these repeats are NOT extra
independent instances. Work-limit runs are deterministically replayable unless
the CPU/wall deadline interrupts first. Same-seed replay reports disagreements
rather than replacing any primary raw result.

## Validation, accounting, output retention

Independent legacy checker reads original coordinates and recomputes the
unrounded Euclidean objective. It does not import local-search helpers. Persisted
routes are checked again separately. Full old tests plus the new move-delta,
local-optimum, micro-oracle, incumbent, timeout, serialization and accounting
tests must pass before the batch. Intentional failures are unit tests, excluded
from empirical failure rates.

Linux `wait4` returns exact per-child user/system CPU and peak RSS for both normal
and killed children. This includes interpreter startup, unlike the original
pilot's worker-only CPU metric. Parent process CPU is measured separately; an
execution-phase sum can add these nonoverlapping values. Timing spans the batch
loop and raw JSONL writes, not source development, tests, analysis, freezing,
final aggregate serialization, later verification or human/model labor. Those
are not silently called free. No paid/model API, GPU, generation training or
selector is run. Timing is about this implementation and host, not asymptotic
solver efficiency. This wrapper is not an untrusted-code sandbox.

Raw JSONL is append-only and flushed after every call. The output directory must
be newly created. No overwrite/retry removes a failed result. Complete artifacts
include per-call JSON/CSV, source snapshots, input hashes, schedule, aggregate
summaries, and independent verification. Failures remain visible, paired quality
comparisons explicitly state complete-pair counts, and no infeasible solution is
scored. Earlier pilot results and data must retain their hashes.

## Analysis fixed before the batch

Primary comparison: savings_vnd versus parallel_savings. Compute mean cost over
three seed repeats per base instance, then relative distance reduction
100*(baseline-search)/baseline on each of 24 instances. Report equally weighted
mean, median, range, win/tie/loss counts and six family/size cells. Secondary:
multistart_vnd versus savings_vnd with the same aggregation. Positive reduction
means shorter routes. Timings and failures are reported separately. No trained
selector, free VBS as deployable policy, significance test or generalization
claim is made. Configurations do not establish H1 complementarity or H2 generated
member benefit. The mature-solver gate remains open.

## Sources and licensing

No third-party source code is copied into this extension; existing URP helpers
are imported unchanged. Standard algorithmic ideas are independently implemented.
No external solver has been installed. The candidate mature dependency is
PyVRP 0.14.0, official PyPI https://pypi.org/project/pyvrp/0.14.0/ and official
source https://github.com/PyVRP/PyVRP, MIT license as declared by PyPI. Installation
and running it require separate authorization. Current releases use iterated
local search; the historical HGS paper is not proof that this version is HGS.
