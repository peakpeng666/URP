# Native CVRP supplement: AILS-II and SISR

This source-only supplement is a separate cohort, not a replacement for the frozen 17-configuration baseline. Original vendor sources and licenses remain alongside narrowly adapted source trees and auditable patches. See PREDECLARATION.md for fixed parameters, objective, timing and applicability limitations.

## Install location and prerequisites

Extract the archive in the existing cvrp_baseline project root, preserving the cohort_b/ directory. The original project must already contain src/research/src/urp_research/cvrplib/io.py, src/research/configs/cvrplib_cases.json and its exact hashed CVRPLIB input files. No pip packages beyond that project's environment are introduced.

Linux; Python 3; g++ with C++20 support; JDK 17 or newer with the jdk.compiler module. No sudo or system changes are needed. The JVM launch must be Java 17 or newer. Java source compilation explicitly targets release 17. Sources are portable; no compiled binaries or installed JDK are bundled.

## Build only in an approved idle timing window

    bash cohort_b/ails/build.sh
    bash cohort_b/sisr/build.sh

Do not re-run prepare_adapter.py after freezing: already adapted sources are included. Build scripts use those source files directly. Do not compile or test concurrently with a timed main cohort.

## Execute the assigned frozen rows

Local host, only after its main experiment batch is finished or an expressly coordinated stable window:

    python cohort_b/run_cohort.py --run --host-id local

Cloud host, only after its main seed-0 batch:

    python cohort_b/run_cohort.py --run --host-id cloud

The shared COHORT_FREEZE.json schedules exactly 120 rows: 24 cloud (seed 0) and 96 local (seeds 1–4), twelve unrestricted X instances, two vendors, five seconds per row. Local serial budget is about eight minutes plus process/checker overhead; cloud about two minutes. Do not launch the same host allocation twice concurrently. Source hashes are checked before execution; input hashes before every row. Each host records its own build fingerprints. Existing completed rows are skipped; an interrupted started row without a result requires reconciliation, not silent retry.

## Results and interpretation

formal-runs-local/ or formal-runs-cloud/ contains atomic per-row JSON, raw incumbent events, independent coverage/capacity/integer-cost checking, signed exit status, deadline and cleanup timestamps, and observer-checker CPU accounting. A feasible incumbent is not the same as clean termination: native errors remain explicitly labelled. Unexpected early cleanup kills remain distinct from deadline kills. Timing includes launch, native initialization and metric verification; synchronous incumbent verification can reduce available search time relative to the main cohort's post-check approach.

AILS keeps its upstream demand-derived route-search bound; SISR has no fixed-K search constraint. Both therefore enter only the standard-X-unlimited subset, never silently substituting unrestricted problems for the fixed-K A/B/E/F/P instances. Original temperature/iteration schedules and search logic are preserved. No BKS or reference routes enter workers. First technical failure and all subsequent smoke evidence remain under evidence/; these are not formal-quality measurements.
