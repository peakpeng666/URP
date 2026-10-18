/**
 * Field simulation of a multi-vehicle plan: Gazebo Fortress runs a world generated from the task map,
 * every vehicle drives its planned route over ROS 2, and the executed schedule is compared with the plan.
 */
import { useState } from 'react';
import { Box, Download, MonitorPlay, Play, Square, Tractor } from 'lucide-react';
import { fmt, lab, useLabResource } from '../../lab/api';
import { Badge, Button, EmptyState, Input, Notice, Select, Switch } from '../../lab/ui';
import { studio, urls, type FieldPhysicsResponse } from '../api';
import { useStudio } from '../store';
import { refreshFieldSim, setFieldSimActionError, useFieldSim } from '../ros/live';
import { executionErrorMessage, planModelSchema, unacceptedPlanReason } from '../execution';
import type { FieldSimState, FieldSimSummary, FieldVehicleState, FleetInstance } from '../types';
import type { SimResult } from '../experiment/replay';
import { SessionEvidence } from '../experiment/SessionEvidence';
import s from './panels.module.css';

const PHASE: Record<FieldSimState['phase'], { text: string; tone: 'gray' | 'blue' | 'green' | 'red' | 'orange' }> = {
  idle: { text: '未运行', tone: 'gray' },
  starting: { text: '启动 Gazebo…', tone: 'blue' },
  ready: { text: '就绪', tone: 'blue' },
  running: { text: '执行中', tone: 'blue' },
  finished: { text: '全部完成', tone: 'green' },
  failed: { text: '未完成', tone: 'red' },
  stopped: { text: '已停止', tone: 'gray' },
};
const STATE_TEXT: Record<FieldVehicleState['state'], string> = { waiting: '等待', driving: '行驶', servicing: '作业', done: '完成', failed: '受阻' };

const pct = (a?: number | null, b?: number | null) => (a != null && b ? `${a >= b ? '+' : ''}${fmt.num(((a - b) / b) * 100, 1)}%` : '');

/** Starts the field simulation for a fleet run and brings the simulation workspace forward. */
export async function startFieldSim(runId: string, opts: { gui?: boolean; rviz?: boolean; real_time_factor?: number; physics?: Record<string, unknown> } = {}) {
  const st = useStudio.getState();
  setFieldSimActionError(null);
  try {
    const run = st.runs[runId] ?? (await lab.run(runId));
    const instance = run.instance as unknown as (FleetInstance & { fleet?: { asset?: { name?: string; id: string }; adapter?: string | null; adapter_note?: string } }) | undefined;
    const blocked = unacceptedPlanReason(instance, planModelSchema(run));
    if (blocked) {
      setFieldSimActionError(blocked);
      st.notify('error', blocked);
      return;
    }
    const fleet = instance?.fleet;
    if (fleet && fleet.adapter !== 'fieldsim-diffdrive') {
      const message = `这个方案的车队是「${fleet.asset?.name ?? fleet.asset?.id}」，田间仿真不能生成该车型：${fleet.adapter_note ?? '缺仿真适配'}。可改用内置田间差速机器人重新求解后再执行。`;
      setFieldSimActionError(message);
      st.notify('error', message);
      return;
    }
  } catch {
    /* run record unreadable: the backend decides */
  }
  try {
    await studio.startFieldsim(runId, opts);
    await refreshFieldSim();
    st.setWorkspace('sim');
    st.notify('info', '正在生成田间世界并启动 Gazebo；只有实际状态与结果检查才会标记执行成功');
  } catch (e) {
    const message = executionErrorMessage(e);
    setFieldSimActionError(message);
    st.notify('error', message);
  }
}

export function FieldSimPanel() {
  const { state, error, actionError } = useFieldSim();
  const focusRun = useStudio((st) => st.focusRun);
  const runs = useStudio((st) => st.runs);
  const [rtf, setRtf] = useState(4);
  const [gui, setGui] = useState(false);
  const [rviz, setRviz] = useState(false);
  const [busy, setBusy] = useState(false);
  const [overrides, setOverrides] = useState<Record<string, unknown>>({});
  const recent = useLabResource('fieldsim-runs', () => lab.runs({ limit: 60 }), { pollMs: 15000 });
  const results = useLabResource('fieldsim-results', () => studio.fieldsimResults(), { pollMs: 5000 });
  const physics = useLabResource('fieldsim-physics', () => studio.fieldsimPhysics());
  const fleetRuns = (recent.data?.runs ?? []).filter((r) => r.problem_class === 'fleet_routing' && r.state === 'done' && r.routes.length);
  const focused = focusRun && runs[focusRun]?.problem_class === 'fleet_routing' ? runs[focusRun] : null;
  const running = !!state?.running;
  const phase = PHASE[state?.phase ?? 'idle'];

  const start = async (runId: string) => {
    setBusy(true);
    const allowed = physics.data?.override_keys ?? [];
    const selected = Object.fromEntries(Object.entries(overrides).filter(([key]) => allowed.includes(key)));
    await startFieldSim(runId, { gui, rviz, real_time_factor: rtf, physics: Object.keys(selected).length ? selected : undefined });
    setBusy(false);
  };
  const stop = async () => {
    setBusy(true);
    try {
      await studio.stopFieldsim();
      setFieldSimActionError(null);
    } catch (e) {
      setFieldSimActionError(executionErrorMessage(e, 'stop'));
    } finally {
      await refreshFieldSim();
      results.reload();
      setBusy(false);
    }
  };
  const window_ = async (kind: 'gui' | 'rviz', on: boolean) => {
    try {
      await studio.fieldsimWindow(kind, on);
      await refreshFieldSim();
    } catch (e) {
      const message = executionErrorMessage(e);
      setFieldSimActionError(message);
      useStudio.getState().notify('error', message);
    }
  };

  return (
    <div className={s.scroll}>
      <div className={s.form}>
        <div className={s.rowSpace}>
          <h3><Tractor size={14} style={{ verticalAlign: -2 }} /> 田间多车仿真</h3>
          <Badge tone={phase.tone}>{phase.text}</Badge>
        </div>
        <p className={s.meta}>Gazebo Fortress 按任务地图生成田块、作物行、障碍和车库。URP 路径跟踪、规划几何和实际轨迹分开记录；HTTP 200 或窗口打开不等于执行成功。</p>
        {error && <Notice tone="error">仿真状态读取失败：{error}</Notice>}
        {actionError && <Notice tone="error">{actionError}<div className={s.row}><Button size="sm" onClick={() => void refreshFieldSim()}>刷新会话状态</Button><Button size="sm" variant="plain" onClick={() => setFieldSimActionError(null)}>知道了</Button></div></Notice>}

        {running || state?.session_id ? (
          <RunningView state={state!} busy={busy} onStop={stop} onWindow={window_} />
        ) : null}

        {!running && (
          <>
            <h4>执行一个多车方案</h4>
            <div className={s.row}>
              <label className={s.meta}>倍速</label>
              <Select aria-label="仿真倍速" value={String(rtf)} onChange={(e) => setRtf(Number(e.target.value))}>
                {[1, 2, 4, 6, 10].map((x) => <option key={x} value={x}>{x}×</option>)}
              </Select>
              <Switch checked={gui} onChange={setGui} label="Gazebo 窗口" />
              <Switch checked={rviz} onChange={setRviz} label="RViz2" />
            </div>
            <PhysicsSetup data={physics.data} error={physics.error?.message ?? null} overrides={overrides} onChange={setOverrides} />
            {focused && (
              <button type="button" className={s.item} disabled={busy} onClick={() => void start(focused.run_id)}>
                <span className={s.itemTitle}><Play size={12} /> 当前方案：{focused.algorithm.name}</span>
                <span className={s.itemSub}>{focused.scenario_id} · {fmt.num(Number(focused.metrics.total_distance_m), 1)} m · {focused.routes.length} 台车{travelText(focused.metrics.travel)}</span>
              </button>
            )}
            <ul className={s.list}>
              {fleetRuns.filter((r) => r.run_id !== focused?.run_id).slice(0, 12).map((r) => (
                <li key={r.run_id}>
                  <button type="button" className={s.item} disabled={busy} onClick={() => void start(r.run_id)}>
                    <span className={s.itemTitle}>{r.algorithm.name}</span>
                    <span className={s.itemSub}>{r.scenario_id} · {fmt.num(Number(r.metrics.total_distance_m), 1)} m · {r.routes.length} 台车{travelText(r.metrics.travel)} · {fmt.time(r.created_utc)}</span>
                  </button>
                </li>
              ))}
              {!fleetRuns.length && <li className={s.meta} style={{ padding: 8 }}>先在「任务规划」里求出一个多车方案。</li>}
            </ul>
          </>
        )}

        {results.error && <Notice tone="error">历次执行读取失败：{results.error.message}</Notice>}
        {(results.data?.results.length ?? 0) > 0 && (
          <>
            <h4>历次执行</h4>
            <ResultsTable rows={results.data!.results} />
          </>
        )}
      </div>
    </div>
  );
}

function PhysicsSetup({ data, error, overrides, onChange }: { data: FieldPhysicsResponse | null; error: string | null; overrides: Record<string, unknown>; onChange: (value: Record<string, unknown>) => void }) {
  const labels: Record<string, string> = {
    max_step_size_s: '物理步长（s）', collision_detector: '碰撞检测器', ground_friction: '地面摩擦', wheel_friction: '轮胎摩擦', payload_kg: '恒定载荷（kg）', wheel_contact: '轮胎接触', tyre_width_m: '胎宽（m）', wheel_lateral_friction: '横向摩擦（诊断）',
  };
  return (
    <details className={s.physics}>
      <summary>物理模型：{data?.default.schema ?? '读取失败或尚未返回'}</summary>
      {error && <Notice tone="error">物理配置读取失败：{error}。仅显示后端实际启动结果，不伪造默认版本。</Notice>}
      {data && (
        <>
          <p className={s.hint}>{data.scope ?? '合成刚体仿真'}。可配置不等于该工况已验证；当前没有真实土壤 / 轮胎校准。</p>
          <p className={s.meta}>默认：步长 {String(data.default.max_step_size_s ?? '—')} s · 检测 {String(data.default.collision_detector ?? '—')} · 地面 / 轮胎摩擦 {String(data.default.ground_friction ?? '—')} / {String(data.default.wheel_friction ?? '—')} · 载荷 {String(data.default.payload_kg ?? '—')} kg</p>
          {data.override_keys.map((key) => {
            const enabled = Object.prototype.hasOwnProperty.call(overrides, key);
            const value = enabled ? overrides[key] : data.default[key];
            const set = (next: unknown) => onChange({ ...overrides, [key]: next });
            const toggle = () => {
              const next = { ...overrides };
              if (enabled) delete next[key];
              else next[key] = data.default[key];
              onChange(next);
            };
            return (
              <div key={key} className={s.row}>
                <label className={s.meta}><input type="checkbox" checked={enabled} onChange={toggle} /> 覆盖 {labels[key] ?? key}</label>
                {enabled && key === 'collision_detector' && <Select aria-label="覆盖碰撞检测器" value={String(value)} onChange={(e) => set(e.target.value)}><option value="ode">ODE</option><option value="bullet">Bullet</option></Select>}
                {enabled && key === 'wheel_contact' && <Select aria-label="覆盖轮胎接触" value={String(value)} onChange={(e) => set(e.target.value)}><option value="tyre">有限宽轮胎</option><option value="sphere">球面接触对照</option></Select>}
                {enabled && !['collision_detector', 'wheel_contact'].includes(key) && (
                  <Input aria-label={`覆盖${labels[key] ?? key}`} type="number" value={Number(value ?? 0)} min={key === 'max_step_size_s' ? 0.0005 : key === 'tyre_width_m' ? 0.04 : key.includes('friction') ? 0.01 : 0} max={key === 'max_step_size_s' ? 0.01 : key === 'payload_kg' ? 50 : key.includes('friction') ? 2 : key === 'tyre_width_m' ? 0.16 : undefined} step={key === 'max_step_size_s' ? 0.0005 : key === 'tyre_width_m' ? 0.01 : 0.1} onChange={(e) => Number.isFinite(e.target.valueAsNumber) && set(e.target.valueAsNumber)} />
                )}
              </div>
            );
          })}
        </>
      )}
    </details>
  );
}

function RunningView({ state, busy, onStop, onWindow }: { state: FieldSimState; busy: boolean; onStop: () => void; onWindow: (k: 'gui' | 'rviz', on: boolean) => void }) {
  const m = state.metrics ?? {};
  const done = state.phase === 'finished' || state.phase === 'failed';
  const evidence = useLabResource<SimResult | null>(`fieldsim-evidence-${state.session_id ?? 'none'}-${state.phase}-${state.running}`, (signal) => {
    if (!state.result || !state.session_id) return Promise.resolve(null);
    return studio.fieldsimResult(state.session_id, { signal });
  });
  return (
    <div className={s.form} style={{ padding: 0 }}>
      <div className={s.kv}>
        <span>方案</span><b>{state.algorithm ?? '—'}</b>
        <span>场景</span><b>{state.scenario_id ?? '—'}</b>
        <span>仿真时间</span><b className={s.mono}>{fmt.sec(state.sim_time ?? 0)}{state.real_time_factor ? ` · ${fmt.num(state.real_time_factor, 1)}×` : ''}</b>
      </div>
      {state.errors.map((e) => <Notice key={e} tone="error">{e}</Notice>)}
      {state.warnings.map((w) => <Notice key={w} tone="info">{w}</Notice>)}
      <div className={s.vehicleList}>
        {state.vehicles.map((v) => (
          <div key={v.name} className={s.vehicleRow}>
            <i className={s.swatch} style={{ background: v.color }} />
            <b>{v.label}</b>
            <span className={s.meta}>{STATE_TEXT[v.state]}</span>
            <span className={s.progressBar}><i style={{ width: `${Math.round(v.progress * 100)}%`, background: v.color }} /></span>
            <span className={s.mono}>{v.tasks_done}/{v.tasks_total}</span>
            <span className={s.mono}>{fmt.num(v.distance_m, 0)} m</span>
          </div>
        ))}
      </div>
      {done && (
        <table className={s.table}>
          <thead><tr><th /><th className={s.num}>规划</th><th className={s.num}>执行</th><th className={s.num}>差异</th></tr></thead>
          <tbody>
            <tr><td>最晚完成</td><td className={s.num}>{fmt.sec(m.planned_makespan_s)}</td><td className={s.num}>{fmt.sec(m.makespan_s)}</td><td className={s.num}>{pct(m.makespan_s, m.planned_makespan_s)}</td></tr>
            <tr><td>总里程</td><td className={s.num}>{fmt.num(m.planned_total_distance_m, 1)} m</td><td className={s.num}>{fmt.num(m.total_distance_m, 1)} m</td><td className={s.num}>{pct(m.total_distance_m, m.planned_total_distance_m)}</td></tr>
            <tr><td>到达任务</td><td className={s.num}>{m.tasks_total}</td><td className={s.num}>{m.tasks_reached}</td><td /></tr>
            <tr><td>横向偏差</td><td className={s.num} /><td className={s.num}>均 {fmt.num(m.cross_track_mean_m, 3)} m</td><td className={s.num}>最大 {fmt.num(m.cross_track_max_m, 2)} m</td></tr>
          </tbody>
        </table>
      )}
      {evidence.error && <Notice tone="error">物理证据读取失败：{evidence.error.message}</Notice>}
      {evidence.data && <SessionEvidence result={evidence.data} />}
      <div className={s.row}>
        {state.running && (
          <>
            <Switch checked={state.components.gui === 'running'} onChange={(on) => onWindow('gui', on)} label="Gazebo 窗口" />
            <Switch checked={state.components.rviz === 'running'} onChange={(on) => onWindow('rviz', on)} label="RViz2" />
            <span className={s.spacer} />
            <Button size="sm" variant="destructive" icon={Square} disabled={busy} onClick={onStop}>{done ? '关闭仿真' : '停止'}</Button>
          </>
        )}
        {state.result && state.session_id && (
          <a className={s.link} href={urls.fieldsimResult(state.session_id)} download><Download size={12} /> 结果 JSON</a>
        )}
      </div>
      {state.running && (
        <p className={s.hint}><MonitorPlay size={12} style={{ verticalAlign: -2 }} /> 中间是 ROS 2 实时视图（Foxglove Bridge），旁边标签页是 Gazebo 场景（gzweb）；底部是遥测曲线。停止 / 关闭是有序关闭并保存记录；后端尚未提供暂停物理或取消任务但保留会话的接口。</p>
      )}
    </div>
  );
}

/** ' · 沿行间' for plans that drive along the crop-row lanes (the rows are solid in Gazebo). */
function travelText(travel: unknown): string {
  return travel === 'rows' ? ' · 沿行间' : travel === 'free' ? ' · 自由通行' : '';
}

function ResultsTable({ rows }: { rows: FieldSimSummary[] }) {
  return (
    <table className={s.table}>
      <thead><tr><th>方案</th><th className={s.num}>状态 / 任务</th><th className={s.num}>最晚完成</th><th className={s.num}>与规划</th><th /></tr></thead>
      <tbody>
        {rows.slice(0, 12).map((r) => (
          <tr key={r.session_id} title={`${r.scenario_id} · ${r.world}`}>
            <td>{r.algorithm ?? r.run_id}<div className={s.meta}>{fmt.time(r.finished_utc)}{travelText(r.travel)}</div></td>
            <td className={s.num}>{r.state === 'succeeded'
              ? <Badge tone="green">完成 {r.metrics.tasks_reached}/{r.metrics.tasks_total}</Badge>
              : r.state === 'canceled' ? <Badge tone="orange">已取消 {r.metrics.tasks_reached}/{r.metrics.tasks_total}</Badge>
                : <Badge tone="red">失败 {r.metrics.tasks_reached}/{r.metrics.tasks_total}</Badge>}</td>
            <td className={s.num}>{fmt.sec(r.metrics.makespan_s)}</td>
            <td className={s.num}>{pct(r.metrics.makespan_s, r.metrics.planned_makespan_s)}</td>
            <td><a className={s.link} href={urls.fieldsimResult(r.session_id)} download><Box size={12} /></a></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function EmptyFieldSim() {
  return <EmptyState icon={Tractor} title="田间多车仿真" />;
}
