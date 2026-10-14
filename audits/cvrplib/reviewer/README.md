# Independent adversarial review

From the delivery/repository root:

    PYTHONPATH=src/research/src python -m unittest discover -s audits/cvrplib/reviewer -p test_adversarial_review.py -v

These 15 review tests use invented numerical fixtures and intentionally faulty tiny workers only. They do not run a public benchmark batch. The saved-score fixture is constructed evidence for testing validation, never a research result.

adversarial_after.log records all 15 passing against the repaired delivery. Individual process records are in logs/. recovered_adversarial_before.log is the initial 7-probe run against the immutable recovered handoff, showing 5 passed and 2 genuine defects: a malformed error event crashed the supervisor, and a worker self-SIGKILL after done was incorrectly accepted as OK. These failures are preserved rather than overwritten by the repair.

The final policy rejects the entire run if any submitted checkpoint violates integrity, retains crashes despite earlier feasible checkpoints, and distinguishes INVALID_SOLUTION/NO_SOLUTION from a mathematical infeasibility proof. Timing tests reject both late delivery with a backdated timestamp and future timestamps. Saved-score tests reject inconsistent input/payload identity and missing/late receipt evidence.

pyvrp_archive_member_comparison.json independently compares six frozen source/protocol members with the original strong-baseline ZIP, rather than only trusting the recovered source manifest. The original VND archive and all ten selected members have also been independently checked; see the [current VND verification](../vnd_original/当前核验.md).

## Fixture revision after a root regression failure

A later 99-test core rerun returned TIMEOUT_NO_SOLUTION instead of the injected malformed-output API_ERROR under the original 0.2-second fixture budget. Its exact child stage was not saved, so startup/scheduler delay is a plausible explanation, not a proven trace. See root_regression_pre_fixture_fix.log. The flaw is that a semantic error test assumed its worker would emit before the short deadline.

Reviewer semantic probes now have 2 seconds to reach their intended assertions. The dedicated delayed-delivery probe uses a 2-second deadline and a 3-second delay, and requires an observed READY_FOR_DELAY marker before accepting the test as exercised. Production deadline/receipt rules are unchanged. All 15 pass in adversarial_fixture_v2.log; raw records are in logs_fixture_v2/. Earlier logs/ and passing/failing transcripts are preserved. Core test changes and subsequent 99-test reruns are recorded separately in acceptance/20261014T085915Z-test-hardening/.

## Preserved independent contract evidence

[contract_findings.md](contract_findings.md) and [nonx_capacity_lowerbounds.json](nonx_capacity_lowerbounds.json) are the original independent contract review and its 41-case demand/capacity lower-bound calculation. They were relocated here without changing bytes. The original review text's historical `review/nonx_capacity_lowerbounds.json` reference refers to the companion file now linked here; its preparation-time limitations are not the current acceptance status. Use the [current CVRPLIB entrypoint](../../../experiments/CVRPLIB入口.md) for current status.
