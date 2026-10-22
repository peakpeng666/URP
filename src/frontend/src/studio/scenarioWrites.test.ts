import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

class MemoryStorage {
  data = new Map<string, string>();
  getItem(k: string) { return this.data.has(k) ? this.data.get(k)! : null; }
  setItem(k: string, v: string) { this.data.set(k, String(v)); }
  removeItem(k: string) { this.data.delete(k); }
}

const json = (body: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(body), { status }));
const lost = () => Promise.reject(new TypeError('response lost'));
const methods = (f: ReturnType<typeof vi.fn>) => f.mock.calls.map((c) => `${c[1]?.method ?? 'GET'} ${String(c[0])}`);

let storage: MemoryStorage;
beforeEach(() => {
  vi.resetModules();
  storage = new MemoryStorage();
  vi.stubGlobal('sessionStorage', storage);
});
afterEach(() => vi.unstubAllGlobals());

/** A "reload": fresh module graph (memory gone), same tab storage. */
async function load() {
  vi.resetModules();
  return import('./scenarioWrites');
}

const instance = { tasks: [{ id: 1, xy: [1, 2] }] };

describe('idempotent fork', () => {
  it('sends a client id and, after a lost response, reads it back instead of forking again', async () => {
    let sent: any;
    const fetch = vi.fn().mockImplementationOnce((_u, o) => { sent = JSON.parse(o.body); return lost(); })
      .mockImplementationOnce(() => json({ id: sent.client_id, instance, provenance: { forked_from: 'base' } }));
    vi.stubGlobal('fetch', fetch);
    const { forkScenarioOnce } = await load();
    await expect(forkScenarioOnce('base', { instance })).rejects.toThrow();
    expect(sent.client_id).toMatch(/^base-my-[0-9a-f]{12}$/);
    const copy = await forkScenarioOnce('base', { instance });
    expect(copy.id).toBe(sent.client_id);
    expect(methods(fetch)).toEqual(['POST /lab/api/scenarios/base/fork', `GET /lab/api/scenarios/${sent.client_id}`]);
    expect(JSON.parse(storage.getItem('urp.studio.pending-writes')!).entries).toEqual({});
  });

  it('survives a reload: queries the persisted id, resubmits the same id only after a 404', async () => {
    const ids: string[] = [];
    const fetch = vi.fn().mockImplementationOnce((_u, o) => { ids.push(JSON.parse(o.body).client_id); return lost(); })
      .mockImplementationOnce(() => json({}, 404))
      .mockImplementationOnce((_u, o) => { ids.push(JSON.parse(o.body).client_id); return json({ id: ids[1], instance }, 201); });
    vi.stubGlobal('fetch', fetch);
    await expect((await load()).forkScenarioOnce('base', { instance })).rejects.toThrow();
    const after = await load();
    expect((await after.forkScenarioOnce('base', { instance })).id).toBe(ids[0]);
    expect(ids[1]).toBe(ids[0]);
    expect(fetch.mock.calls.map((c) => c[1]?.method ?? 'GET')).toEqual(['POST', 'GET', 'POST']);
  });

  it('dedupes concurrent identical forks into one request', async () => {
    const fetch = vi.fn().mockImplementation((_u, o) => json({ id: JSON.parse(o.body).client_id }, 201));
    vi.stubGlobal('fetch', fetch);
    const { forkScenarioOnce } = await load();
    const [a, b] = await Promise.all([forkScenarioOnce('base', { instance }), forkScenarioOnce('base', { instance })]);
    expect(a.id).toBe(b.id);
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it('a definite rejection clears the record so the next attempt is a new write', async () => {
    const fetch = vi.fn().mockImplementationOnce(() => json({ error: { code: 'invalid_instance', message: 'bad' } }, 400))
      .mockImplementationOnce((_u, o) => json({ id: JSON.parse(o.body).client_id }, 201));
    vi.stubGlobal('fetch', fetch);
    const { forkScenarioOnce } = await load();
    await expect(forkScenarioOnce('base', { instance })).rejects.toThrow();
    await forkScenarioOnce('base', { instance });
    expect(fetch.mock.calls.map((c) => c[1]?.method)).toEqual(['POST', 'POST']);
  });

  it('a stored copy with different content is a conflict, never adopted', async () => {
    let id = '';
    const fetch = vi.fn().mockImplementationOnce((_u, o) => { id = JSON.parse(o.body).client_id; return lost(); })
      .mockImplementationOnce(() => json({ id, instance: { tasks: [] }, provenance: { forked_from: 'base' } }));
    vi.stubGlobal('fetch', fetch);
    const { forkScenarioOnce } = await load();
    await expect(forkScenarioOnce('base', { instance })).rejects.toThrow();
    await expect(forkScenarioOnce('base', { instance })).rejects.toThrow('内容与本次提交不一致');
    expect(JSON.parse(storage.getItem('urp.studio.pending-writes')!).entries).toEqual({});
  });
});

describe('idempotent scenario import', () => {
  const doc = { id: 'my-import', problem_class: 'coverage', instance: { field: [[0, 0], [1, 0], [1, 1]] } };
  it('timeout then recovery: the retry reads the original id and never posts twice', async () => {
    const fetch = vi.fn().mockImplementationOnce(lost)
      .mockImplementationOnce(() => json({ ...doc, origin: 'user', title: 'x' }));
    vi.stubGlobal('fetch', fetch);
    const { importScenarioOnce } = await load();
    await expect(importScenarioOnce(doc)).rejects.toThrow();
    expect((await importScenarioOnce(doc)).id).toBe('my-import');
    expect(fetch.mock.calls.map((c) => c[1]?.method ?? 'GET')).toEqual(['POST', 'GET']);
  });
  it('a 409 on a retried write is resolved by reading back identical content', async () => {
    const fetch = vi.fn().mockImplementationOnce(lost).mockImplementationOnce(() => json({}, 404))
      .mockImplementationOnce(() => json({ error: { code: 'scenario_conflict', message: 'exists' } }, 409))
      .mockImplementationOnce(() => json({ ...doc, origin: 'user', title: 'x' }));
    vi.stubGlobal('fetch', fetch);
    const { importScenarioOnce } = await load();
    await expect(importScenarioOnce(doc)).rejects.toThrow();
    expect((await importScenarioOnce(doc)).id).toBe('my-import');
  });
});

describe('idempotent GeoJSON import', () => {
  it('after an uncertain outcome, finds the scenario it produced instead of importing again', async () => {
    const fetch = vi.fn().mockImplementationOnce(lost)
      .mockImplementationOnce(() => json({ scenarios: [{ id: 'geo-1', title: 'field', origin: 'user' }] }))
      .mockImplementationOnce(() => json({ id: 'geo-1', title: 'field' }));
    vi.stubGlobal('fetch', fetch);
    const { importGeojsonOnce } = await load();
    await expect(importGeojsonOnce({ type: 'FeatureCollection', features: [] }, 'field')).rejects.toThrow();
    expect((await importGeojsonOnce({ type: 'FeatureCollection', features: [] }, 'field')).id).toBe('geo-1');
    expect(fetch.mock.calls.filter((c) => c[1]?.method === 'POST')).toHaveLength(1);
  });
});

describe('pending write storage', () => {
  it('tolerates corrupt, foreign-version and unavailable storage', async () => {
    storage.setItem('urp.studio.pending-writes', '{not json');
    let mod = await import('./pendingWrites');
    mod.rememberWrite('k', { id: 'abc-1', kind: 'fork', created: Date.now() });
    expect(mod.pendingWrite('k')?.id).toBe('abc-1');
    storage.setItem('urp.studio.pending-writes', JSON.stringify({ v: 99, entries: { k: { id: 'zz-9', kind: 'x', created: 1 } } }));
    vi.resetModules(); mod = await import('./pendingWrites');
    expect(mod.pendingWrite('k')).toBeUndefined();
    storage.setItem('urp.studio.pending-writes', JSON.stringify({ v: 1, entries: { a: { id: 'BAD ID', kind: 'x', created: Date.now() }, b: 3 } }));
    expect(mod.pendingWrite('a')).toBeUndefined();
    vi.stubGlobal('sessionStorage', { getItem() { throw new Error('denied'); }, setItem() { throw new Error('denied'); } });
    vi.resetModules(); mod = await import('./pendingWrites');
    mod.rememberWrite('k', { id: 'abc-2', kind: 'fork', created: Date.now() });
    expect(mod.pendingWrite('k')?.id).toBe('abc-2');
    mod.forgetWrite('k');
    expect(mod.pendingWrite('k')).toBeUndefined();
  });
  it('drops expired records', async () => {
    storage.setItem('urp.studio.pending-writes', JSON.stringify({ v: 1, entries: { old: { id: 'old-1', kind: 'fork', created: Date.now() - 2 * 86400_000 } } }));
    const mod = await import('./pendingWrites');
    expect(mod.pendingWrite('old')).toBeUndefined();
  });
});
