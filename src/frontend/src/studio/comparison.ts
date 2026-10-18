import type { Scenario, Solution, Instance } from '../lab/types';
import { planningFingerprint, stableStringify } from './fleet';
import type { FleetInstance } from './types';

export function inputIdentity(problem: string, instance: Instance | undefined): string {
  return problem === 'fleet_routing' ? planningFingerprint(instance as unknown as FleetInstance | undefined) : stableStringify(instance ?? null);
}

export function currentInput(run: Solution, scenario: Scenario, draft: Instance): boolean {
  return run.scenario_id === scenario.id && !!run.instance && inputIdentity(run.problem_class, run.instance) === inputIdentity(scenario.problem_class, draft);
}

/** A shared axis/green best value requires a common model, units and wall budget. */
export function comparisonKey(run: Solution): string | null {
  if (!run.instance_sha256 || !run.objective?.unit || !run.frame) return null;
  const model = run.planning?.comparison_key ?? stableStringify({
    problem: run.problem_class, input: run.instance_sha256, frame: run.frame,
    unit: run.objective.unit, objective: run.instance && 'objective' in run.instance ? run.instance.objective : null,
    turn_radius_enforced: run.problem_class === 'coverage' ? run.metrics.turn_radius_enforced ?? null : null,
  });
  return JSON.stringify([model, run.objective.unit, run.params.time_limit_s ?? null]);
}

export function comparable(a: Solution, b: Solution): boolean {
  const key = comparisonKey(a);
  return key !== null && key === comparisonKey(b);
}

export function verifiedPlan(run: Solution): boolean {
  return !requiresCoverageRecheck(run) && run.state === 'done' && ['optimal', 'feasible'].includes(run.status ?? '') && run.check?.valid === true
    && (!run.map_check || (run.map_check.checked && run.map_check.collision_free === true))
    && typeof run.objective.value === 'number' && Number.isFinite(run.objective.value);
}

export function requiresCoverageRecheck(run: Solution): boolean {
  return run.algorithm?.id === 'f2c.full' && run.raw_result?.adapter_contract !== 'urp.f2c-full/2';
}

export function resultState(run: Solution): { text: string; title?: string } {
  if (run.state === 'queued') return { text: '排队中' };
  if (run.state === 'running') return { text: '计算中' };
  if (run.state === 'timeout') return { text: '超时', title: run.error ?? '预算内未返回最终解' };
  if (run.state === 'canceled') return { text: '已取消', title: run.error ?? undefined };
  if (run.state !== 'done') return { text: '出错', title: run.error ?? undefined };
  if (requiresCoverageRecheck(run)) return { text: '旧覆盖记录 · 须重求解', title: '旧全流程适配漏掉末段；原始记录保留，不计入新版可行解比较或执行' };
  if (run.status === 'infeasible') return { text: '不可行（求解器报告）', title: run.error ?? run.check?.errors[0] };
  if (run.status === 'no_solution') return { text: '未找到可行解', title: run.error ?? run.check?.errors[0] };
  if (!verifiedPlan(run)) return { text: run.check?.valid === false || run.map_check?.collision_free === false ? '检查未通过' : '有解 · 待检查' };
  return { text: run.status === 'optimal' ? '最优（求解器报告）' : '可行 · 已验算' };
}
