# Prospective handwritten test matrix

Status: source-only preparation. This worker has not imported the interpreter or
NumPy, parsed the fixtures with Python, compiled Python, run tests, run a formula,
made a model/backend call, or generated an algorithm candidate. Expected outcomes
are specifications and source-derived assertions, not measurements.

`test_handwritten_controls.py` now targets the reviewed source-only API:

- `schema.validate_program(raw: bytes) -> Program`; controlled `StructureError`
- `interpreter.evaluate(program, item, bins, work, warnings, placement, trace)`
- `interpreter.pack(program, items, capacity, work, warnings)`
- `WorkBudget`, `WarningLog`, and the explicit domain/numerical/resource exceptions

Do not run the file merely because it exists. Numerical execution remains deferred
until the coordinator confirms the other model-smoke process and its cleanup have
finished, completes static review, and authorizes the bounded execution window.
Every eventual numerical run must retain the existing 20-second CPU,
30-second wall plus 1-second cleanup, and 2-GiB memory limits. No test runner may
silently replace those limits or consume formal research evaluation slots.

## Coverage

1. Strict bytes-only JSON admission
   - Exact top-level keys; unknown, reflection-like, and dynamic-call keys
   - Duplicate keys both at top level and in constant objects
   - NaN/Infinity literals, exponent overflow, large integers, invalid UTF-8
   - Nested input below the raw byte cap must yield controlled rejection
   - 32,768-byte inclusive raw bound; 32,769 rejected before parse
   - UTF-8 byte counts instead of character counts
   - 1,024-byte one-line description boundary and control-character rejection
   - 16/17 constants, 64/65 nodes, and valid zero-constant control

2. Closed type and reference rules
   - `i32` exact integers; `f64` integer or float JSON values; no booleans
   - Constant magnitude endpoints and immediately outside the bound
   - Bad containers, unhashable type names, missing and extra fields
   - Correct arity for every allowed operation family
   - Self, forward, negative, bool, float, object, and expression references
   - Canonical `c0`.. names, missing constants, and huge reference strings
   - `gt` needs numeric operands with at least one vector
   - `where` needs VB condition and F64 scalar/vector branches
   - Wrong scalar/vector, bool, integer, and unknown-operation roots rejected
   - Dead/unreachable malformed nodes are still rejected
   - Frozen tuple-backed program and distinct raw/canonical source identities

3. Handwritten numerical controls, once separately permitted
   - Strong typed scalar and vector promotion, including f64 JSON integer values
   - Mixed scalar/vector `where` branches in both orders, scalar-left `gt`, mixed
     vector/vector `gt`, and f64-scalar-left add/sub/mul/div against int64 vectors
   - Inclusive positive/negative 1,000,000 integer bounds
   - +/-1 boundary violations; widened 1,000,000 squared before narrowing
   - One violating vector element fails the complete evaluation
   - Dead nodes and rows after the selected root still execute
   - Unselected `where` branch executes; a shared node executes exactly once
   - Repeated warnings remain ordered by placement and node with no deduplication
   - Intermediate NaN/Inf classifications differ from final nonfinite rejection
   - Finite-root recovery after a permitted infinite intermediate
   - Input shape/dtype/domain checks, 10,000/10,001 vector lengths
   - Input arrays remain byte-identical, including reversed/noncontiguous views
   - Trusted trace classifies dtypes, shape, NaN, and signed infinities
   - Wrong dtype/shape from an internal operation becomes a contract fault

4. Fixed published formula parity, once separately permitted
   - Exactly 15 operations and 5 constants, including a scalar int32 multiply
   - Verify the frozen handwritten formula source SHA256 before importing it;
     compare nine named graph intermediates bit-for-bit with that sibling module
   - Compare the six unnamed operations with direct handwritten NumPy expressions
     using strong scalar constants; this is scoped transcription checking, not
     independent numerical proof
   - Retain the four fixed vectors and add exactly 100 full item-domain vectors
     `arange(item, 501, dtype=int64)`, covering 45,050 domain pairs and checking the
     source-derived total of 9,550 positive-infinite denominators
   - Check input dtype, shape, and bytes remain unchanged after both implementations
   - Fill module-level `EVIDENCE` with exactly 100 bounded rows: item, length,
     final-score SHA256, denominator infinity count, warning nodes, and a combined
     hash of all 15 values. The hash frames each dtype, shape, byte length, and raw
     bytes with delimiters. Never serialize intermediate arrays in this evidence
   - Never execute or import the upstream author file
   - Compare warning messages separately because the implementations have different
     source filenames/line numbers
   - Source-derived item=1, bins=[1,5] must choose index 1; no exact-fit override
   - Exact fit, strict `diff > 3*item` at either side and at equality
   - Denominator diff=354 finite; diff=355 positive infinity with warning at node
     12; the downstream quotient is positive zero and the root remains finite
   - Record any bitwise discrepancy without adding a tolerance or changing the
     formula. This is handwritten-transcription parity, not author-byte execution

5. Resources, placements, and diagnostics
   - Budget accepts at most 5,000,000 units; exact bound succeeds, next unit fails
   - Every node costs the current vector length, including scalar/dead nodes
   - Maximum 64-node by 10,000-vector control costs 640,000 units
   - Maximum 64-node, 256-placement all-feasible packing costs exactly 4,259,840
     units including scans, with a directly checked feasible complete assignment
   - Budget failure happens before the unpaid node executes
   - Packing additionally charges all preallocated bins on every feasibility scan
   - Empty packing, stable first-maximum ties, exact-fill feasibility removal,
     256 accepted placements, and 257 rejected before work
   - Small complete assignments/residuals and analytically known work counts
   - Warning event/kind/text overflow is explicit, marks evidence incomplete,
     and restores the original Python warning state
   - The default 12,000-event bound is exercised without overriding it: 63 scalar
     warning nodes per placement retain exactly 12,000 events, fail at placement
     190/node 30, and never return packing success or evaluate that placement's root
   - An unexpected warning source/category produces `UnexpectedWarning`

## Expected external status mapping

The unit tests inspect trusted return values and exceptions. Worker/supervisor
integration must separately confirm the bounded external statuses below and must
not serialize raw NumPy arrays, Python objects, NaN, or Infinity into JSON:

| Condition | Expected external status |
|---|---|
| Strict admission/type failure | `structural_rejected` |
| Item/bin/placement/capacity domain failure | `input_rejected` |
| Integer bound violation or nonfinite final root | `numeric_invalid` |
| Work exhaustion or memory/resource exhaustion | `resource_unresolved` |
| Diagnostic overflow only | `diagnostic_unresolved` |
| Unexpected warning, internal wrong shape/dtype, or transport fault | `infrastructure_failure` |
| Finite evaluation | `completed_finite` |
| Worker returned packing data | `packing_returned` |

`packing_returned` is not end-to-end packing success. A separate independent host
check of the complete assignment, residuals, capacity constraints, and reported
counts is an additional mandatory success gate.

Integration review must also cover truncated/malformed worker output, duplicate or
nonfinite JSON fields, worker exit versus reported status consistency, stdout and
stderr bounds, CPU/wall/memory enforcement, process-group cleanup, and unchanged
source hash binding. Use deterministic fault-injection hooks only if explicitly
provided by the reviewed trusted runner; do not add arbitrary code execution,
unbounded loops, dynamic imports from candidate data, or model calls to test them.

No claims of process isolation, production safety, algorithm quality, or research
success follow from source preparation or a passing unit suite. The math-DAG
interpreter is a restricted teaching interface, not a general Python sandbox.
