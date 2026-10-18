import { afterEach, describe, expect, it, vi } from 'vitest';
import { lab } from './api';

afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });
function stalledServer() {
  vi.stubGlobal('fetch', vi.fn((_url: string, options: RequestInit) => new Promise((_resolve, reject) => {
    options.signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')), { once: true });
  })));
}
describe('bounded gateway requests', () => {
  it('a hung gateway returns a recoverable timeout instead of leaving the UI busy forever', async () => {
    vi.useFakeTimers(); stalledServer();
    const failure = expect(lab.health()).rejects.toMatchObject({ code: 'timeout', status: 0 });
    await vi.advanceTimersByTimeAsync(30_000);
    await failure;
    expect(vi.getTimerCount()).toBe(0);
  });
  it('normal simulation shutdown has a separate ninety-second deadline', async () => {
    vi.useFakeTimers(); stalledServer();
    let finished = false;
    const request = lab.simStop();
    void request.then(() => { finished = true; }, () => { finished = true; });
    const failure = expect(request).rejects.toMatchObject({ code: 'timeout' });
    await vi.advanceTimersByTimeAsync(30_000);
    expect(finished).toBe(false);
    await vi.advanceTimersByTimeAsync(60_000);
    await failure;
    expect(vi.getTimerCount()).toBe(0);
  });
});
