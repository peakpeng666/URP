import { describe, expect, it, vi } from 'vitest';
import { buildPattern, createImportGuard, defaultValues } from './catalog';
import { AGRI_PATTERNS } from './patterns';
const pattern = AGRI_PATTERNS.find((p) => p.id === 'field-sampling')!;
describe('catalog request lifecycle', () => {
  it('ignores repeated clicks until success or failure, then permits an explicit retry', () => {
    const guard = createImportGuard(); const ticket = guard.begin()!;
    expect(guard.begin()).toBeNull(); expect(guard.canNavigate(ticket)).toBe(true);
    guard.finish(); expect(guard.canNavigate(ticket)).toBe(false); expect(guard.begin()).not.toBeNull();
  });
  it('never redirects after leaving and returning to the original location', () => {
    const guard = createImportGuard(); const ticket = guard.begin()!;
    guard.invalidateNavigation(); guard.invalidateNavigation();
    expect(guard.canNavigate(ticket)).toBe(false);
    guard.finish(); const next = guard.begin()!; expect(guard.canNavigate(next)).toBe(true);
  });
  it('invalidates a response on unmount without claiming the server canceled its write', () => {
    const guard = createImportGuard(); const ticket = guard.begin()!;
    guard.invalidateNavigation(); expect(guard.canNavigate(ticket)).toBe(false); expect(guard.begin()).toBeNull();
    guard.finish();
  });
});
describe('scenario identity and numeric boundaries', () => {
  it('never reuses an ID for repeated same-millisecond builds or changed parameters', () => {
    const now = vi.spyOn(Date, 'now').mockReturnValue(123456);
    try {
      const a = buildPattern(pattern, defaultValues(pattern), 42);
      const b = buildPattern(pattern, defaultValues(pattern), 42);
      const c = buildPattern(pattern, { ...defaultValues(pattern), task_count: 6 }, 42);
      expect(new Set([a.id, b.id, c.id]).size).toBe(3);
      for (const id of [a.id, b.id, c.id]) expect(id).toMatch(/^[a-z0-9][a-z0-9_.-]{1,63}$/);
      expect(a.instance).toEqual(b.instance); expect(c.instance).not.toEqual(a.instance);
    } finally { now.mockRestore(); }
  });
  it.each([NaN, Infinity, -Infinity, -1, 0.5, 4294967296])('rejects invalid seed %s', (seed) => {
    expect(() => buildPattern(pattern, defaultValues(pattern), seed)).toThrow('种子');
  });
  it.each([0, 4294967295])('supports inclusive uint32 seed %s and JSON roundtrip', (seed) => {
    const built = buildPattern(pattern, defaultValues(pattern), seed);
    expect(JSON.parse(JSON.stringify(built))).toEqual(built);
  });
  it.each([NaN, Infinity, -Infinity, 0, 600.1])('rejects invalid numeric parameter %s', (field_w) => {
    expect(() => buildPattern(pattern, { ...defaultValues(pattern), field_w }, 42)).toThrow();
  });
});

describe('HTTP recovery and duplicate writes', () => {
  it('shares one pending import across callers and retries with a new ID after a 409', async () => {
    const { importPattern } = await import('./catalog');
    let complete!: (value: Response) => void;
    const fetchMock = vi.fn().mockImplementationOnce(() => new Promise<Response>((resolve) => { complete = resolve; }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: 'new-saved-id', title: 'saved' }), { status: 201 }));
    vi.stubGlobal('fetch', fetchMock);
    try {
      const values = defaultValues(pattern);
      const a = importPattern(pattern, values, 42); const b = importPattern(pattern, Object.fromEntries(Object.entries(values).reverse()), 42);
      const failures = Promise.allSettled([a, b]);
      expect(fetchMock).toHaveBeenCalledTimes(1);
      const firstId = JSON.parse(fetchMock.mock.calls[0][1].body).id;
      complete(new Response(JSON.stringify({ message: '场景 id 已存在' }), { status: 409 }));
      expect((await failures).map((r) => r.status)).toEqual(['rejected', 'rejected']);
      expect(values).toEqual(defaultValues(pattern));
      expect((await importPattern(pattern, values, 42)).id).toBe('new-saved-id');
      expect(fetchMock).toHaveBeenCalledTimes(2);
      expect(JSON.parse(fetchMock.mock.calls[1][1].body).id).not.toBe(firstId);
    } finally { vi.unstubAllGlobals(); }
  });
  it('rejects malformed success responses rather than navigating to an undefined scene', async () => {
    const { importPattern } = await import('./catalog');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 201 })));
    try { await expect(importPattern(pattern, defaultValues(pattern), 42)).rejects.toThrow('核对保存结果'); }
    finally { vi.unstubAllGlobals(); }
  });
});

describe('download failure cleanup', () => {
  it('releases object URLs even if the browser refuses the click', async () => {
    const { downloadFile } = await import('./export');
    vi.useFakeTimers();
    const create = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:test');
    const revoke = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    vi.stubGlobal('document', { createElement: () => ({ click() { throw new Error('blocked download'); } }) });
    vi.stubGlobal('window', { setTimeout: globalThis.setTimeout });
    try {
      expect(() => downloadFile({ serialized: '{}', mime: 'application/json', fileName: 'matrix.json' })).toThrow('blocked download');
      vi.runAllTimers(); expect(revoke).toHaveBeenCalledWith('blob:test');
    } finally { vi.useRealTimers(); vi.unstubAllGlobals(); create.mockRestore(); revoke.mockRestore(); }
  });
});

describe('LAN HTTP compatibility', () => {
  it('builds distinct IDs without secure-context randomUUID', () => {
    const getRandomValues = vi.fn(crypto.getRandomValues.bind(crypto));
    vi.stubGlobal('crypto', { getRandomValues });
    try {
      const p = AGRI_PATTERNS.find((p) => p.id === 'field-sampling')!;
      const values = defaultValues(p);
      const first = buildPattern(p, values, 42);
      const second = buildPattern(p, values, 42);
      expect(first.id).not.toBe(second.id);
      expect(first.id).toMatch(/-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
      expect(getRandomValues).toHaveBeenCalledTimes(2);
    } finally { vi.unstubAllGlobals(); }
  });
});
