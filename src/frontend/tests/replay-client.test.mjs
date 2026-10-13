import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { ReplayDataClient, DataLoadError, StaleResponseError, fetchJSON } from '../core/data-client.mjs';
import { ReplayDataError, ReplayComparison } from '../core/replay.mjs';

function run(runId = 'stream__BF', instanceId = 'stream') {
  return {
    schema_version: 1, run_id: runId, instance_id: instanceId, policy: 'BF',
    capacity: 100, switch_after: 2, items: [70, 20, 90], assignment: [2, 2, 1],
    pre_remaining: [100, 30, 100], post_remaining: [30, 10, 10],
    feasible_counts: [3, 3, 2], used_bins_after: [1, 1, 2], remaining: [100, 10, 10],
  };
}

function delayedFetch() {
  const requests = new Map();
  return {
    // Deliberately ignores cancellation: revision checks must still protect state.
    fetchImpl(url, options) {
      return new Promise((resolve, reject) => requests.set(url, { resolve, reject, signal: options.signal }));
    },
    resolve(url, data) { requests.get(url).resolve(new Response(JSON.stringify(data))); },
    reject(url, error) { requests.get(url).reject(error); },
    request(url) { return requests.get(url); },
  };
}

test('latest request wins even when an old fetch ignores abort and resolves last', async () => {
  const transport = delayedFetch();
  const client = new ReplayDataClient(transport);
  const old = client.loadRun('/old');
  const oldRejected = assert.rejects(old, StaleResponseError);
  const current = client.loadRun('/new', { processed: 2 });
  assert.equal(transport.request('/old').signal.aborted, true);
  assert.equal(client.current, null);
  transport.resolve('/new', run('new__BF'));
  const engine = await current;
  assert.equal(engine.metadata.runId, 'new__BF');
  assert.equal(engine.processed, 2);
  transport.resolve('/old', run('old__BF'));
  await oldRejected;
  assert.equal(client.current, engine);
  assert.equal(client.status, 'ready');
  assert.equal(client.error, null);
});

test('comparison loads both descriptors at one time and rejects a different input stream', async () => {
  const client = new ReplayDataClient({ fetchImpl: async (url) => new Response(JSON.stringify(run(url, url === '/bad' ? 'different' : 'stream'))) });
  const result = await client.loadComparison('/left', '/right', { processed: 3 });
  assert.ok(result instanceof ReplayComparison);
  assert.equal(result.getState().left.processed, 3);
  assert.equal(result.getState().right.processed, 3);
  assert.equal(client.sources.length, 2);
  assert.equal(client.sources[0].hashVerified, false);
  await assert.rejects(client.loadComparison('/left', '/bad'), ReplayDataError);
  assert.equal(client.status, 'error');
  assert.equal(client.current, null);
});

test('catalog SHA256 verifies original response bytes and detects altered data', async () => {
  const body = JSON.stringify(run());
  const sha256 = createHash('sha256').update(body).digest('hex');
  const client = new ReplayDataClient({ fetchImpl: async () => new Response(body) });
  await client.loadRun({ data_url: '/run', run_id: 'stream__BF', policy: 'BF', sha256 });
  assert.equal(client.sources[0].hashVerified, true);
  await assert.rejects(client.loadRun({ data_url: '/run', sha256: '0'.repeat(64) }), (error) => error.code === 'HASH_MISMATCH');
  assert.equal(client.current, null);
  const unavailable = new ReplayDataClient({ fetchImpl: async () => new Response(body), cryptoImpl: null });
  await assert.rejects(unavailable.loadRun({ data_url: '/run', sha256 }), (error) => error.code === 'HASH_UNAVAILABLE');
});

test('missing, malformed, mismatched, and invalid run data fail with actionable errors', async () => {
  const cases = [
    [async () => new Response('missing', { status: 404 }), { code: 'HTTP_ERROR' }],
    [async () => new Response('<html>fallback page</html>'), { code: 'INVALID_JSON' }],
    [async () => { throw new TypeError('offline'); }, { code: 'NETWORK_ERROR' }],
  ];
  for (const [fetchImpl, expected] of cases) {
    const client = new ReplayDataClient({ fetchImpl });
    await assert.rejects(client.loadRun('/broken'), (error) => error instanceof DataLoadError && error.code === expected.code);
    assert.equal(client.status, 'error');
  }
  const client = new ReplayDataClient({ fetchImpl: async () => new Response(JSON.stringify(run())) });
  await assert.rejects(client.loadRun({ data_url: '/run', run_id: 'wrong' }), (error) => error.code === 'IDENTITY_MISMATCH');
  await assert.rejects(client.loadRun({ data_url: '/run', sha256: 'invalid' }), (error) => error.code === 'INVALID_DESCRIPTOR');
  const invalid = new ReplayDataClient({ fetchImpl: async () => new Response('{"schema_version":1}') });
  await assert.rejects(invalid.loadRun('/invalid'), ReplayDataError);
});

test('external cancellation and explicit cancel prevent late state commits', async () => {
  const transport = delayedFetch();
  const client = new ReplayDataClient(transport);
  const signal = new AbortController();
  const pending = client.loadRun('/external', { signal: signal.signal });
  const rejected = assert.rejects(pending, { name: 'AbortError' });
  signal.abort();
  transport.resolve('/external', run());
  await rejected;
  assert.equal(client.status, 'idle');
  assert.equal(client.current, null);
  const next = client.loadRun('/cancel');
  const cancelled = assert.rejects(next, StaleResponseError);
  client.cancel();
  transport.resolve('/cancel', run());
  await cancelled;
  assert.equal(client.status, 'idle');
  assert.equal(client.current, null);
});

test('stateless JSON loader can load catalog but rejects invalid UTF-8 and pre-aborted calls', async () => {
  assert.deepEqual(await fetchJSON('/catalog', { fetchImpl: async () => new Response('{"schema_version":1}') }), { schema_version: 1 });
  await assert.rejects(fetchJSON('/bad', { fetchImpl: async () => new Response(new Uint8Array([0xff])) }), (error) => error.code === 'INVALID_JSON');
  const signal = AbortSignal.abort();
  let called = false;
  await assert.rejects(fetchJSON('/abort', { signal, fetchImpl: async () => { called = true; } }), { name: 'AbortError' });
  assert.equal(called, false);
});
