import { describe, expect, it } from 'vitest';
import type { FleetInstance } from './types';
import { depotsOf, fleetClassFor, normalizeFleetInstance, planningFingerprint, setDepot, stableStringify } from './fleet';

const base: FleetInstance = {
  boundary: [[0, 0], [60, 0], [60, 40], [0, 40]],
  plots: [],
  obstacles: [],
  depot: [3, 15],
  tasks: [
    { id: 1, xy: [20, 15], demand: 1, label: 'T1', service_s: 5 },
    { id: 2, xy: [40, 25], demand: 1, label: 'T2', service_s: 0 },
  ],
  vehicles: { count: 2, capacity: 4, speed_mps: 1, trips: 'multi', travel: 'free', names: ['一', '二'] },
  objective: 'makespan',
  robot_radius: 0.5,
  units: 'm',
};

const clone = () => structuredClone(base);

describe('fleet draft compatibility', () => {
  it('keeps depot and depots[0] synchronized for a legacy single-depot edit', () => {
    const edited = setDepot(clone(), 0, [10, 15]);
    expect(edited.depot).toEqual([10, 15]);
    expect(edited.depots).toEqual([[10, 15]]);
    expect(normalizeFleetInstance(edited)).toMatchObject({ depot: [10, 15], depots: [[10, 15]] });
  });

  it('edits the selected depot without reordering other depots', () => {
    const multi = clone();
    multi.depots = [[3, 15], [30, 15], [55, 25]];
    multi.depot = [3, 15];
    const edited = setDepot(multi, 1, [32, 18]);
    expect(depotsOf(edited)).toEqual([[3, 15], [32, 18], [55, 25]]);
    expect(edited.depot).toEqual([3, 15]);
  });

  it('removes conflicting legacy fleet fields only when fleet classes are present', () => {
    const changed = clone();
    changed.vehicles.fleet = [{ count: 1, capacity: 4, speed_mps: 1, robot_radius: 0.5, payload: 'load' }];
    const normalized = normalizeFleetInstance(changed);
    expect(normalized.vehicles.count).toBeUndefined();
    expect(normalized.vehicles.capacity).toBeUndefined();
    expect(normalized.vehicles.names).toBeUndefined();
    expect(normalized.vehicles.fleet).toHaveLength(1);
  });
});

describe('complete planning input fingerprint', () => {
  it('changes for service time, depots, unload points, corridors and fleet classes', () => {
    const before = planningFingerprint(base);
    const changes: ((value: FleetInstance) => void)[] = [
      (value) => { value.tasks[0].service_s = 35; },
      (value) => { value.depots = [[3, 15], [55, 25]]; },
      (value) => { value.unload_points = [[35, 15]]; },
      (value) => { value.corridors = [{ id: 'C1', polygon: [[0, 0], [5, 0], [5, 5]] }]; },
      (value) => { value.vehicles.fleet = [{ count: 1, capacity: 4, speed_mps: 0.8, robot_radius: 0.6, payload: 'load' }]; },
    ];
    for (const change of changes) {
      const value = clone();
      change(value);
      expect(planningFingerprint(value)).not.toBe(before);
    }
  });

  it('is stable across object key order and depot alias representation', () => {
    const normalized = normalizeFleetInstance(clone());
    expect(planningFingerprint(normalized)).toBe(planningFingerprint(base));
    expect(stableStringify({ b: 1, a: [2, { d: 4, c: 3 }] })).toBe(stableStringify({ a: [2, { c: 3, d: 4 }], b: 1 }));
  });

  it('includes future solver fields instead of relying on a hand-picked field list', () => {
    const extended = clone() as FleetInstance & { future_solver_option?: { enabled: boolean } };
    extended.future_solver_option = { enabled: true };
    expect(planningFingerprint(extended)).not.toBe(planningFingerprint(base));
  });
});

describe('fleet class result compatibility', () => {
  it('resolves backend class names and historical numeric indexes without changing capacities', () => {
    const hetero = clone();
    hetero.vehicles.fleet = [
      { name: '小型', count: 1, capacity: 1, payload: 'load' },
      { name: '大型', count: 1, capacity: 10, payload: 'load' },
    ];
    hetero.tasks[1].demand = 10;
    expect(fleetClassFor(hetero, '小型')?.capacity).toBe(1);
    expect(fleetClassFor(hetero, '大型')?.capacity).toBe(10);
    expect(fleetClassFor(hetero, 1)?.name).toBe('大型');
    expect(fleetClassFor(hetero, undefined)).toBeUndefined();
    expect(fleetClassFor(hetero, '小型')).not.toBe(fleetClassFor(hetero, '大型'));
    expect(hetero.vehicles.fleet.map((item) => item.capacity)).toEqual([1, 10]);
    expect(hetero.tasks.map((item) => item.demand)).toEqual([1, 10]);
  });
});
