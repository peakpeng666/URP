import { describe, expect, it } from 'vitest';
import { playbackDistanceAtTime, playbackDuration } from './planningPlayback';
import type { FleetInstance, FleetRoute } from './types';

const inst = {
  boundary: [[0, 0], [20, 0], [20, 20], [0, 20]],
  plots: [], obstacles: [], depot: [0, 0],
  tasks: [{ id: 1, xy: [10, 0], demand: 1, label: 'T1', service_s: 10 }],
  vehicles: { count: 2, capacity: 4, speed_mps: 1, travel: 'free', fleet: [
    { name: '慢车', count: 1, capacity: 4, speed_mps: 1, payload: 'load' },
    { name: '快车', count: 1, capacity: 4, speed_mps: 2, payload: 'load' },
  ] },
  objective: 'total_distance', robot_radius: 0.5, units: 'm',
} as FleetInstance;

const route = {
  vehicle: 0, vehicle_name: '快车', color: '#000', trips: [[1]], nodes: null,
  sequence: [1], services: [{ task: 1, position: 1 }], polyline: [[0, 0], [10, 0], [10, 10]],
  cost: 20, load: 1, fleet_class: '快车', speed_mps: 2, duration_s: 20,
} as FleetRoute;

describe('fleet planning preview timing', () => {
  it('uses the route speed and holds position during recorded task service time', () => {
    expect(playbackDistanceAtTime(inst, route, 2.5)).toBe(5);
    expect(playbackDistanceAtTime(inst, route, 5)).toBe(10);
    expect(playbackDistanceAtTime(inst, route, 12)).toBe(10);
    expect(playbackDistanceAtTime(inst, route, 17.5)).toBe(15);
    expect(playbackDistanceAtTime(inst, route, 20)).toBe(20);
  });

  it('uses the longest route duration instead of one shared fleet speed', () => {
    const slow = { ...route, vehicle_name: '慢车', fleet_class: '慢车', speed_mps: 1, services: [], duration_s: 20 };
    expect(playbackDuration(inst, [route, slow])).toBe(20);
    expect(playbackDuration(inst, [{ ...route, duration_s: Number.NaN }])).toBe(20);
  });
});
