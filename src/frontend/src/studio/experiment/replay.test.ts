import { describe, expect, it } from 'vitest';
import { derive, metricsAt, poseAt, taskEvents, type SimResult, type TrailPoint } from './replay';

const trail: TrailPoint[] = [[10, 0, 0, 0], [20, 10, 0, 0], [30, 20, 0, 0]];
const result = {
  tasks: [{ vehicle: 'vehicle_0', id: 1, label: 'T1', xy: [10, 0], stop: [10, 0], state: 'reached', t_sim: 20, distance_m: null, serviced_at: 25, service_complete: true }],
  trails: { vehicle_0: trail },
  vehicles: [],
  execution_plan: { vehicles: [{ name: 'vehicle_0', path: [[0, 0], [20, 0]] }] },
} as unknown as SimResult;

describe('recorded replay time boundaries', () => {
  it('does not invent poses outside the recorded time interval', () => {
    expect(poseAt(trail, 9.999)).toBeNull();
    expect(poseAt(trail, 30.001)).toBeNull();
    expect(poseAt(trail, 15)).toEqual([5, 0, 0]);
    const noOverlap = {
      ...result,
      tasks: [],
      trails: { a: trail, b: [[40, 100, 0, 0], [50, 110, 0, 0]] as TrailPoint[] },
    } as unknown as SimResult;
    expect(derive(noOverlap).separation).toBeNull();
  });

  it('aligns cumulative metrics with arrival and service-completion events', () => {
    expect(taskEvents(result).map((event) => [event.kind, event.t])).toEqual([['reached', 20], ['completed', 25]]);
    const atArrival = metricsAt(result, 'vehicle_0', 20);
    expect(atArrival).toMatchObject({ distance_m: 10, elapsed_s: 10, tasks_reached: 1, tasks_completed: 0, cross_track_mean_m: 0, cross_track_max_m: 0 });
    const atCompletion = metricsAt(result, 'vehicle_0', 25);
    expect(atCompletion).toMatchObject({ distance_m: 15, elapsed_s: 15, tasks_reached: 1, tasks_completed: 1 });
  });
});
