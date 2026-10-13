# Restricted mathematical DAG: handwritten prototype

This is a small teaching variant for score-function design. The only supplied
program is a JSON graph with eight fixed mathematical operations. The trusted
interpreter never evals, executes, imports or compiles candidate source. No
model-generated graphs or evolutionary search are authorized or included here.
It is not the paper's unrestricted Python search space or its GPT-3.5 backend.

## Fixed contract

`spec.json` gives all limits. `src/schema.py` is the closed admission/type checker;
`src/interpreter.py` is the fixed NumPy dispatcher. Constants are strong np.int32
or np.float64 scalars, not weak Python scalars. Integer operands are checked
inside ±1,000,000; wide intermediate arithmetic is safe inside int64 and rejects
out-of-domain results before narrowing. Vectors are exact 1-D NumPy arrays;
scalars are not zero-dimensional arrays. Arithmetic broadcasting is scalar to
same-length vector only. Integer array results stay int64. Floating results are
binary64. Boolean vectors can only feed `where`.

Every listed node executes once, including dead nodes and nodes after the selected
root. No folding, pruning, algebraic rewriting or exact-fit override occurs.
`where` consumes already evaluated branches. Thus dead-node edits can change
warnings/failure even if root scores are unchanged. Intermediate Inf/NaN are
permitted and counted over completed nodes; final scores must be a finite,
exact same-length float64 vector. First `argmax` wins ties. Warnings preserve
placement/node/emission order. Diagnostic overflow is unresolved; an unexpected
warning source is an infrastructure failure. No numerical failure is clipped,
repaired or silently replaced with another policy.

The published formula is represented by 15 nodes. Its 9 named intermediates are
compared bit-for-bit to the previously reviewed handwritten transcription, with
six extra subexpressions explicitly checked. These are transcription checks,
not an independent proof of all floating behavior and not author-byte execution.
The upstream author's Python file is never imported.

## Resource and trust boundary

Each worker is limited to 20 CPU seconds, 30 wall seconds plus 1 second cleanup,
2 GiB address space, zero file growth and 32 descriptors. stdout is capped at
400,000 bytes and stderr at 16,384 bytes, separately. Bounds are prospective:
RSS is measured, not claimed to be a hard total-process-tree limit. The handwritten
validation reserves full per-call limits within observed stage budgets of 90 CPU
and 120 wall seconds; final publication overhead is reported separately.

The JSON graph has no host API, callable, attribute, import, filesystem, network,
environment or arbitrary Python object surface. This property comes from the
closed data interpreter. The worker remains trusted native Python/NumPy code:
OS rlimits and this data language are not a general-purpose capability sandbox.
The old Wasm boundary is unchanged and is not replaced for Python candidates.

At most 64 nodes, 10,000 feasible capacities and 256 placements are permitted.
Every node is charged its vector length, including scalar/dead nodes, and every
placement also charges the complete preallocated-bin scan. The hard abstract
work budget is 5,000,000; maximum admitted packing is bounded by
256² × (64+1) = 4,259,840 charged units. Validation, diagnostic and trace scans
have bounded constant factors; these units are not an exact floating-operation
or CPU count.

## Handwritten validation

The planned launch comprises one bounded unit-suite worker, 19 numeric controls,
5 micro-packings, 3 rejection workers, 3 maximal-envelope workers and 7 transport
fault workers: 38 requests in total. All are fixed handwritten controls. The
formula-domain check covers 45,050 legal scalar-item/capacity pairs, plus named
boundary vectors. The host separately checks packing feasibility from original
items. It does not claim independent recomputation of every floating choice.

`prepare_freeze.py` performs static parse/hash inventory only, without NumPy or
formula imports. `manual_validation.py --freeze-sha256 DIGEST --output NEW_DIR
--run-reviewed-handwritten` is the explicit local safety acknowledgement after
review. A new output directory is required; failed invocations and evidence
remain. This entrypoint has no model backend or candidate population interface.
Any future generated-graph stage requires a separately reviewed immutable
population, prompt/model/template/seed/budget protocol and fresh authorization.
