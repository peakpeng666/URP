/**
 * Replay of a finished field simulation on the task map: the recorded ground-truth trails, task arrivals and the
 * executed plan, with derived checks (cross-track error against the executed path, closest approach between
 * vehicles, stalls, unreached tasks). Everything here is computed from the saved result.json, nothing is simulated.
 */
import { create } from 'zustand';
import type { XY } from '../../lab/types';
import { studio } from '../api';
import type { FieldPhysics, FieldPhysicsEvidence, FieldSimMetrics, FieldVehicleState } from '../types';
import { trafficStatus, type TrafficEvidence } from './traffic';

export type TrailPoint = [number, number, number, number]; // t (sim s), x, y, yaw

export interface SimTask { vehicle: string; stop: XY | null; id: number; label: string; xy: XY; state: string; t_sim: number | null; distance_m: number | null }
export interface SimPlanVehicle { name: string; label: string; color: string; start: [number, number, number]; path: XY[]; planned_length_m: number; planned_duration_s: number }
export interface SimResult extends TrafficEvidence {
  session_id: string; run_id: string; scenario_id: string; algorithm: string | null; world: string; finished_utc: string;
  sim_time: number | null; real_time_factor: number | null; state: 'succeeded' | 'failed' | 'canceled';
  metrics: FieldSimMetrics; travel?: 'rows' | 'free';
  vehicles: FieldVehicleState[]; tasks: SimTask[]; trails: Record<string, TrailPoint[]>;
  execution_plan?: { vehicles?: SimPlanVehicle[]; robot_radius_m?: number; travel?: string; world?: string; bounds?: number[] };
  execution_provenance?: Record<string, unknown> | null; planning_solution?: Record<string, unknown> | null; provenance_warning?: string;
  physics?: FieldPhysics | null;
  physics_audit?: FieldPhysicsEvidence | null;
  physics_runtime?: FieldPhysicsEvidence | null;
  truth_timing?: { scope?: string; [key: string]: unknown } | null;
  energy?: Record<string, unknown> | null;
  errors?: string[];
  session_report?: { status?: string; cleanup_status?: string; execution_state?: string; remaining_owned_processes?: unknown[]; errors?: string[] } | null;
}

export interface Anomaly { key: string; tone: 'error' | 'warn'; text: string; xy: XY | null; t: number | null; vehicle?: string }

export const SIM_BODY = { length_m: 0.8, width_m: 0.56 };
export function simBody(result: SimResult): { length_m: number; width_m: number } {
  const size = result.physics?.body?.size_m;
  return size?.length === 3 ? { length_m: size[0], width_m: size[1] } : SIM_BODY;
}

export function poseAt(trail: TrailPoint[], t: number): [number, number, number] | null {
  if (!trail.length) return null;
  if (t <= trail[0][0]) return [trail[0][1], trail[0][2], trail[0][3]];
  const last = trail[trail.length - 1];
  if (t >= last[0]) return [last[1], last[2], last[3]];
  let lo = 0, hi = trail.length - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (trail[mid][0] <= t) lo = mid; else hi = mid;
  }
  const a = trail[lo], b = trail[hi];
  const f = (t - a[0]) / Math.max(1e-9, b[0] - a[0]);
  let dyaw = b[3] - a[3];
  if (dyaw > Math.PI) dyaw -= 2 * Math.PI;
  if (dyaw < -Math.PI) dyaw += 2 * Math.PI;
  return [a[1] + f * (b[1] - a[1]), a[2] + f * (b[2] - a[2]), a[3] + f * dyaw];
}

/** Index of the last trail sample at or before t. */
export function indexAt(trail: TrailPoint[], t: number): number {
  let lo = 0, hi = trail.length - 1;
  if (!trail.length || t < trail[0][0]) return -1;
  if (t >= trail[hi][0]) return hi;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (trail[mid][0] <= t) lo = mid; else hi = mid;
  }
  return lo;
}

function distToPath(p: XY, path: XY[]): number {
  let d = Infinity;
  for (let i = 0; i + 1 < path.length; i++) {
    const [ax, ay] = path[i], [bx, by] = path[i + 1];
    const dx = bx - ax, dy = by - ay, L = dx * dx + dy * dy;
    const t = L ? Math.max(0, Math.min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L)) : 0;
    d = Math.min(d, Math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy));
  }
  return d;
}

export interface Derived {
  duration: number;
  crossTrack: Record<string, { max: number; at: TrailPoint | null; mean: number }>;
  separation: { d: number; t: number; a: string; b: string; xy: XY } | null;
  stalls: { vehicle: string; t0: number; t1: number; xy: XY }[];
  anomalies: Anomaly[];
}

export function derive(r: SimResult): Derived {
  const names = Object.keys(r.trails);
  const duration = Math.max(0, ...names.map((n) => r.trails[n].at(-1)?.[0] ?? 0));
  const plan = new Map((r.execution_plan?.vehicles ?? []).map((v) => [v.name, v]));
  const label = (n: string) => r.vehicles.find((v) => v.name === n)?.label ?? n;

  // cross-track: distance from each ground-truth sample to the path the vehicle was told to follow
  const crossTrack: Derived['crossTrack'] = {};
  for (const n of names) {
    const path = plan.get(n)?.path;
    if (!path || path.length < 2) continue;
    let max = 0, sum = 0, at: TrailPoint | null = null;
    for (const p of r.trails[n]) {
      const d = distToPath([p[1], p[2]], path);
      sum += d;
      if (d > max) { max = d; at = p; }
    }
    crossTrack[n] = { max, at, mean: r.trails[n].length ? sum / r.trails[n].length : 0 };
  }

  // closest approach between any two vehicles on a common 0.5 s clock
  let separation: Derived['separation'] = null;
  if (names.length > 1) {
    for (let t = 0; t <= duration; t += 0.5) {
      const ps = names.map((n) => poseAt(r.trails[n], t));
      for (let i = 0; i < names.length; i++) {
        for (let j = i + 1; j < names.length; j++) {
          const a = ps[i], b = ps[j];
          if (!a || !b) continue;
          const d = Math.hypot(a[0] - b[0], a[1] - b[1]);
          if (!separation || d < separation.d) separation = { d, t, a: names[i], b: names[j], xy: [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2] };
        }
      }
    }
  }

  // stalls: ≥ 20 s with < 5 cm progress, away from task stops and the depot, before the vehicle finished
  const stalls: Derived['stalls'] = [];
  const stops = r.tasks.map((t) => t.stop ?? t.xy);
  for (const n of names) {
    const tr = r.trails[n];
    const start = plan.get(n)?.start;
    let i = 0;
    while (i < tr.length) {
      let j = i;
      while (j + 1 < tr.length && Math.hypot(tr[j + 1][1] - tr[i][1], tr[j + 1][2] - tr[i][2]) < 0.05) j++;
      const span = tr[j][0] - tr[i][0];
      const xy: XY = [tr[i][1], tr[i][2]];
      const atStop = stops.some((s) => Math.hypot(s[0] - xy[0], s[1] - xy[1]) < 1.2) || (start && Math.hypot(start[0] - xy[0], start[1] - xy[1]) < 1.2);
      if (span >= 20 && !atStop && j < tr.length - 1) stalls.push({ vehicle: n, t0: tr[i][0], t1: tr[j][0], xy });
      i = j + 1;
    }
  }

  const anomalies: Anomaly[] = [];
  for (const t of r.tasks) {
    if (t.state !== 'reached') anomalies.push({ key: `task-${t.id}`, tone: 'error', text: `任务 ${t.label} 未到达（${label(t.vehicle)}）`, xy: t.stop ?? t.xy, t: null, vehicle: t.vehicle });
  }
  for (const v of r.vehicles) {
    if (v.state === 'failed') anomalies.push({ key: `veh-${v.name}`, tone: 'error', text: `${v.label} 受阻，未完成路线`, xy: v.pose ? [v.pose[0], v.pose[1]] : null, t: null, vehicle: v.name });
  }
  for (const s of stalls) {
    anomalies.push({ key: `stall-${s.vehicle}-${s.t0}`, tone: 'warn', text: `${label(s.vehicle)} 在 ${s.t0.toFixed(0)}–${s.t1.toFixed(0)} s 停滞 ${(s.t1 - s.t0).toFixed(0)} s`, xy: s.xy, t: s.t0, vehicle: s.vehicle });
  }
  for (const [n, c] of Object.entries(crossTrack)) {
    if (c.at && c.max > 0.3) anomalies.push({ key: `xt-${n}`, tone: 'warn', text: `${label(n)} 最大横向偏差 ${c.max.toFixed(2)} m（t=${c.at[0].toFixed(0)} s）`, xy: [c.at[1], c.at[2]], t: c.at[0], vehicle: n });
  }
  const body = simBody(r);
  const traffic = trafficStatus(r);
  if (separation && separation.d < Math.hypot(body.length_m, body.width_m)) {
    anomalies.push({ key: 'sep', tone: 'warn', text: `${label(separation.a)} 与 ${label(separation.b)} 最近相距 ${separation.d.toFixed(2)} m（t=${separation.t.toFixed(0)} s）：记录轨迹接近；${traffic.value}，以接触事件与独立检查为准`, xy: separation.xy, t: separation.t });
  }
  if (r.row_collisions != null && r.row_collisions > 0) {
    anomalies.push({ key: 'rows', tone: 'warn', text: `车辆与作物行接触消息 ${r.row_collisions} 条（去重时间戳 + 碰撞体对，非事故次数）`, xy: null, t: null });
  }
  if (r.robot_contact_events != null && r.robot_contact_events > 0) {
    anomalies.push({ key: 'robot-contacts', tone: 'error', text: `车间接触消息 ${r.robot_contact_events} 条（去重时间戳 + 碰撞体对，非事故次数）`, xy: null, t: null });
  }
  if (traffic.tone !== 'good') {
    anomalies.push({ key: 'traffic-evidence', tone: traffic.tone === 'bad' ? 'error' : 'warn', text: `${traffic.value}：${traffic.note}`, xy: null, t: null });
  }
  return { duration, crossTrack, separation, stalls, anomalies };
}

interface ReplayStore {
  sessionId: string | null;
  result: SimResult | null;
  derived: Derived | null;
  loading: boolean;
  error: string | null;
  t: number;
  playing: boolean;
  speed: number;
  show: { planned: boolean; actual: boolean; body: boolean; tasks: boolean; anomalies: boolean };
  hidden: string[];
  focus: Anomaly | null;
  load: (sessionId: string) => Promise<void>;
  clear: () => void;
  setT: (t: number) => void;
  setPlaying: (p: boolean) => void;
  setSpeed: (s: number) => void;
  toggle: (k: keyof ReplayStore['show']) => void;
  toggleVehicle: (name: string) => void;
  setFocus: (a: Anomaly | null) => void;
}

let loadController: AbortController | null = null;

export const useReplay = create<ReplayStore>((set, get) => ({
  sessionId: null,
  result: null,
  derived: null,
  loading: false,
  error: null,
  t: 0,
  playing: false,
  speed: 20,
  show: { planned: true, actual: true, body: true, tasks: true, anomalies: true },
  hidden: [],
  focus: null,
  async load(sessionId) {
    loadController?.abort();
    const controller = new AbortController();
    loadController = controller;
    set({ sessionId, loading: true, error: null, playing: false, focus: null });
    try {
      const result = await studio.fieldsimResult(sessionId, { signal: controller.signal });
      if (get().sessionId !== sessionId || controller.signal.aborted) return;
      const derived = derive(result);
      set({ result, derived, loading: false, t: derived.duration, hidden: [] });
    } catch (e) {
      if (get().sessionId !== sessionId) return;
      set({ loading: false, error: (e as Error).name === 'AbortError' ? '回放读取已取消' : (e as Error).message, result: null, derived: null });
    } finally {
      if (loadController === controller) loadController = null;
    }
  },
  clear: () => {
    loadController?.abort();
    loadController = null;
    set({ sessionId: null, result: null, derived: null, playing: false, focus: null, error: null, loading: false });
  },
  setT: (t) => set({ t }),
  setPlaying: (playing) => set({ playing }),
  setSpeed: (speed) => set({ speed }),
  toggle: (k) => set((s) => ({ show: { ...s.show, [k]: !s.show[k] } })),
  toggleVehicle: (name) => set((s) => ({ hidden: s.hidden.includes(name) ? s.hidden.filter((x) => x !== name) : [...s.hidden, name] })),
  setFocus: (focus) => set({ focus }),
}));
