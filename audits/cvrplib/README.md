# Independent CVRPLIB data/source audit

Run from repository root:

    python audits/cvrplib/independent_data_audit.py
    python -m unittest discover -s audits/cvrplib -p 'test_independent_data_audit.py' -v

The script is standard-library-only and imports no solver, runner, distance matrix, or recovered validation implementation. The audit independently parses actual nodes, depot, demand and DIMENSION; checks exact once-only customer coverage, all route loads, and exact rational nearest-integer EUC_2D edge sums. It rejects unsupported edge types and ambiguous node mappings. All 53 original VRPs have depot 1, contiguous node IDs; reference SOL IDs are explicitly interpreted as original ID minus one.

Results: all 100 original files (53 VRP + 47 SOL) match the pinned commit f110f039854f7314e36632ce7d3ee977cd0de0fc manifest byte counts and SHA-256. Six added SOLs match the independently preserved preparation provenance hashes. All 53 reference solutions pass coverage, capacity, cost and declared fleet checks. No reference was repaired, substituted or optimized.

The historical SOURCE_MANIFEST.json is preserved byte-for-byte. ADDITIONAL_SIX_SOURCE.json is separate, copied unchanged from the preparation ZIP; it intentionally retains its historical pending-validation status. The new additional_six_validation.json and independent_data_audit.json are the validation receipts, not a rewrite of historical provenance. Exact official URLs and fetch timestamps for all six are in that source file.

Fleet contract evidence: Uchoa et al., New Benchmark Instances for the Capacitated Vehicle Routing Problem, https://optimization-online.org/wp-content/uploads/2014/10/4597.pdf . Pages 2–4 document rounded-distance fixed-route ABEFMP conventions and name semantics. Independently, every one of this dataset's 41 non-X cases has ceil(total demand/capacity)=K and a feasible K-route reference. Thus the imposed <=K contract is mathematically equivalent to exact K for these particular data, not assumed from filenames alone. Historical small16 frozen TASKS/PROTOCOL are preserved and give the same K_ref. Section 3.3.2, pp.15–16, explicitly does not fix route count for X; name K is only a lower bound, never an upper cap. Fixed vehicle cost is zero and distance is the sole objective.

There are 53 capacity/fleet cases, 51 normalized coordinate-demand bases. Base fingerprints preserve depot role, exact normalized coordinates and customer-demand multiset but intentionally exclude capacity, fleet and node labeling. The only two shared-base pairs are E-n51-k5/P-n51-k10 and E-n76-k7/P-n76-k4. These are different optimization cases and must remain in the same split to prevent base leakage. Customer counts parsed from DIMENSION range 18–523.

Empirical descriptors report coordinate bounds, demand min/max/mean/population standard deviation and distinct customer locations. These are measurements only, not claims of clustered/random generator labels. Reference validation is not an optimality proof or a claim that an archived reference remains the latest BKS; gaps should be labeled against the pinned validated reference.

Seven deterministic tests exercise half-up rounding, the boundary on either side of a half, large exact values, Euclidean rather than Manhattan distance, negative coordinates, and per-edge rather than final-total rounding. The reusable recovered checker and its rejection/runner tests are separate from this independent source audit.
