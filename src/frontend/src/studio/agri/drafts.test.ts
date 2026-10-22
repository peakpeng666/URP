import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AGRI_PATTERNS } from './patterns';
import { defaultValues, buildPattern } from './catalog';
import { clearDraft, debouncedDraftWriter, draftKey, DRAFT_SCHEMA, loadDraft, loadFilters, saveDraft, saveFilters } from './drafts';
import { extractPreview, previewIssues } from './preview';
import { selfIntersects, signedArea } from './geometry';
import { pointInPolygon as editorPip, distToSegment } from '../editor/geometry';

class MemStorage {
  m = new Map<string, string>(); quota = Infinity;
  getItem(k: string) { return this.m.has(k) ? this.m.get(k)! : null; }
  setItem(k: string, v: string) { if (k !== '__urp_probe__' && v.length > this.quota) throw new DOMException('full', 'QuotaExceededError'); this.m.set(k, v); }
  removeItem(k: string) { this.m.delete(k); }
}
const p = AGRI_PATTERNS.find((x) => x.id === 'field-sampling')!;
let local: MemStorage;
beforeEach(() => { local = new MemStorage(); vi.stubGlobal('localStorage', local); vi.stubGlobal('sessionStorage', new MemStorage()); });
afterEach(() => vi.unstubAllGlobals());

describe('agri drafts', () => {
  it('round-trips values and seed, keeping blank numbers as unfilled', () => {
    const key = p.runnable!.params.find((x) => x.type === 'number')!.key;
    const v = { ...defaultValues(p), [key]: NaN };
    expect(saveDraft(p, v, '7')).toBe('');
    const got = loadDraft(p, defaultValues(p));
    expect(got.restored).toBe(true); expect(got.seed).toBe('7'); expect(Number.isNaN(got.values[key])).toBe(true);
  });
  it('drops a corrupt draft and says so', () => {
    local.setItem(draftKey(p.id), '{not json');
    const got = loadDraft(p, defaultValues(p));
    expect(got.restored).toBe(false); expect(got.notice).toMatch('损坏'); expect(local.getItem(draftKey(p.id))).toBeNull();
  });
  it('refuses an incompatible schema without deleting it', () => {
    local.setItem(draftKey(p.id), JSON.stringify({ schema: DRAFT_SCHEMA + 1, patternId: p.id, values: {} }));
    const got = loadDraft(p, defaultValues(p));
    expect(got.restored).toBe(false); expect(got.notice).toMatch('不兼容'); expect(local.getItem(draftKey(p.id))).not.toBeNull();
  });
  it('migrates a stale signature keeping only type-matching values', () => {
    const [a] = p.runnable!.params;
    local.setItem(draftKey(p.id), JSON.stringify({ schema: DRAFT_SCHEMA, patternId: p.id, signature: 'old', values: { [a.key]: 'wrong-type', ghost: 1 }, seed: '9' }));
    const got = loadDraft(p, defaultValues(p));
    expect(got.values[a.key]).toEqual(a.default); expect('ghost' in got.values).toBe(false); expect(got.notice).toMatch('参数已变更');
  });
  it('reports quota exhaustion instead of throwing', () => {
    local.quota = 10;
    expect(saveDraft(p, defaultValues(p), '1')).toMatch('已满');
  });
  it('works without any storage', () => {
    vi.stubGlobal('localStorage', undefined);
    expect(loadDraft(p, defaultValues(p)).restored).toBe(false);
    expect(saveDraft(p, defaultValues(p), '1')).toMatch('不可用');
    expect(() => clearDraft(p.id)).not.toThrow();
  });
  it('persists catalog filters per session', () => {
    saveFilters({ environment: 'orchard', operation: '', status: 'runnable' });
    expect(loadFilters()).toEqual({ environment: 'orchard', operation: '', status: 'runnable' });
  });
});

describe('agri preview', () => {
  it('extracts every runnable builder without modifying the instance', () => {
    for (const pat of AGRI_PATTERNS.filter((x) => x.runnable)) {
      const built = buildPattern(pat, defaultValues(pat), 42);
      const before = JSON.stringify(built.instance);
      const pv = extractPreview(built);
      expect(pv.boundary.length).toBeGreaterThanOrEqual(3);
      expect(previewIssues(pv).filter((i) => i.level === 'error'), pat.id).toEqual([]);
      expect(JSON.stringify(built.instance)).toBe(before);
    }
  });
  it('flags self-intersection, degenerate area and tasks inside obstacles', () => {
    const built = buildPattern(p, defaultValues(p), 42);
    const pv = extractPreview(built);
    const t = pv.tasks[0];
    const box: [number, number][] = [[t.xy[0] - 1, t.xy[1] - 1], [t.xy[0] + 1, t.xy[1] - 1], [t.xy[0] + 1, t.xy[1] + 1], [t.xy[0] - 1, t.xy[1] + 1]];
    const issues = previewIssues({ ...pv, obstacles: [...pv.obstacles, { id: 'X', kind: 'rock', polygon: box }] });
    expect(issues.some((i) => i.target === `task:${t.id}`)).toBe(true);
    expect(selfIntersects([[0, 0], [2, 2], [2, 0], [0, 2]])).toBe(true);
    expect(selfIntersects([[0, 0], [2, 0], [2, 2], [0, 2]])).toBe(false);
    expect(signedArea([[0, 0], [1, 1], [2, 2]])).toBe(0);
    expect(previewIssues({ ...pv, boundary: [[0, 0], [2, 2], [2, 0], [0, 2]] }).some((i) => i.message === '边界自交')).toBe(true);
  });
  it('editor geometry now shares the agri implementation', () => {
    expect(editorPip([1, 1], [[0, 0], [2, 0], [2, 2], [0, 2]])).toBe(true);
    expect(distToSegment([0, 1], [-1, 0], [1, 0])).toBe(1);
  });
});

import { lastImport, recordImport } from './drafts';
describe('last import record', () => {
  it('remembers the last imported scenario per pattern and tolerates garbage', () => {
    expect(lastImport(p.id)).toBeNull();
    recordImport(p.id, { scenarioId: 's1', title: 'T', seed: '3', at: 'x' });
    expect(lastImport(p.id)?.scenarioId).toBe('s1');
    local.setItem(`urp.agri.lastImport.v1:${p.id}`, '{bad');
    expect(lastImport(p.id)).toBeNull();
  });
});

describe('debouncedDraftWriter', () => {
  it('flushes a pending write once and never writes twice', async () => {
    const { vi } = await import('vitest');
    vi.useFakeTimers();
    try {
      let n = 0;
      const w = debouncedDraftWriter(() => { n += 1; }, 300);
      expect(w.pending()).toBe(true);
      w.flush(); expect(n).toBe(1); expect(w.pending()).toBe(false);
      vi.advanceTimersByTime(500); w.flush(); expect(n).toBe(1);
      const w2 = debouncedDraftWriter(() => { n += 1; }, 300);
      vi.advanceTimersByTime(300); expect(n).toBe(2); w2.flush(); expect(n).toBe(2);
      const w3 = debouncedDraftWriter(() => { n += 1; }, 300);
      w3.cancel(); vi.advanceTimersByTime(500); w3.flush(); expect(n).toBe(2);
    } finally { vi.useRealTimers(); }
  });
});
