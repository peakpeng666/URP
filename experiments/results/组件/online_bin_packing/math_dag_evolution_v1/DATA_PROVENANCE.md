# Fixed data panel: 4 design + 4 validation cases

This is prospective **data-only preparation** for the restricted mathematical-DAG teaching experiment. No candidate, baseline, DAG interpreter, model, NumPy, or upstream program was executed. Only JSON/text reads, byte hashes, exact integer-list comparisons, and artifact writes were used. Existing source files were not changed.

## Frozen choice and entry points

Use the first 128 items, preserving their order, from these zero-based source indices. Cross **each** sequence with capacities 100 and 500:

| Split | Source set | Source index | Full length | Slice |
|---|---|---:|---:|---|
| Design | historical_design_5k | 0 | 5000 | [0:128] |
| Design | historical_design_5k | 1 | 5000 | [0:128] |
| Validation | test_dataset_1k | 0 | 1000 | [0:128] |
| Validation | test_dataset_5k | 0 | 5000 | [0:128] |

These indices and the 128-item prefix length were chosen deterministically from source order before candidate generation/scoring, with no random search, shuffling, outcome inspection, or score-based choice. Items are exact integers in 1..100; each case has 128 items, below the 256-item bound. This is **two distinct item sequences per split**, with two capacity conditions per sequence, not four independent sequences.

- `data/design.json`: four design cases only; the generation/selection entry point
- `data/validation.json`: four validation cases only; load after committing both arm winners from design results
- `data/panel.json`: combined audit/review artifact; not a selector input
- `data/panel_overlap_audit.json`: independent comparisons and inventory
- `data/panel.sha256`: exact combined-panel byte checksum

The split files reproduce the combined cases exactly. Validation is reserved for the **two precommitted arm winners and three fixed comparators**. Do not use validation items, traces, failures, or scores to generate, repair, rank, or reselect candidates. File separation reduces accidental leakage; it is not a security boundary, and all underlying data are public.

## Why paired capacities

Giving one validation sequence capacity 100 and another capacity 500 would confound item-sequence identity with capacity. Crossing both sequences with both capacities allows within-sequence capacity comparisons and ensures the design and validation panels both cover both conditions. Report paired per-case differences and capacity-stratified summaries; do not treat the eight cases as eight independent sequences.

The cost is four rather than three design evaluations per candidate (+1/3), and four rather than two validation evaluations per winner (2x). The gross ceiling supplied for this protocol is **22 x 4 + 2 x 4 + 3 x 8 = 120 score-request slots**, with no reuse across distinct generated records, including duplicate graphs. The same FF/BF design observations serve both seed and comparator roles and are counted once. Winner-role validation is separately planned even when two roles choose an identical graph, with no best-of-repetition selection. This note neither performs nor authorizes those evaluations. A full pass over eight cases is 60% more work than over five; the tiny crossed panel is justified by removing an avoidable confound, not by greater statistical power.

## Original sources and capacity semantics

The item source is the pinned [EoH repository commit e4b5ddba03b2b88025747e11c6049f8b529a4368](https://github.com/FeiLiu36/EoH/tree/e4b5ddba03b2b88025747e11c6049f8b529a4368), dated 2024-07-27. The direct numeric input is the previously prepared `../paper_baseline_v1/data/historical_numeric.json`. Its item-list hashes were independently checked against `historical_data_audit.json`. All nine original historical-source files were rechecked against their recorded SHA-256 and Git blob SHA-1 values; binary pickle files were **only byte-hashed**, never deserialized.

- Design: [`eoh/src/eoh/problems/optimization/bp_online/get_instance.py`](https://github.com/FeiLiu36/EoH/blob/e4b5ddba03b2b88025747e11c6049f8b529a4368/eoh/src/eoh/problems/optimization/bp_online/get_instance.py), embedded `test_0`/`test_1`, both literal capacity 100
- Validation: [`test_dataset_1k.pkl`](https://github.com/FeiLiu36/EoH/blob/e4b5ddba03b2b88025747e11c6049f8b529a4368/examples/bp_online/evaluation/testingdata/test_dataset_1k.pkl) and [`test_dataset_5k.pkl`](https://github.com/FeiLiu36/EoH/blob/e4b5ddba03b2b88025747e11c6049f8b529a4368/examples/bp_online/evaluation/testingdata/test_dataset_5k.pkl), first stored sequence from each
- The pickles store item counts and item sequences, **not capacity**. The historical [evaluation loader](https://github.com/FeiLiu36/EoH/blob/e4b5ddba03b2b88025747e11c6049f8b529a4368/examples/bp_online/evaluation/get_instance.py) assigns default capacity 100; its `get_instances` loop mistakenly changes only the first instance because it loops over the outer dataset count. This panel assigns each requested capacity to every case and every bin
- At capacity 500 the absolute integer items are unchanged. This is an explicit capacity reassignment; item sizes are not multiplied or normalized
- The historical embedded evaluation copy has a literal capacity 1000 on its first instance, but contains the same item sequences as the design source. It is an alias used only in overlap checks, not the selected capacity source
- The historical [generator text](https://github.com/FeiLiu36/EoH/blob/e4b5ddba03b2b88025747e11c6049f8b529a4368/examples/bp_online/evaluation/testingdata/generate_instances.py) describes Weibull shape 3, scale 45, clipped to 1..100 and rounded. No seed is asserted, and this text does not prove which random realization produced every stored sequence

Each case preserves the source commit, URL, file SHA-256, Git blob SHA-1, full-sequence ID/index/length, original item dtype, raw capacity (null when absent), loader default capacity, full-list hashes, prefix boundaries, prefix hashes, and typed-item hashes. The test sequence's original dtype is little-endian signed int32; the numeric JSON contains exact Python integers. Type-tagged hashes distinguish this conversion explicitly, without importing NumPy. Full definitions are in `panel.json`; the ordered numeric-list hash matches the earlier audit convention. Dependencies use exact byte hashes and relative paths rooted at this experiment.

## Independently checked overlap and limitations

The new audit reads all **50 full sequences from 10 sets**: all five historical sets and all five current sets in `paper_baseline_v1`. It independently checks all 1,225 existing-sequence pairs plus all 200 selected-prefix/existing-sequence pairs, using exact full-sequence equality, whole-shorter-prefix equality, and 128-item-prefix equality. The existing audit's conclusions are not used as substitutes for these comparisons.

- No exact or 128-prefix overlap between the four chosen distinct sequences, including across design and validation
- Four intentional equal-item case pairs, one for each sequence reused at two capacities
- Fifteen full-sequence alias pairs among historical design, historical embedded evaluation, and current embedded design, with matching original indices; no additional 128-prefix-only matches and no whole-shorter-prefix-only matches
- Every chosen prefix necessarily matches its original source sequence; the design prefixes also match both embedded aliases

The validation set is held out **only from this prospective selection protocol**. These are public, reused historical data, and source arrays may already have been exposed to prior work or model training. No equality/prefix test establishes statistical independence or absence of contamination. Truncating 1,000/5,000-item sequences to 128 changes horizon and bin-opening/ending effects. This panel supports a bounded teaching experiment, not a full-scale EoH reproduction or a strong generalization claim. No policy scores, lower-bound scores, or performance outcomes were computed during preparation.
