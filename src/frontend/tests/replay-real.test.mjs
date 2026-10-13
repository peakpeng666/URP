import test from 'node:test';
import assert from 'node:assert/strict';
import { readdir, readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { ReplayEngine, ReplayComparison } from '../core/replay.mjs';
import { ReplayDataClient } from '../core/data-client.mjs';

const directory = new URL('../public/data/runs/', import.meta.url);
let names = [];
try { names = (await readdir(directory)).filter((name) => name.endsWith('.json')).sort(); }
catch (error) { if (error.code !== 'ENOENT') throw error; }

const load = async (name) => JSON.parse(await readFile(new URL(name, directory), 'utf8'));

test('every exported historical run reaches its recorded final state', { skip: names.length === 0 ? 'Run data-convert first: no real run JSON available' : false }, async () => {
  assert.equal(names.length, 768, 'A complete export must contain all 768 physical runs');
  for (const name of names) {
    const data = await load(name);
    const engine = new ReplayEngine(data);
    const state = engine.seek(data.items.length);
    assert.equal(state.usedBins, data.used_bins_after.at(-1), name);
    const bins = engine.getBins({ limit: data.remaining.length, usedOnly: false }).bins;
    assert.deepEqual(bins.map((bin) => bin.remaining), data.remaining, name);
    assert.equal(bins.reduce((sum, bin) => sum + bin.count, 0), data.items.length, name);
    assert.equal(bins.reduce((sum, bin) => sum + bin.load, 0), data.items.reduce((a, b) => a + b, 0), name);
    engine.seek(0);
    assert.equal(engine.getState().usedBins, 0, name);
  }
});

test('real catalog descriptors pass byte-level SHA256 loading and same-stream comparison', { skip: names.length === 0 ? 'Run data-convert first' : false }, async () => {
  const catalog = JSON.parse(await readFile(new URL('../public/data/catalog.json', import.meta.url), 'utf8'));
  const stream = catalog.streams.find((stream) => stream.split === 'confirmation');
  const left = stream.runs.find((run) => run.policy === 'SELECTOR');
  const right = stream.runs.find((run) => run.policy === 'BF_then_EoH');
  const client = new ReplayDataClient({ fetchImpl: async (url) => {
    const relative = url.replace(/^\/data\//, '');
    return new Response(await readFile(new URL(`../public/data/${relative}`, import.meta.url)));
  } });
  const comparison = await client.loadComparison(left, right, { processed: 500 });
  assert.equal(comparison.processed, 500);
  assert.equal(comparison.getState().deltaUsedBins, 0);
  assert.equal(comparison.getDecision('left').available, true);
  assert.ok(client.sources.every((source) => source.hashVerified));
});

test('real SELECTOR refuses corrupted 31-feature/k5/neighbor-row/label relationships', { skip: names.length === 0 ? 'Run data-convert first' : false }, async () => {
  const real = await load(names.find((name) => name.endsWith('__SELECTOR.json')));
  const faults = [
    (data) => { data.steps = 4999; },
    (data) => { data.selector_consumed_count = 501; },
    (data) => { data.decision.features.pop(); },
    (data) => { data.decision.neighbors = [999999]; },
    (data) => { data.decision.neighbors[1] = data.decision.neighbors[0]; },
    (data) => { data.decision.squared_distances[0] = Infinity; },
    (data) => { data.decision.predicted_final_bins = [0, 0]; },
    (data) => { data.decision.neighbor_rows[0].index += 1; },
    (data) => { data.decision.neighbor_rows[0].squared_distance += 0.1; },
    (data) => { data.decision.neighbor_rows[0].instance_id = 'confirmation_unseen'; },
    (data) => { data.decision.neighbor_rows[0].labels[0] += 1; },
    (data) => { data.decision.feature_names.pop(); },
  ];
  for (const mutate of faults) {
    const data = structuredClone(real);
    mutate(data);
    assert.throws(() => new ReplayEngine(data), { name: 'ReplayDataError' });
  }
});

test('real selector: 0/499/500/501/5000 and random seeks agree with a scalar reconstruction', { skip: names.length === 0 ? 'Run data-convert first' : false }, async () => {
  const name = names.find((name) => name.endsWith('__SELECTOR.json'));
  assert.ok(name, 'Converted data must contain a real SELECTOR run');
  const data = await load(name);
  const engine = new ReplayEngine(data);
  let random = 0x17b00;
  const positions = [0, 499, 500, 501, 5000];
  for (let i = 0; i < 100; i += 1) {
    random = (Math.imul(random, 1664525) + 1013904223) >>> 0;
    positions.push(random % (data.items.length + 1));
  }
  for (const processed of positions) {
    const state = engine.seek(processed);
    const remaining = Array(data.remaining.length).fill(data.capacity);
    const counts = Array(data.remaining.length).fill(0);
    for (let i = 0; i < processed; i += 1) {
      remaining[data.assignment[i]] -= data.items[i];
      counts[data.assignment[i]] += 1;
    }
    const bins = engine.getBins({ limit: remaining.length, usedOnly: false }).bins;
    assert.deepEqual(bins.map((bin) => bin.remaining), remaining, `processed=${processed}`);
    assert.deepEqual(bins.map((bin) => bin.count), counts, `processed=${processed}`);
    assert.equal(state.usedBins, counts.filter((count) => count > 0).length);
    assert.equal(engine.getCurve().length, processed + 1);
    assert.equal(engine.getDecision().available, processed >= 500);
    if (processed === 500) {
      assert.equal(state.current.itemNumber, 500);
      assert.deepEqual(engine.getItems({ start: 500 }), []);
    }
  }
  const alternateName = `${data.instance_id}__BF_then_EoH.json`;
  assert.ok(names.includes(alternateName), 'Same-stream baseline must be exported');
  const comparison = new ReplayComparison(data, await load(alternateName));
  for (const processed of [0, 499, 500, 501, 5000, 17]) {
    const state = comparison.seek(processed);
    assert.equal(state.left.processed, state.right.processed);
    assert.equal(state.left.totalVolume, state.right.totalVolume);
    if (processed <= 500) assert.equal(state.left.usedBins, state.right.usedBins);
  }
  console.log(`Verified real replay fixture: ${fileURLToPath(new URL(name, directory))}`);
});

test('risk and full-EoH runs retain exact sparse-slot state on random seeks', { skip: names.length === 0 ? 'Run data-convert first' : false }, async () => {
  const representatives = [
    names.find((name) => name.startsWith('risk_') && name.endsWith('__SELECTOR.json')),
    names.find((name) => name.endsWith('__published_EoH.json')),
    names.find((name) => name.startsWith('train_') && name.endsWith('__BF_then_EoH.json')),
  ];
  assert.ok(representatives.every(Boolean), 'risk, full EoH, and train streams must exist');
  for (const name of representatives) {
    const data = await load(name);
    const engine = new ReplayEngine(data);
    for (const processed of [5000, 0, 499, 500, 501, 4231, 67, 2917, 1024]) {
      engine.seek(processed);
      const remaining = Array(data.remaining.length).fill(data.capacity);
      const counts = Array(data.remaining.length).fill(0);
      for (let i = 0; i < processed; i += 1) {
        remaining[data.assignment[i]] -= data.items[i];
        counts[data.assignment[i]] += 1;
      }
      const bins = engine.getBins({ limit: remaining.length, usedOnly: false }).bins;
      assert.deepEqual(bins.map((bin) => bin.remaining), remaining, `${name} @ ${processed}`);
      assert.deepEqual(bins.map((bin) => bin.count), counts, `${name} @ ${processed}`);
    }
    if (data.policy === 'published_EoH') assert.equal(engine.getState().phase, 'full-policy');
  }
});
