import { afterEach, describe, expect, it, vi } from 'vitest';
import { DEMO_PROBLEM, parseProblem, projectPoints, requestApi, terminalJob } from './workspace-api';

afterEach(() => vi.unstubAllGlobals());
describe('live task contract', () => {
  it('keeps genuine numeric inputs and rejects booleans, mismatches and unsupported task fields', () => {
    expect(parseProblem(JSON.stringify(DEMO_PROBLEM))).toEqual(DEMO_PROBLEM);
    for (const patch of [{ capacity: true }, { K: false }, { coordinates: [[0, 0], [true, 0]] },
      { demands: [0, 1] }, { demands: [1, 2, 3, 2, 4, 1] }, { capacity: 0 },
      { K: 99 }, { worker_path: '/tmp/worker.py' }, { time_windows: [] }]) {
      expect(() => parseProblem(JSON.stringify({ ...DEMO_PROBLEM, ...patch }))).toThrow();
    }
  });
  it('never projects unknown/nonfinite coordinates as zero and keeps Y upright', () => {
    expect(projectPoints([[NaN, 0]])).toEqual([]);
    expect(projectPoints([])).toEqual([]);
    expect(projectPoints([[2, 3], [2, 3]])).toEqual([[380, 180], [380, 180]]);
    const [a, b, c] = projectPoints([[0, 0], [10, 0], [0, 10]]);
    expect(b[0] - a[0]).toBeCloseTo(a[1] - c[1]);
    expect(c[1]).toBeLessThan(a[1]);
  });
  it('distinguishes pending work from all retained terminal states', () => {
    expect(terminalJob('queued')).toBe(false);
    expect(terminalJob('running')).toBe(false);
    for (const status of ['completed', 'failed', 'interrupted'] as const) expect(terminalJob(status)).toBe(true);
  });
  it('preserves structured API rejections and rejects a static fallback document', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: 'scene_conflict', message: '场景版本冲突' }),
      { status: 409, headers: { 'Content-Type': 'application/json' } })));
    await expect(requestApi('/api/jobs')).rejects.toMatchObject({ status: 409, code: 'scene_conflict', message: '场景版本冲突' });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>app</html>', { headers: { 'Content-Type': 'text/html' } })));
    await expect(requestApi('/api/jobs')).rejects.toMatchObject({ code: 'invalid_api_response' });
  });
  it('does not cache mutable job state or accept a remote API address', async () => {
    const fetcher = vi.fn().mockImplementation(() => Promise.resolve(new Response('{}', { headers: { 'Content-Type': 'application/json' } })));
    vi.stubGlobal('fetch', fetcher);
    await requestApi('/api/jobs'); await requestApi('/api/jobs');
    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(fetcher.mock.calls[0][1].cache).toBe('no-store');
    await expect(requestApi('https://example.com/api/jobs')).rejects.toThrow();
    expect(fetcher).toHaveBeenCalledTimes(2);
  });
});
