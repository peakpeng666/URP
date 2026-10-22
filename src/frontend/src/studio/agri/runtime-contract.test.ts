import { describe, expect, it } from 'vitest';
import { RUNNABLE_PATTERNS } from './patterns/runnable';
import type { FleetInstance } from '../types';

function build(id: string, patch: Record<string, unknown> = {}) {
  const pattern = RUNNABLE_PATTERNS.find(p => p.id === id)!;
  const values = Object.fromEntries(pattern.runnable!.params.map(p => [p.key, p.default]));
  return pattern.runnable!.build({ ...values, ...patch }, 42);
}

describe('agri backend schema and resource regression', () => {
  it('uses the existing fleet schema without a competing rows field', () => {
    const { instance } = build('orchard-harvest-transport');
    const fleet = instance as unknown as FleetInstance;
    expect(fleet.plots[0].polygon).toHaveLength(4);
    expect(fleet.plots[0].crop).toBe('苹果');
    expect(fleet.tasks[0].id).toBe(1);
    expect(fleet.tasks[0].xy).toHaveLength(2);
    expect(fleet.tasks[0].label).toBe('采摘点1');
    expect(instance).not.toHaveProperty('rows');
  });
  it('changes both canonical row direction and generated task coordinates', () => {
    const a = build('orchard-harvest-transport', { row_angle: 0 }).instance as unknown as FleetInstance;
    const b = build('orchard-harvest-transport', { row_angle: 90 }).instance as unknown as FleetInstance;
    expect(a.plots[0].rows_deg).toBe(0);
    expect(b.plots[0].rows_deg).toBe(90);
    expect(a.tasks).not.toEqual(b.tasks);
  });
  it('rejects insufficient capacity rather than silently increasing it', () => {
    expect(() => build('bale-collection', { capacity: 1, demand_per_task: 100 })).toThrow(/容量/);
  });
  it('never silently creates additional vehicles', () => {
    expect(() => build('mixed-fleet-transport', { vehicles: 1 })).toThrow(/至少/);
    for (const vehicles of [2, 3, 4, 15]) {
      const inst = build('mixed-fleet-transport', { vehicles }).instance as unknown as FleetInstance;
      expect(inst.vehicles.fleet!.reduce((sum, f) => sum + f.count, 0)).toBe(vehicles);
    }
  });
  it('rejects degenerate field interiors and oversized obstacles', () => {
    expect(() => build('multi-field-fleet', { field_w: 40, field_h: 40 })).toThrow(/边距/);
    expect(() => build('coverage-obstacle-field', { field_w: 40, field_h: 40, pond_r: 40 })).toThrow(/池塘/);
    expect(() => build('coverage-tillage', { field_w: 40, field_h: 40, headland_width: 20 })).toThrow(/为空/);
    expect(() => build('coverage-tillage', { field_w: 600, field_h: 600, swath_width: 0.5 })).toThrow(/幅宽/);
  });
  it('rejects nonfinite and fractional integer parameters', () => {
    expect(() => build('bale-collection', { field_w: NaN })).toThrow();
    expect(() => build('bale-collection', { task_count: 4.2 })).toThrow(/整数/);
  });
  it('does not mark an unlinked historical run as verified evidence', () => {
    for (const p of RUNNABLE_PATTERNS) expect(p.capabilities.experimented.level).toBe('no');
  });
});
