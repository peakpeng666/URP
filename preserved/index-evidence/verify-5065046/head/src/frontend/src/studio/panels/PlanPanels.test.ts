import { afterEach, describe, expect, it, vi } from 'vitest';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import type { Scenario, Solution } from '../../lab/types';
vi.mock('../../lab/api', async (load) => ({ ...await load<typeof import('../../lab/api')>(), events: { subscribe: vi.fn() } }));
vi.mock('../store', async (load) => {
  const actual = await load<typeof import('../store')>();
  // Server rendering otherwise reads Zustand's initial snapshot, not the test's
  // loaded run. Render the actual panel against an explicit current snapshot.
  return { ...actual, useStudio: Object.assign((select?: (state: ReturnType<typeof actual.useStudio.getState>) => unknown) =>
    select ? select(actual.useStudio.getState()) : actual.useStudio.getState(), actual.useStudio) };
});
import { useStudio } from '../store';
import { ComparePanel } from './PlanPanels';
import { ExperimentPanel } from '../experiment/ExperimentPanel';

const initial = useStudio.getState();
afterEach(() => useStudio.setState(initial, true));

describe('actual comparison panel across problem families', () => {
  it.each(['point_to_point', 'coverage', 'turn_routing', 'euclidean_cvrp'] as const)('renders %s without assuming a fleet instance', (problem) => {
    const instance = problem === 'point_to_point' ? { start: [0, 0, 0], goal: [1, 1, 0] } : { capacity: 3 };
    const r = { run_id: 'run-one', scenario_id: 'scene', problem_class: problem, instance, instance_sha256: 'hash',
      frame: { kind: 'benchmark', units: 'unitless' }, objective: { value: 2, unit: 'unitless' },
      state: 'done', status: 'feasible', check: { valid: true, errors: [] }, map_check: null,
      routes: [{ polyline: [[0, 0], [1, 1]] }], params: {}, metrics: {}, algorithm: { id: 'test', name: '测试算法' },
    } as unknown as Solution;
    useStudio.setState({ scenario: { id: 'scene', problem_class: problem } as Scenario, draft: instance,
      runIds: [r.run_id], runs: { [r.run_id]: r }, focusRun: r.run_id, algorithms: [] });
    expect(renderToStaticMarkup(createElement(ComparePanel))).toContain('可行 · 已验算');
  });
});

describe('actual experiment panel with legacy and abstract fleet fields', () => {
  it.each([
    ['euclidean_cvrp', 'unlimited_identical_vehicles', '绑定的场景与资产版本'],
    ['turn_routing', { asset: { id: 'old-vehicle' } }, '旧绑定未记录忽略字段'],
  ] as const)('renders %s without assuming fleet is a complete asset binding', (problem, fleet, expected) => {
    const r = { run_id: 'legacy-one', scenario_id: 'scene', problem_class: problem,
      instance: { fleet }, instance_sha256: 'hash', state: 'done', status: 'feasible',
      check: { valid: true, errors: [] }, objective: { value: 2, unit: 'unitless' },
      algorithm: { id: 'test', name: '历史算法' }, metrics: {}, params: {},
    } as unknown as Solution;
    useStudio.setState({ scenario: { id: 'scene', problem_class: problem } as Scenario,
      focusRun: r.run_id, runs: { [r.run_id]: r } });
    expect(renderToStaticMarkup(createElement(ExperimentPanel))).toContain(expected);
  });
});
