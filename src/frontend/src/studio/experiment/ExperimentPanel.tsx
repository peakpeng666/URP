/**
 * Experiment result of the focused solution: plan metrics with explicit denominators, independent check,
 * the matching field simulation (tracking error, arrivals, closest approach) and an export that binds the
 * record to the scenario and to the exact asset versions it used.
 */
import { useEffect, useMemo, useState } from 'react';
import { Download, FlaskConical } from 'lucide-react';
import { exportUrl, fmt } from '../../lab/api';
import type { Solution } from '../../lab/types';
import { Badge, Button, EmptyState, Spinner } from '../../lab/ui';
import { studio, urls } from '../api';
import { isFleet, useStudio } from '../store';
import type { FieldSimSummary, FleetInstance, PerVehicle } from '../types';
import type { AssetRef } from '../assets/api';
import type { FleetAssetBinding } from '../assets/planBridge';
import { derive, useReplay, type Derived, type SimResult } from './replay';
import p from '../panels/panels.module.css';
import a from '../assets/assets.module.css';

type Run = Solution & { recommendation_at_submission?: Record<string, unknown>; reproducibility?: Record<string, unknown> };
type Tone = 'good' | 'warn' | 'bad' | undefined;

function Cell({ label, value, note, tone }: { label: string; value: string; note?: string; tone?: Tone }) {
  return <div className={a.metricCell} data-tone={tone}><span>{label}</span><b>{value}</b>{note && <small>{note}</small>}</div>;
}

export function ExperimentPanel() {
  const st = useStudio();
  const run = (st.focusRun ? st.runs[st.focusRun] : undefined) as Run | undefined;
  const [sims, setSims] = useState<FieldSimSummary[] | null>(null);
  const [sim, setSim] = useState<{ r: SimResult; d: Derived } | null>(null);
  const [simLoading, setSimLoading] = useState(false);
  useEffect(() => {
    setSims(null);
    setSim(null);
    if (!run || run.problem_class !== 'fleet_routing' || run.state !== 'done') return;
    let alive = true;
    studio.fieldsimResults(run.run_id).then((x) => alive && setSims(x.results)).catch(() => alive && setSims([]));
    return () => { alive = false; };
  }, [run?.run_id, run?.state]); // eslint-disable-line react-hooks/exhaustive-deps
  const latest = sims?.[0];
  useEffect(() => {
    if (!latest) return;
    let alive = true;
    setSimLoading(true);
    fetch(urls.fieldsimResult(latest.session_id), { cache: 'no-store' }).then((r) => r.json()).then((r: SimResult) => {
      if (alive) setSim({ r, d: derive(r) });
    }).catch(() => undefined).finally(() => alive && setSimLoading(false));
    return () => { alive = false; };
  }, [latest?.session_id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!st.scenario) return <EmptyState icon={FlaskConical} title="未打开场景" />;
  if (!run) return <EmptyState icon={FlaskConical} title="选择一个方案" detail="求解后在「方案对比」里点一个方案，这里汇总它的规划指标、验算、仿真执行与可导出的实验记录。" />;
  if (run.state !== 'done') return <EmptyState title={run.error ?? '方案还在计算'} />;
  const fleet = run.problem_class === 'fleet_routing';
  return (
    <div className={p.scroll}>
      <div className={p.form}>
        <div className={p.rowSpace}>
          <h3>{run.algorithm.name} · 实验结果</h3>
          <ExportButton run={run} sim={sim} sims={sims} />
        </div>
        {fleet ? <FleetMetrics run={run} sim={sim} simLoading={simLoading} hasSims={!!sims?.length} /> : <GenericMetrics run={run} />}
        <AssetBinding run={run} />
      </div>
    </div>
  );
}

function FleetMetrics({ run, sim, simLoading, hasSims }: { run: Run; sim: { r: SimResult; d: Derived } | null; simLoading: boolean; hasSims: boolean }) {
  const inst = run.instance as unknown as FleetInstance;
  const per = (run.metrics.per_vehicle as unknown as PerVehicle[] | undefined) ?? [];
  const total = inst?.tasks?.length ?? 0;
  const served = per.reduce((x, v) => x + v.tasks, 0);
  const errors = run.check?.errors ?? [];
  const maxLoad = per.length ? Math.max(...per.map((v) => v.load)) : null;
  const m = sim?.r.metrics;
  const sep = sim?.d.separation;
  return (
    <>
      <h3>规划（求解器输出，经独立验算）</h3>
      <div className={a.metricGrid}>
        <Cell label="任务完成率（规划）" value={total ? `${fmt.num((100 * served) / total, 1)}%` : '—'} note={`${served} / ${total}，分母：任务地图中的全部任务点`} tone={served === total ? 'good' : 'bad'} />
        <Cell label="总里程" value={`${fmt.num(run.metrics.total_distance_m as number, 1)} m`} note="各车路线长度之和（验算复算）" />
        <Cell label="最晚完成" value={fmt.sec(run.metrics.makespan_s as number)} note={`按车速 ${inst?.vehicles?.speed_mps} m/s 与作业时间换算`} />
        <Cell label="趟数 / 返库" value={`${fmt.num(run.metrics.trips as number, 0)} 趟`} note={`每趟结束回车库卸载；单趟最大载重 ${maxLoad ?? '—'} / 容量 ${inst?.vehicles?.capacity}`} tone={maxLoad != null && maxLoad > inst?.vehicles?.capacity ? 'bad' : undefined} />
        <Cell label="约束违规" value={run.check ? String(errors.length) : '未验算'} note={run.check ? (errors.length ? errors.slice(0, 2).join('；') : `验算方：${run.check.checker ?? '独立检查器'}`) : ''} tone={run.check ? (errors.length ? 'bad' : 'good') : 'warn'} />
        <Cell label="使用车辆" value={`${fmt.num(run.metrics.vehicles_used as number, 0)} / ${inst?.vehicles?.count}`} note={`分工均衡度（变异系数）${fmt.num(run.metrics.balance_cv as number, 2)}`} />
        <Cell label="覆盖率" value="不适用" note="多车任务按任务点计完成率；覆盖率只对覆盖作业（分母：田块面积）计算" />
        <Cell label="计算时间" value={fmt.sec(run.metrics.wall_s)} note={run.params?.time_limit_s != null ? `预算 ${run.params.time_limit_s} s` : ''} />
      </div>
      <h3>仿真执行（Gazebo 田间仿真）</h3>
      {simLoading && <Spinner />}
      {!simLoading && !hasSims && <p className={p.hint}>这个方案还没有在仿真中执行（「方案对比」里点 Gazebo）。跟踪误差与多车间距只有执行后才有。</p>}
      {sim && m && (
        <>
          <div className={a.metricGrid}>
            <Cell label="任务到达率（仿真）" value={`${fmt.num((100 * m.tasks_reached) / Math.max(1, m.tasks_total), 1)}%`} note={`${m.tasks_reached} / ${m.tasks_total}，分母：方案分配给各车的任务点`} tone={m.tasks_reached === m.tasks_total ? 'good' : 'bad'} />
            <Cell label="实际总里程" value={`${fmt.num(m.total_distance_m, 1)} m`} note={`规划 ${fmt.num(m.planned_total_distance_m, 1)} m`} />
            <Cell label="实际最晚完成" value={fmt.sec(m.makespan_s)} note={`规划 ${fmt.sec(m.planned_makespan_s)}（仿真时间）`} />
            <Cell label="路径跟踪误差" value={`${fmt.num(m.cross_track_mean_m, 3)} m`} note={`最大 ${fmt.num(m.cross_track_max_m, 2)} m；真值位置到跟踪路线的横向距离`} tone={m.cross_track_max_m > 0.5 ? 'warn' : 'good'} />
            <Cell label="多车避碰" value="未验收" tone="warn" note={`${sep ? `实测最近车距 ${sep.d.toFixed(2)} m（t=${sep.t.toFixed(0)} s）；` : ''}规划不建模车间冲突，仿真屏蔽车间碰撞且不做避让`} />
            <Cell label="异常" value={String(sim.d.anomalies.length)} note={sim.d.anomalies.slice(0, 2).map((x) => x.text).join('；') || '无'} tone={sim.d.anomalies.some((x) => x.tone === 'error') ? 'bad' : sim.d.anomalies.length ? 'warn' : 'good'} />
          </div>
          <div className={p.row}>
            <span className={p.meta} style={{ margin: 0 }}>执行：纯追踪路径跟踪（非 Nav2 重规划）· 定位：Gazebo 真值 · 会话 {sim.r.session_id}</span>
            <span className={p.spacer} />
            <Button size="sm" onClick={() => { void useReplay.getState().load(sim.r.session_id); window.dispatchEvent(new CustomEvent('studio:open-panel', { detail: 'replay' })); }}>在地图上回放</Button>
          </div>
        </>
      )}
    </>
  );
}

function GenericMetrics({ run }: { run: Run }) {
  const m = run.metrics;
  const cov = m.coverage_fraction as number | null | undefined;
  return (
    <div className={a.metricGrid}>
      <Cell label="目标值" value={`${fmt.num(run.objective.value, 2)} ${run.objective.unit}`} note={run.objective.lower_bound != null ? `下界 ${fmt.num(run.objective.lower_bound, 2)}` : ''} />
      <Cell label="验算" value={run.check ? (run.check.valid ? '通过' : `${run.check.errors.length} 项未通过`) : '未验算'} tone={run.check?.valid ? 'good' : 'bad'} note={run.check?.errors.slice(0, 2).join('；')} />
      {cov != null && <Cell label="覆盖率" value={`${fmt.num(cov * 100, 1)}%`} note={`覆盖面积 ${fmt.num(m.coverage_area_m2 as number, 1)} m² / 田块面积 ${fmt.num(m.field_area_m2 as number, 1)} m²`} />}
      <Cell label="计算时间" value={fmt.sec(m.wall_s)} />
    </div>
  );
}

function AssetBinding({ run }: { run: Run }) {
  const inst = run.instance as unknown as { asset_refs?: AssetRef[]; fleet?: FleetAssetBinding } | undefined;
  const refs = inst?.asset_refs ?? [];
  return (
    <>
      <h3>绑定的场景与资产版本</h3>
      <div className={a.kv}>
        <span>场景</span><span>{run.scenario_id} · 实例 <span className={a.mono}>{run.instance_sha256?.slice(0, 12)}</span></span>
        {refs.map((r) => (
          <span key={`${r.role}-${r.id}-${r.version}`} style={{ display: 'contents' }}>
            <span>{{ map: '地图', vehicle: '车辆', facility: '设施', template: '模板' }[r.role] ?? r.role}</span>
            <span>{r.name ?? r.id} v{r.version} <span className={a.mono}>{r.sha256.slice(0, 12)}</span></span>
          </span>
        ))}
        {!refs.length && <><span>资产</span><span>这个方案的任务地图没有绑定资产（文字生成或手工绘制的地图）</span></>}
        {inst?.fleet && <><span>未参与规划</span><span>{inst.fleet.ignored.length ? inst.fleet.ignored.join('；') : '无'}</span></>}
      </div>
    </>
  );
}

function ExportButton({ run, sim, sims }: { run: Run; sim: { r: SimResult; d: Derived } | null; sims: FieldSimSummary[] | null }) {
  const st = useStudio();
  const record = useMemo(() => {
    const inst = run.instance as unknown as (FleetInstance & { asset_refs?: AssetRef[]; fleet?: FleetAssetBinding }) | undefined;
    const sc = run.scenario_snapshot ?? st.scenario;
    return {
      schema: 'agri-workbench.experiment-record/1',
      exported_utc: new Date().toISOString(),
      note: '所有数值取自运行记录与仿真结果文件；本文件不含任何补算或示意数据。',
      scenario: sc ? { id: sc.id, title: sc.title, problem_class: sc.problem_class, frame: sc.frame, provenance: sc.provenance } : { id: run.scenario_id },
      instance_sha256: run.instance_sha256,
      assets: inst?.asset_refs ?? [],
      fleet_binding: inst?.fleet ?? null,
      decision: run.recommendation_at_submission ?? null,
      run: {
        run_id: run.run_id, job_id: run.job_id, algorithm: run.algorithm, params: run.params, state: run.state, status: run.status,
        objective: run.objective, metrics: run.metrics, check: run.check, map_check: run.map_check, created_utc: run.created_utc, finished_utc: run.finished_utc,
        reproducibility: run.reproducibility ?? null,
      },
      simulation: sim ? {
        session_id: sim.r.session_id, state: sim.r.state, world: sim.r.world, finished_utc: sim.r.finished_utc, sim_time: sim.r.sim_time,
        real_time_factor: sim.r.real_time_factor, travel: sim.r.travel ?? null, row_collisions: sim.r.row_collisions ?? null, metrics: sim.r.metrics,
        execution: '纯追踪路径跟踪（不调用 Nav2 重规划）', localization: 'Gazebo 真值位姿',
        derived: { duration_s: sim.d.duration, min_separation: sim.d.separation, stalls: sim.d.stalls, anomalies: sim.d.anomalies, cross_track: sim.d.crossTrack },
        execution_provenance: sim.r.execution_provenance ?? null,
      } : null,
      other_simulations: (sims ?? []).slice(1).map((x) => ({ session_id: x.session_id, state: x.state, finished_utc: x.finished_utc, metrics: x.metrics })),
      acceptance: {
        plan_check: run.check ? (run.check.valid ? 'passed' : 'failed') : 'not_checked',
        simulation: sim ? (sim.r.state === 'succeeded' ? 'all_vehicles_finished' : 'not_finished') : 'not_executed',
        multi_vehicle_collision_avoidance: 'not_accepted（规划不建模车间冲突，仿真不做车间避让）',
      },
      raw: {
        run_json: exportUrl.run(run.run_id, 'json'), run_csv: exportUrl.run(run.run_id, 'csv'), run_geojson: exportUrl.run(run.run_id, 'geojson'),
        simulation_result: sim ? urls.fieldsimResult(sim.r.session_id) : null,
      },
    };
  }, [run, sim, sims, st.scenario]);
  const download = () => {
    const blob = new Blob([JSON.stringify(record, null, 1)], { type: 'application/json' });
    const href = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = href;
    link.download = `experiment-${run.scenario_id}-${run.run_id}.json`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(href), 2000);
  };
  return (
    <div className={p.row}>
      {!isFleet(st.scenario) && <Badge tone="gray">{run.problem_class}</Badge>}
      <Button size="sm" icon={Download} onClick={download} title="导出实验记录：场景、资产版本、决策快照、方案、验算与仿真结果">导出实验记录</Button>
    </div>
  );
}
