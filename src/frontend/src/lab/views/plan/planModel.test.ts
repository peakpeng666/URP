import { describe, expect, it } from 'vitest';
import type { Algorithm, EuclideanCvrpInstance, Scenario, Solution, TurnRoutingInstance } from '../../types';
import {
  addCvrpPoint,
  baseScene,
  coerceParams,
  groupScenarios,
  instanceKey,
  paramError,
  relation,
  removeCvrpPoint,
  serviceOrder,
  setCvrpDepot,
  setDemand,
  setTurnDepot,
  simBlockReason,
  solutionPaths,
  stableStringify,
  taskRows,
  toggleTurnTask,
  violationMarkers,
} from './planModel';

const turn: TurnRoutingInstance = {
  depot: 0,
  capacity: 3,
  customers: [
    { id: 0, node: 2, demand: 1, label: 'A' },
    { id: 1, node: 3, demand: 2, label: 'B' },
  ],
  arcs: [
    [0, 1, 1],
    [1, 0, 1],
    [1, 2, 1],
    [2, 3, 1],
    [3, 0, 1],
  ],
  forbidden_turns: [[0, 1, 0]],
  turn_penalties: [[1, 2, 3, 5]],
  coordinates: { '0': [0, 0], '1': [1, 0], '2': [1, 1], '3': [0, 1] },
  units: 'synthetic_integer_cost',
};

const cvrp: EuclideanCvrpInstance = {
  coordinates: [
    [0, 0],
    [3, 4],
    [6, 8],
  ],
  demands: [0, 2, 3],
  capacity: 10,
  depot: 0,
  fleet: 'unlimited_identical_vehicles',
  objective: 'sum_unrounded_euclidean_distance',
  labels: ['D', '1', '2'],
};

const scenario = (problem_class: Scenario['problem_class'], instance: Scenario['instance'], frame: Scenario['frame'] = { kind: 'benchmark', units: 'unitless' }): Scenario => ({
  id: 's',
  title: 't',
  summary: '',
  problem_class,
  frame,
  cost_unit: 'synthetic_integer_cost',
  sim: { supported: false, world: null, spawn: null, reason: '基准坐标' },
  task_count: 2,
  node_count: 4,
  provenance: { generator: 'test' },
  instance,
  editable: { tasks: true },
});

const solution = (over: Partial<Solution> = {}): Solution => ({
  run_id: 'run_1',
  job_id: 'job_1',
  scenario_id: 's',
  problem_class: 'turn_routing',
  instance_sha256: 'abc',
  frame: { kind: 'map', units: 'm', world: 'warehouse', map: { world: 'warehouse', resolution: 0.03, origin: [0, 0, 0], width: 10, height: 10, image: '', yaml: '' } },
  cost_unit: 'cm_equivalent',
  algorithm: { id: 'urp.turn_mode_dp', name: 'DP', source: 'project', origin: 'x', version: null },
  params: {},
  state: 'done',
  status: 'optimal',
  objective: { value: 10, unit: 'cm_equivalent', lower_bound: null },
  routes: [{ vehicle: 0, nodes: [0, 1, 2, 3, 0], sequence: [0, 1], services: [{ task: 1, position: 3 }, { task: 0, position: 2 }], polyline: [], cost: 10, load: 3 }],
  check: { checker: 'checker.py', source: 'project', valid: true, errors: [], computed_cost: 10 },
  map_check: { checked: true, collision_free: true, min_clearance_m: 0.5, robot_radius_m: 0.175, violations: [] },
  metrics: { cost: 10, length: 4, length_unit: 'm', n_routes: 1, n_tasks: 2, turns: 3, turn_penalty_total: 5, forbidden_turn_violations: 0, wall_s: 0.1, cpu_s: 0.1 },
  log: null,
  error: null,
  created_utc: '',
  finished_utc: null,
  label: null,
  ...over,
});

describe('scenario grouping', () => {
  it('groups by problem class in a fixed order and drops empty groups', () => {
    const groups = groupScenarios([
      { ...scenario('coverage', cvrp), id: 'c' },
      { ...scenario('turn_routing', turn), id: 't' },
    ]);
    expect(groups.map((g) => g.label)).toEqual(['转弯约束路网', '覆盖作业']);
  });
});

describe('instance identity', () => {
  it('ignores key order and changes with content', () => {
    expect(stableStringify({ b: 1, a: [1, { d: 2, c: 3 }] })).toBe('{"a":[1,{"c":3,"d":2}],"b":1}');
    expect(instanceKey({ ...turn })).toBe(instanceKey(turn));
    expect(instanceKey(toggleTurnTask(turn, 1))).not.toBe(instanceKey(turn));
  });

  it('classifies results against the current instance', () => {
    const shas = new Map([['k1', 'sha1']]);
    expect(relation('k1', 'k1', null, shas)).toBe('current');
    expect(relation('k0', 'k1', null, shas)).toBe('stale');
    expect(relation(null, 'k1', 'sha1', shas)).toBe('current');
    expect(relation(null, 'k1', 'sha2', shas)).toBe('stale');
    expect(relation(null, 'k2', 'sha1', shas)).toBe('unknown');
  });
});

describe('editing', () => {
  it('toggles turn-routing tasks and renumbers ids', () => {
    const added = toggleTurnTask(turn, 1);
    expect(added.customers.map((c) => [c.id, c.node])).toEqual([
      [0, 2],
      [1, 3],
      [2, 1],
    ]);
    const removed = toggleTurnTask(added, 2);
    expect(removed.customers.map((c) => [c.id, c.node])).toEqual([
      [0, 3],
      [1, 1],
    ]);
    expect(toggleTurnTask(turn, 0)).toBe(turn);
  });

  it('moving the depot onto a task drops that task', () => {
    const d = setTurnDepot(turn, 2);
    expect(d.depot).toBe(2);
    expect(d.customers.map((c) => c.node)).toEqual([3]);
  });

  it('adds, removes and edits CVRP points without touching the depot index', () => {
    const a = addCvrpPoint(cvrp, [1.234, 5.678]);
    expect(a.coordinates.at(-1)).toEqual([1.23, 5.68]);
    expect(a.demands).toEqual([0, 2, 3, 1]);
    expect(a.labels).toEqual(['D', '1', '2', '3']);
    const r = removeCvrpPoint(a, 1);
    expect(r.coordinates).toEqual([[0, 0], [6, 8], [1.23, 5.68]]);
    expect(r.demands).toEqual([0, 3, 1]);
    expect(removeCvrpPoint(a, 0)).toBe(a);
    expect(setCvrpDepot(cvrp, [9, 9]).coordinates[0]).toEqual([9, 9]);
    expect((setDemand('euclidean_cvrp', cvrp, 2, 7) as EuclideanCvrpInstance).demands).toEqual([0, 2, 7]);
    expect((setDemand('turn_routing', turn, 1, 4) as TurnRoutingInstance).customers[1].demand).toBe(4);
  });

  it('lists tasks with coordinates', () => {
    expect(taskRows('turn_routing', turn).map((t) => [t.label, t.xy])).toEqual([
      ['A', [1, 1]],
      ['B', [0, 1]],
    ]);
    expect(taskRows('euclidean_cvrp', cvrp).map((t) => t.id)).toEqual([1, 2]);
  });
});

describe('scene', () => {
  it('draws two-way arcs once and keeps one-way arcs directed', () => {
    const scene = baseScene(scenario('turn_routing', turn), turn);
    expect(scene.arcs).toHaveLength(4);
    expect(scene.arcs!.filter((a) => a.oneWay)).toHaveLength(3);
    expect(scene.nodes!.find((n) => n.id === '0')!.kind).toBe('depot');
    expect(scene.nodes!.find((n) => n.id === '2')!.kind).toBe('task');
    expect(scene.nodes!.find((n) => n.id === '1')!.kind).toBe('other');
    expect(scene.turnHints!('1')).toHaveLength(1);
    expect(scene.units).toBe('unitless');
  });

  it('resolves service order through task ids', () => {
    const route = solution().routes[0];
    expect(serviceOrder('turn_routing', turn, route)).toEqual([
      { xy: [1, 1], text: '1' },
      { xy: [0, 1], text: '2' },
    ]);
    expect(serviceOrder('euclidean_cvrp', cvrp, { ...route, services: [], nodes: [0, 2, 1, 0] }).map((o) => o.xy)).toEqual([
      [6, 8],
      [3, 4],
    ]);
  });

  it('colours per route alone and per result when comparing; stale results are dashed without order', () => {
    const a = solution();
    const b = solution({ run_id: 'run_2', routes: [a.routes[0], a.routes[0]] });
    const single = solutionPaths([{ solution: b, colorIndex: 4, current: true, focused: true }], 'turn_routing', turn, null);
    expect(single.map((p) => p.color)).toEqual(['var(--route-1)', 'var(--route-2)']);
    const both = solutionPaths(
      [
        { solution: a, colorIndex: 0, current: true, focused: true },
        { solution: b, colorIndex: 2, current: false, focused: false },
      ],
      'turn_routing',
      turn,
      null,
    );
    expect(both.map((p) => p.color)).toEqual(['var(--route-1)', 'var(--route-3)', 'var(--route-3)']);
    expect(both[0].order).toHaveLength(2);
    expect(both[1].order).toBeUndefined();
    expect(both[1].dash).toBeDefined();
  });

  it('marks map-check violations', () => {
    const s = solution({ map_check: { checked: true, collision_free: false, min_clearance_m: 0.1, robot_radius_m: 0.175, violations: [{ route: 0, segment: 4, point: [1, 2], clearance_m: 0.1 }] } });
    const m = violationMarkers([s]);
    expect(m).toHaveLength(1);
    expect(m[0].title).toContain('第 5 段');
  });
});

describe('simulation gate', () => {
  it('requires map frame, routes and a valid independent check', () => {
    expect(simBlockReason(solution(), { supported: true, world: 'warehouse', spawn: null, reason: null })).toBeNull();
    expect(simBlockReason(solution({ frame: { kind: 'benchmark', units: 'unitless' } }), null)).toContain('基准坐标');
    expect(simBlockReason(solution({ check: null }), null)).toContain('未经独立检查');
    expect(simBlockReason(solution({ routes: [] }), null)).toContain('没有路线');
    expect(simBlockReason(solution({ check: { checker: 'c', source: 'project', valid: false, errors: ['x'], computed_cost: null } }), null)).toContain('无效');
    expect(simBlockReason(solution(), { supported: false, world: null, spawn: null, reason: '世界不可用' })).toBe('世界不可用');
  });
});

describe('params', () => {
  const alg = {
    params: [
      { name: 'time_limit_s', type: 'number', default: 5, min: 0.5, max: 120, label: 't' },
      { name: 'seed', type: 'integer', default: 1, min: 0, label: 's' },
    ],
  } as unknown as Algorithm;

  it('validates ranges and integers', () => {
    expect(paramError(alg.params[0], 200)).toBe('不大于 120');
    expect(paramError(alg.params[0], 0.1)).toBe('不小于 0.5');
    expect(paramError(alg.params[1], 1.5)).toBe('需要整数');
    expect(paramError(alg.params[0], 10)).toBeNull();
  });

  it('coerces with defaults', () => {
    expect(coerceParams(alg, { time_limit_s: '7' as unknown as number })).toEqual({ time_limit_s: 7, seed: 1 });
  });
});
