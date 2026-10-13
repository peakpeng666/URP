import test from 'node:test';
import assert from 'node:assert/strict';
import { ReplayEngine, ReplayComparison, ReplayDataError } from '../core/replay.mjs';

// This deliberately small, sparse fixture is test-only and never exported to public/data.
function fixture({ assignment = [4, 1, 4, 1, 5, 4], instanceId = 'test-stream' } = {}) {
  const items = [40, 70, 20, 30, 90, 40];
  const remaining = Array(6).fill(100);
  const used = new Set();
  const pre = [], post = [], feasible = [], bins = [];
  for (let i = 0; i < items.length; i += 1) {
    feasible.push(remaining.filter((r) => r >= items[i]).length);
    pre.push(remaining[assignment[i]]);
    remaining[assignment[i]] -= items[i];
    post.push(remaining[assignment[i]]);
    used.add(assignment[i]);
    bins.push(used.size);
  }
  return {
    schema_version: 1, run_id: 'test-stream__SELECTOR', instance_id: instanceId, policy: 'SELECTOR',
    capacity: 100, selector_consumed_count: 3, items, assignment, remaining,
    pre_remaining: pre, post_remaining: post, feasible_counts: feasible, used_bins_after: bins,
    branch: 'BF', prefix_features: [1, 2],
    decision: { features: [1, 2], neighbors: [0], squared_distances: [0.5], predicted_final_bins: [3, 4], selected_index: 0, final_outcome: 'must not leak' },
  };
}

function independentState(data, processed) {
  const remaining = Array(data.remaining.length).fill(data.capacity);
  const indices = Array.from({ length: remaining.length }, () => []);
  for (let i = 0; i < processed; i += 1) {
    remaining[data.assignment[i]] -= data.items[i];
    indices[data.assignment[i]].push(i);
  }
  return { remaining, indices, usedBins: indices.filter((entries) => entries.length > 0).length };
}

test('empty state, sparse bins, conservation, and exact endpoints', () => {
  const data = fixture();
  const engine = new ReplayEngine(data, { checkpointInterval: 2 });
  assert.equal(engine.processed, 0);
  assert.equal(engine.getState().current, null);
  assert.equal(engine.getState().fillRatio, null);
  assert.deepEqual(engine.getBins().bins, []);
  assert.equal(engine.getBin(4).remaining, 100);
  engine.step();
  assert.equal(engine.getState().usedBins, 1);
  assert.equal(engine.getState().activeBin, 4);
  assert.equal(engine.getState().current.feasibleSlots, 6);
  assert.deepEqual(engine.getBins().bins.map((bin) => bin.bin), [4]);
  assert.deepEqual(engine.getBin(4).items, [{ index: 0, itemNumber: 1, size: 40 }]);
  engine.seek(6);
  assert.equal(engine.getState().usedBins, 3);
  assert.equal(engine.getState().totalVolume, 290);
  assert.equal(engine.getState().unusedCapacity, 10);
  assert.deepEqual(engine.getBins({ includeItems: true }).bins.map((bin) => bin.bin), [1, 4, 5]);
  assert.deepEqual(engine.getBins({ offset: 1, limit: 1 }).bins.map((bin) => bin.bin), [4]);
  assert.equal(engine.getBins({ usedOnly: false, limit: 6 }).bins.length, 6);
  assert.deepEqual(engine.getBin(4).items.map((item) => item.itemNumber), [1, 3, 6]);
  assert.equal(engine.step().processed, 6);
  assert.equal(engine.step(-100).processed, 0);
  assert.equal(engine.getBin(4).count, 0);
});

test('nonmonotonic random seeks agree with independently reconstructed state', () => {
  const data = fixture();
  const engine = new ReplayEngine(data, { checkpointInterval: 2 });
  for (const processed of [6, 1, 3, 0, 5, 2, 4, 6, 3, 1, 0]) {
    const state = engine.seek(processed);
    const expected = independentState(data, processed);
    assert.equal(state.usedBins, expected.usedBins);
    for (let bin = 0; bin < expected.remaining.length; bin += 1) {
      assert.equal(engine.getBin(bin).remaining, expected.remaining[bin]);
      assert.deepEqual(engine.getBin(bin).items.map((item) => item.index), expected.indices[bin]);
    }
    assert.equal(engine.getCurve().at(-1).processed, processed);
    assert.equal(engine.getCurve().at(-1).usedBins, state.usedBins);
  }
  assert.ok(engine.checkpointCount >= 5);
});

test('observed views hide unarrived items, future curve, result, and selection', () => {
  const engine = new ReplayEngine(fixture());
  engine.seek(2);
  assert.equal(engine.getState().decisionAvailable, false);
  assert.equal(engine.getState().selectedBranch, null);
  assert.equal(engine.getDecision().available, false);
  assert.equal(engine.getDecision().features, undefined);
  assert.equal(engine.getFinalResult(), null);
  assert.equal(engine.getItems({ limit: 100 }).length, 2);
  assert.equal(engine.getItems({ start: 2 }).length, 0);
  assert.equal(engine.getCurve().length, 3);
  assert.equal(engine.getItems({ retrospective: true }).length, 6);
  assert.equal(engine.getCurve({ retrospective: true }).length, 7);
  assert.equal(engine.getDecision({ retrospective: true }).available, true);
  assert.equal(engine.getFinalResult({ retrospective: true }).usedBins, 3);
  engine.seek(3);
  assert.equal(engine.getState().atDecisionBoundary, true);
  assert.equal(engine.getState().selectedBranch, 'BF');
  assert.equal(engine.getDecision().available, true);
  assert.deepEqual(engine.getDecision().predicted_final_bins, [3, 4]);
  assert.equal(engine.getDecision().final_outcome, undefined);
  assert.equal(engine.getItems().at(-1).itemNumber, 3);
  assert.equal(engine.getItems({ start: 3 }).length, 0);
  engine.seek(4);
  assert.equal(engine.getState().atDecisionBoundary, false);
  assert.equal(engine.getState().current.itemNumber, 4);
  engine.seek(1);
  assert.equal(engine.getDecision().available, false);
});

test('neither caller input mutation nor returned view mutation alters replay', () => {
  const data = fixture();
  const engine = new ReplayEngine(data);
  data.items[0] = 100;
  data.assignment[0] = 0;
  data.decision.features[0] = 99;
  engine.seek(3);
  const decision = engine.getDecision();
  decision.features[0] = 77;
  const bin = engine.getBin(4);
  bin.items[0].size = 99;
  bin.remaining = -10;
  const curve = engine.getCurve();
  curve[1].usedBins = 99;
  assert.equal(engine.getBin(4).remaining, 40);
  assert.equal(engine.getBin(4).items[0].size, 40);
  assert.equal(engine.getDecision().features[0], 1);
  assert.equal(engine.getCurve()[1].usedBins, 1);
});

test('bulk snapshots expose only current sparse-slot state and remain independent copies', () => {
  const engine = new ReplayEngine(fixture());
  const initial = engine.snapshot();
  assert.ok(initial.remaining instanceof Float64Array);
  assert.ok(initial.counts instanceof Uint32Array);
  assert.equal(initial.processed, 0);
  assert.deepEqual([...initial.remaining], [100, 100, 100, 100, 100, 100]);
  assert.deepEqual([...initial.counts], [0, 0, 0, 0, 0, 0]);
  engine.seek(3);
  const observed = engine.snapshot();
  assert.equal(observed.processed, 3);
  assert.deepEqual([...observed.remaining], [100, 30, 100, 100, 40, 100]);
  assert.deepEqual([...observed.counts], [0, 1, 0, 0, 2, 0]);
  assert.equal(observed.remaining[5], 100, 'future-used slot remains empty');
  observed.remaining.fill(-1);
  observed.counts.fill(99);
  observed.processed = 6;
  assert.equal(engine.processed, 3);
  assert.equal(engine.getBin(4).remaining, 40);
  assert.equal(engine.getBin(4).count, 2);
  assert.equal(engine.snapshot().remaining[5], 100);
  assert.deepEqual([...initial.remaining], [100, 100, 100, 100, 100, 100]);
  engine.seek(6);
  engine.seek(3);
  assert.equal(engine.snapshot().remaining[4], 40, 'snapshot edits never affect cached checkpoints');
});

test('comparison snapshots share time and cannot modify either side', () => {
  const comparison = new ReplayComparison(fixture(), fixture({ assignment: [0, 1, 0, 1, 2, 3] }));
  comparison.seek(3);
  const left = comparison.snapshot('left');
  const right = comparison.snapshot('right');
  assert.equal(left.processed, right.processed);
  assert.equal(left.remaining[4], 40);
  assert.equal(right.remaining[0], 40);
  left.remaining.fill(0);
  right.counts.fill(100);
  assert.equal(comparison.getBin('left', 4).remaining, 40);
  assert.equal(comparison.getBin('right', 0).count, 2);
  assert.throws(() => comparison.snapshot('bad'), RangeError);
});

test('comparison keeps time and stream identity synchronized', () => {
  const left = fixture();
  const right = fixture({ assignment: [0, 1, 0, 1, 2, 3] });
  right.policy = 'BF_then_EoH';
  right.run_id = 'test-stream__BF_then_EoH';
  const comparison = new ReplayComparison(left, right);
  for (const processed of [0, 3, 6, 1, 4]) {
    const state = comparison.seek(processed);
    assert.equal(state.left.processed, processed);
    assert.equal(state.right.processed, processed);
    assert.equal(state.left.current?.size, state.right.current?.size);
  }
  assert.equal(comparison.seek(6).deltaUsedBins, -1);
  assert.equal(comparison.getBins('right').total, 4);
  assert.equal(comparison.step(-6).processed, 0);
  assert.throws(() => comparison.getCurve('oops'), RangeError);
  assert.throws(() => new ReplayComparison(left, fixture({ instanceId: 'other' })), ReplayDataError);
  const different = fixture();
  different.items[0] = 41;
  assert.throws(() => new ReplayComparison(left, different), ReplayDataError);
});

test('rejects invalid shapes, nonfinite values, impossible slot IDs, and position arguments', () => {
  for (const mutate of [
    (data) => { data.schema_version = 2; },
    (data) => { data.items = null; },
    (data) => { data.assignment.pop(); },
    (data) => { data.assignment[0] = 6; },
    (data) => { data.items[0] = 101; },
    (data) => { data.post_remaining[0] = NaN; },
    (data) => { data.feasible_counts[0] = 7; },
    (data) => { data.used_bins_after[0] = 1.5; },
    (data) => { data.selector_consumed_count = 7; },
  ]) {
    const data = fixture();
    mutate(data);
    assert.throws(() => new ReplayEngine(data), ReplayDataError);
  }
  const engine = new ReplayEngine(fixture());
  for (const position of [-1, 7, 1.5, NaN, Infinity, '3']) assert.throws(() => engine.seek(position), RangeError);
  assert.throws(() => engine.getBin(6), RangeError);
  assert.throws(() => engine.step(0.5), RangeError);
  assert.throws(() => engine.getBins({ limit: -1 }), RangeError);
});

test('corrupt step and final state fail transactionally without poisoning checkpoints', () => {
  for (const field of ['pre_remaining', 'post_remaining', 'used_bins_after', 'feasible_counts', 'remaining']) {
    const data = fixture();
    if (field === 'remaining') data[field][0] = 99;
    else data[field][4] -= 1;
    const engine = new ReplayEngine(data, { checkpointInterval: 1 });
    engine.seek(2);
    const before = engine.getState();
    const cacheSize = engine.checkpointCount;
    assert.throws(() => engine.seek(6), ReplayDataError, field);
    assert.deepEqual(engine.getState(), before);
    assert.equal(engine.checkpointCount, cacheSize);
    assert.equal(engine.getBin(4).remaining, 60);
    assert.equal(engine.seek(3).processed, 3);
  }
});

test('feasible counts include empty slots and stay correct after checkpoint rollback', () => {
  const data = fixture();
  data.feasible_counts[0] = 1;
  assert.throws(() => new ReplayEngine(data), (error) => error instanceof ReplayDataError && error.details.field === 'feasible_counts');
  const valid = new ReplayEngine(fixture(), { checkpointInterval: 1 });
  for (const processed of [6, 2, 5, 0, 4, 1, 6]) assert.equal(valid.seek(processed).processed, processed);
});

test('direct callers cannot pass failed status, false totals, or malformed selector decisions', () => {
  const mutations = [
    (data) => { data.status = 'failed'; },
    (data) => { data.steps = 5; },
    (data) => { data.used_bins = -100; },
    (data) => { data.used_bins = 2; },
    (data) => { data.decision = null; },
    (data) => { data.decision.neighbors = [999999]; },
    (data) => { data.decision.predicted_final_bins = [0, 0]; },
    (data) => { data.decision.predicted_final_bins = [7, 8]; },
    (data) => { data.decision.selected_index = 1; },
    (data) => { data.decision.squared_distances = [-1]; },
    (data) => { data.decision.features = [NaN, 2]; },
    (data) => { data.prefix_features = [7, 2]; },
  ];
  for (const mutate of mutations) {
    const data = fixture();
    mutate(data);
    assert.throws(() => new ReplayEngine(data), ReplayDataError);
  }
});

test('a failed right-hand seek rolls both comparison views back', () => {
  const right = fixture();
  right.post_remaining[4] = 9;
  const comparison = new ReplayComparison(fixture(), right);
  comparison.seek(3);
  assert.throws(() => comparison.seek(6), ReplayDataError);
  assert.equal(comparison.getState().left.processed, 3);
  assert.equal(comparison.getState().right.processed, 3);
});
