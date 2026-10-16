import type { Frame, SimMode, SimRunState, Solution } from '../types';
import type { Tone } from '../ui';

export const RUN_STATE_LABEL: Record<string, string> = {
  queued: '排队中',
  running: '求解中',
  done: '完成',
  error: '出错',
  timeout: '超时',
  canceled: '已取消',
};

export const SOLVE_STATUS_LABEL: Record<string, string> = {
  optimal: '最优',
  feasible: '可行',
  infeasible: '不可行',
  no_solution: '未找到通过检查的解',
};

export const PROBLEM_CLASS_LABEL: Record<string, string> = {
  turn_routing: '转弯约束路网',
  euclidean_cvrp: '欧氏 CVRP',
  coverage: '覆盖作业',
};

export const COST_UNIT_LABEL: Record<string, string> = {
  cm_equivalent: 'cm 当量',
  synthetic_integer_cost: '合成整数成本',
  euclidean: '欧氏距离（无单位）',
};

export const SIM_MODE_LABEL: Record<SimMode, string> = {
  follow_path: '沿规划路径行驶（FollowPath）',
  nav2_waypoints: 'Nav2 逐点导航（只用任务顺序）',
};

export const SIM_RUN_STATE_LABEL: Record<SimRunState, string> = {
  queued: '排队中',
  approach: '接驳中',
  executing: '执行中',
  succeeded: '成功',
  failed: '失败',
  canceled: '已取消',
};

export const label = (map: Record<string, string>, key: string | null | undefined, empty = '—') =>
  key === null || key === undefined || key === '' ? empty : map[key] ?? key;

export function runTone(run: Pick<Solution, 'state' | 'status'>): Tone {
  if (run.state === 'queued' || run.state === 'running') return 'busy';
  if (run.state === 'error' || run.state === 'timeout') return 'error';
  if (run.state === 'canceled') return 'idle';
  if (run.status === 'optimal' || run.status === 'feasible') return 'ok';
  if (run.status === 'infeasible' || run.status === 'no_solution') return 'warn';
  return 'idle';
}

export function simRunTone(state: SimRunState | string): Tone {
  if (state === 'succeeded') return 'ok';
  if (state === 'failed') return 'error';
  if (state === 'canceled') return 'idle';
  return 'busy';
}

/** Independent checker verdict; a missing check is never shown as a pass. */
export function checkVerdict(run: Pick<Solution, 'check'>): { tone: Tone; mark: string; text: string } {
  if (!run.check) return { tone: 'idle', mark: '–', text: '未检查' };
  return run.check.valid ? { tone: 'ok', mark: '✓', text: '通过' } : { tone: 'error', mark: '✕', text: '未通过' };
}

export function frameLabel(frame: Frame | null | undefined): string {
  if (!frame) return '坐标系未知';
  if (frame.kind === 'map') return `地图坐标 · 米 · ${frame.world}`;
  return frame.kind === 'field' ? '实地坐标 · 米' : '基准坐标 · 无单位';
}

export const lengthUnitLabel = (unit: string | null | undefined) =>
  unit === 'm' ? 'm' : unit === 'unitless' ? '（无单位）' : unit ?? '';

export const shortSha = (sha: string | null | undefined) => (sha ? `${sha.slice(0, 10)}…` : '—');

/* ------------------------------------------------------------ filters -- */

export interface RunFilters {
  scenario: string;
  problemClass: string;
  source: string;
  state: string;
}

export function filterRuns<T extends Pick<Solution, 'scenario_id' | 'problem_class' | 'state' | 'algorithm'>>(
  runs: T[],
  f: RunFilters,
): T[] {
  return runs.filter(
    (r) =>
      (!f.scenario || r.scenario_id === f.scenario) &&
      (!f.problemClass || r.problem_class === f.problemClass) &&
      (!f.source || r.algorithm?.source === f.source) &&
      (!f.state || r.state === f.state),
  );
}

export const distinct = (values: (string | null | undefined)[]) =>
  [...new Set(values.filter((v): v is string => !!v))].sort();

export function newestFirst<T extends { created_utc: string }>(rows: T[]): T[] {
  return [...rows].sort((a, b) => (a.created_utc < b.created_utc ? 1 : a.created_utc > b.created_utc ? -1 : 0));
}

export const parseCompare = (raw: string | null): string[] =>
  raw ? [...new Set(raw.split(',').map((s) => s.trim()).filter(Boolean))] : [];

export function toggleCompare(ids: string[], id: string): string[] {
  return ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id];
}

/* ------------------------------------------------------- comparability -- */

type Comparable = Pick<Solution, 'run_id' | 'scenario_id' | 'instance_sha256' | 'cost_unit'>;

export const comparabilityKey = (r: Comparable) => `${r.scenario_id}\u0000${r.instance_sha256}\u0000${r.cost_unit}`;

/** Why two runs cannot be compared directly (empty when they can). */
export function incomparabilityReasons(a: Comparable, b: Comparable): string[] {
  const reasons: string[] = [];
  if (a.scenario_id !== b.scenario_id) reasons.push(`场景不同（${a.scenario_id} ≠ ${b.scenario_id}）`);
  else if (a.instance_sha256 !== b.instance_sha256)
    reasons.push(`实例不同（实例哈希 ${shortSha(a.instance_sha256)} ≠ ${shortSha(b.instance_sha256)}，任务或参数被编辑过）`);
  if (a.cost_unit !== b.cost_unit)
    reasons.push(`成本单位不同（${label(COST_UNIT_LABEL, a.cost_unit)} ≠ ${label(COST_UNIT_LABEL, b.cost_unit)}）`);
  return reasons;
}

export interface CompareAnalysis {
  /** Run ids grouped by scenario + instance sha + cost unit, largest group first. */
  groups: string[][];
  /** Ids that share a group with at least one other selected run. */
  comparable: Set<string>;
  /** For runs without a comparable partner: why, relative to the largest group. */
  reasons: Record<string, string[]>;
  allComparable: boolean;
}

export function analyzeComparability(runs: Comparable[]): CompareAnalysis {
  const byKey = new Map<string, Comparable[]>();
  for (const r of runs) {
    const k = comparabilityKey(r);
    byKey.set(k, [...(byKey.get(k) ?? []), r]);
  }
  const groups = [...byKey.values()].sort((a, b) => b.length - a.length);
  const comparable = new Set<string>();
  for (const g of groups) if (g.length >= 2) for (const r of g) comparable.add(r.run_id);
  const reference = groups[0]?.[0];
  const reasons: Record<string, string[]> = {};
  for (const r of runs) {
    if (comparable.has(r.run_id) || !reference) continue;
    const other = reference.run_id === r.run_id ? groups.find((g) => g[0].run_id !== r.run_id)?.[0] : reference;
    reasons[r.run_id] = other ? incomparabilityReasons(r, other) : [];
  }
  return {
    groups: groups.map((g) => g.map((r) => r.run_id)),
    comparable,
    reasons,
    allComparable: runs.length >= 2 && groups.length === 1,
  };
}

/* ------------------------------------------------------ compare metrics -- */

export interface CompareMetric {
  key: string;
  label: string;
  value: (r: Solution) => number | null;
  unit: (r: Solution) => string;
  /** Lower is better; null = descriptive only, never highlighted. */
  better: 'min' | null;
  /** Quality metrics only count runs with a feasible, checker-validated solution. */
  needsValidSolution: boolean;
}

const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);

export const COMPARE_METRICS: CompareMetric[] = [
  {
    key: 'objective',
    label: '目标值',
    value: (r) => num(r.objective?.value),
    unit: (r) => label(COST_UNIT_LABEL, r.objective?.unit ?? r.cost_unit, ''),
    better: 'min',
    needsValidSolution: true,
  },
  {
    key: 'lower_bound',
    label: '下界',
    value: (r) => num(r.objective?.lower_bound),
    unit: (r) => label(COST_UNIT_LABEL, r.objective?.unit ?? r.cost_unit, ''),
    better: null,
    needsValidSolution: false,
  },
  {
    key: 'length',
    label: '路线长度',
    value: (r) => num(r.metrics?.length),
    unit: (r) => lengthUnitLabel(r.metrics?.length_unit),
    better: 'min',
    needsValidSolution: true,
  },
  { key: 'n_routes', label: '路线数', value: (r) => num(r.metrics?.n_routes), unit: () => '', better: null, needsValidSolution: false },
  { key: 'n_tasks', label: '任务数', value: (r) => num(r.metrics?.n_tasks), unit: () => '', better: null, needsValidSolution: false },
  { key: 'turns', label: '转弯次数', value: (r) => num(r.metrics?.turns), unit: () => '', better: 'min', needsValidSolution: true },
  {
    key: 'turn_penalty_total',
    label: '转弯惩罚合计',
    value: (r) => num(r.metrics?.turn_penalty_total),
    unit: (r) => label(COST_UNIT_LABEL, r.cost_unit, ''),
    better: 'min',
    needsValidSolution: true,
  },
  {
    key: 'forbidden_turn_violations',
    label: '禁止转弯违例',
    value: (r) => num(r.metrics?.forbidden_turn_violations),
    unit: () => '',
    better: 'min',
    needsValidSolution: true,
  },
  { key: 'wall_s', label: '墙钟时间', value: (r) => num(r.metrics?.wall_s), unit: () => 's', better: 'min', needsValidSolution: false },
  { key: 'cpu_s', label: 'CPU 时间', value: (r) => num(r.metrics?.cpu_s), unit: () => 's', better: 'min', needsValidSolution: false },
];

export const hasValidSolution = (r: Pick<Solution, 'state' | 'status' | 'check'>) =>
  r.state === 'done' && (r.status === 'optimal' || r.status === 'feasible') && r.check?.valid === true;

/**
 * Best values, marked only inside a comparable group and only when at least two
 * eligible runs report a value. Returns metric key → run ids holding the best value.
 */
export function bestValues(runs: Solution[], analysis: CompareAnalysis): Record<string, Set<string>> {
  const byId = new Map(runs.map((r) => [r.run_id, r]));
  const out: Record<string, Set<string>> = {};
  for (const m of COMPARE_METRICS) {
    out[m.key] = new Set();
    if (!m.better) continue;
    for (const ids of analysis.groups) {
      if (ids.length < 2) continue;
      const candidates = ids
        .map((id) => byId.get(id))
        .filter((r): r is Solution => !!r && (m.needsValidSolution ? hasValidSolution(r) : r.state === 'done'))
        .map((r) => ({ id: r.run_id, v: m.value(r) }))
        .filter((c): c is { id: string; v: number } => c.v !== null);
      if (candidates.length < 2) continue;
      const best = Math.min(...candidates.map((c) => c.v));
      for (const c of candidates) if (c.v === best) out[m.key].add(c.id);
    }
  }
  return out;
}
