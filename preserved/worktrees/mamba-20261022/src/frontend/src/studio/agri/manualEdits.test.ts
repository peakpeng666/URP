import { describe, expect, it } from 'vitest';
import { AGRI_PATTERNS } from './patterns';
import { buildPattern, defaultValues } from './catalog';
import { manualEdits } from './manualEdits';

const p = AGRI_PATTERNS.find((x) => x.id === 'field-sampling')!;
describe('manual edit detection', () => {
  const built = buildPattern(p, defaultValues(p), 42);
  it('sees no edits on an untouched import', () => {
    const r = manualEdits(p, built);
    expect(r.reproducible).toBe(true); expect(r.changes).toEqual([]); expect(r.seed).toBe(42);
  });
  it('reports moved, added and removed tasks and a moved depot', () => {
    const inst = structuredClone(built.instance) as { tasks: { id: number; xy: [number, number] }[]; depot: [number, number] };
    inst.tasks[0].xy = [inst.tasks[0].xy[0] + 3, inst.tasks[0].xy[1]];
    inst.tasks.pop();
    inst.tasks.push({ ...inst.tasks[1], id: 999 });
    inst.depot = [inst.depot[0] + 1, inst.depot[1]];
    const r = manualEdits(p, { ...built, instance: inst });
    expect(r.changes.join('|')).toMatch(/任务点改动 1/); expect(r.changes.join('|')).toMatch(/任务点新增 1/);
    expect(r.changes.join('|')).toMatch(/任务点删除 1/); expect(r.changes).toContain('库点已移动');
  });
  it('refuses to guess when seed or params are missing', () => {
    expect(manualEdits(p, { instance: built.instance, provenance: {} }).reproducible).toBe(false);
    expect(manualEdits(p, { instance: built.instance, provenance: { seed: 1, params: {} } }).reason).toMatch('不一致');
  });
});
