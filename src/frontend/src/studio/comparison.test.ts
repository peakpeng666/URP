import { describe, expect, it } from 'vitest';
import type { Solution } from '../lab/types';
import { comparable, resultState, verifiedPlan } from './comparison';

const run = () => ({
  run_id: 'one', problem_class: 'euclidean_cvrp', instance_sha256: 'complete-hash',
  frame: { kind: 'benchmark', units: 'unitless' }, instance: { objective: 'sum_unrounded_euclidean_distance' },
  state: 'done', status: 'feasible', routes: [{}], check: { valid: true, errors: [] }, map_check: null,
  objective: { value: 10, unit: 'euclidean' }, metrics: {}, params: { time_limit_s: 2 },
}) as unknown as Solution;

describe('scientific plan comparison', () => {
  it('requires identical units, inputs, distance rules, frames and budgets', () => {
    expect(comparable(run(), run())).toBe(true);
    for (const mutation of [
      { objective: { value: 10, unit: 'm' } }, { instance_sha256: 'another-hash' },
      { instance: { objective: 'sum_rounded_euclidean_distance' } },
      { frame: { kind: 'field', units: 'm' } }, { params: { time_limit_s: 3 } },
    ]) expect(comparable(run(), { ...run(), ...mutation } as Solution)).toBe(false);
  });
  it('never treats a failed map check or no-solution result as a verified plan', () => {
    expect(verifiedPlan(run())).toBe(true);
    expect(verifiedPlan({ ...run(), map_check: { checked: true, collision_free: false } as Solution['map_check'] })).toBe(false);
    expect(resultState({ ...run(), status: 'no_solution' }).text).toBe('未找到可行解');
    expect(verifiedPlan({ ...run(), check: null })).toBe(false);
    expect(comparable({ ...run(), instance_sha256: '' }, run())).toBe(false);
  });
  it('retains old full coverage records without ranking or executing their truncated geometry', () => {
    const old = { ...run(), problem_class: 'coverage', algorithm: { id: 'f2c.full' } } as Solution;
    expect(verifiedPlan(old)).toBe(false);
    expect(resultState(old).text).toContain('须重求解');
    expect(verifiedPlan({ ...old, raw_result: { adapter_contract: 'urp.f2c-full/2' } })).toBe(true);
  });
});
