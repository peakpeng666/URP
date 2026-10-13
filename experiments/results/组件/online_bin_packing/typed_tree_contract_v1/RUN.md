# Prepared four-slot interface pilot

No inference has been authorized or run by preparation. Current source is isolated from old freezes. Use the frozen Python executable; set PYTHONDONTWRITEBYTECODE=1.

Verify only (zero model or scoring worker calls):

    python run_pilot.py --freeze-sha256 SHA256_OF_FINAL_FREEZE

After explicit approval only, write an approval file outside this frozen directory containing:

    {"authorized":true,"scope":"typed_tree_contract4_once","freeze_sha256":"SHA256_OF_FINAL_FREEZE","run_id":"typed_tree_pilot_01"}

Then, from this directory:

    PYTHONDONTWRITEBYTECODE=1 python launch_approved.py --freeze-sha256 SHA256_OF_FINAL_FREEZE --approval /tmp/typed_tree_approval.json

This uses the existing local server/HTTP/reaping implementation and existing isolated math worker. Maximum four fixed requests, three fixed diagnostic vectors per admitted tree, no retries, historical packing or selection. Raw model tree and compiled DAG are both retained. Type/compiler/transport/integrity/unknown cleanup failure stops subsequent slots. Numeric-invalid observations remain outcomes. Model budget reservation245CPU/131wall and scoring20CPU/31wall are conservative unchanged guards; overall cap1200CPU/900wall includes100/100 preparation debit and40/40 final reservation. A slot may remain not_run if the remaining budget is insufficient.

The saved outer accounting includes child cleanup and driver final report. Excludes the tiny outer accounting write itself; the40/40 final margin is not a claim to have directly measured every bookkeeping instruction. There is no kernel-wide process-tree CPU cap. Lifecycle termination begins at118 seconds; observed>120 is failure, not a hard OS scheduling guarantee.

Scope: type-contract usability. Depth2 cannot represent the original EoH formula. No claim about algorithm quality or original-paper reproduction.
