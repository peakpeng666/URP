# Work-counter erratum, 2026-10-04

An independent review after the frozen run found a one-item generator look-ahead
in `descend`: Python computes/yields a candidate delta before `state.tick()`
checks whether the work limit has already been reached. Therefore the 15 capped
multistart calls compute **100,001 candidate deltas**, although `move_evaluations`
records **100,000 admitted comparisons**. The extra delta is not compared or
accepted. The original description of a strict 100,000 *computed-delta* limit is
incorrect for these 15 calls. The remaining 345 calls were not work-capped.

The frozen source, protocol and primary raw data have deliberately not been
rewritten. All original routes, distances, feasibility results and measured CPU
remain valid; CPU timing includes that extra computation. No CPU or wall ceiling
was reached. This defect does not justify suppressing or replacing any result.

A separate `../local_search_v2/` revision moves the work-limit guard before asking
the generator for another delta, adds an instrumented regression test, and reruns
the identical instance/seed/method schedule and budgets. It is a correctness
revision of the same methods, not an extra algorithm family or tuned configuration.
Consult that revision's separate raw data and verification before using its
numbers; v1 remains a historical, auditable run.
