/**
 * Asset → task map: binds vehicle, facility and map assets into the open multi-vehicle task map.
 * Every binding changes the instance that is saved and submitted to the solvers (robot radius, capacity,
 * speed, obstacles) and records the asset version in instance.asset_refs, so runs and exports carry it.
 * What the planners cannot use (rectangle orientation, turning radius …) is listed, never silently dropped.
 */
import { navigate } from '../../app/router';
import type { Scenario, XY } from '../../lab/types';
import { studio } from '../api';
import { OBSTACLE_STYLE, centroid, nextObstacleId } from '../editor/geometry';
import { asFleet, flushSave, isFleet, useStudio } from '../store';
import type { FleetInstance, FleetObstacle, ObstacleKind } from '../types';
import type { Affine, Asset, AssetRef, AssetVersion, PlanningProfile } from './api';

export interface FleetAssetBinding {
  asset: AssetRef;
  kinematics: string | null;
  footprint: PlanningProfile['footprint'];
  robot_radius_m: number;
  /** null with payload 'none': an inspection / sampling vehicle without a capacity constraint */
  capacity: number | null;
  payload: 'none' | 'load';
  speed_mps: number | null;
  min_turn_radius_m: number | null;
  work_width_m: number | null;
  /** simulation adapter that really spawns this vehicle and executes multi-vehicle plans; null = cannot be executed here */
  adapter: string | null;
  /** why there is no fleet executor for this vehicle */
  adapter_note?: string;
  /** what the multi-vehicle planner does not use from the asset */
  ignored: string[];
  bound_utc: string;
}

export type AssetAwareInstance = FleetInstance & { asset_refs?: AssetRef[]; fleet?: FleetAssetBinding };

export interface BackgroundLayer {
  asset: AssetRef;
  type: 'raster' | 'vector' | 'image';
  /** file inside the asset version: derived/preview.png, derived/features_local.json or the image itself */
  file: string;
  /** pixel → task-map metres, for raster and image backgrounds */
  affine?: Affine;
  size_px?: [number, number];
  opacity?: number;
}

export const refOf = (a: Asset, ver: AssetVersion, role: AssetRef['role']): AssetRef =>
  ({ role, id: a.id, version: ver.v, sha256: ver.sha256, name: a.name });

/** Circumscribed radius: what the planners inflate obstacles by (same rule as the backend). */
export function footprintRadius(fp: PlanningProfile['footprint']): number | null {
  if (!fp) return null;
  if (fp.type === 'circle' && fp.radius_m) return fp.radius_m;
  if (fp.type === 'rect' && fp.length_m && fp.width_m) return Math.hypot(fp.length_m / 2, fp.width_m / 2);
  if (fp.type === 'polygon' && fp.points?.length) return Math.max(...fp.points.map(([x, y]) => Math.hypot(x, y)));
  return null;
}

/** Replace refs of the same role (single-valued roles) or the same asset (multi-valued roles). */
export function upsertRef(refs: AssetRef[] | undefined, ref: AssetRef, single: boolean): AssetRef[] {
  const rest = (refs ?? []).filter((r) => (single ? r.role !== ref.role : !(r.role === ref.role && r.id === ref.id)));
  return [...rest, ref];
}

function openFleet(): { inst: AssetAwareInstance } | string {
  const st = useStudio.getState();
  if (!st.scenario || !st.draft) return '先在「任务规划」里打开一个多车任务地图';
  if (!isFleet(st.scenario)) return '当前场景不是多车任务地图（车辆 / 设施资产只能放进多车任务地图）';
  return { inst: asFleet(st.draft) as AssetAwareInstance };
}

const edit = (fn: (i: AssetAwareInstance) => AssetAwareInstance) =>
  useStudio.getState().edit((i) => fn(i as unknown as AssetAwareInstance) as unknown as typeof i);

/** The planning binding of a vehicle asset version, or why it cannot plan yet. */
export function fleetBindingOf(a: Asset, ver: AssetVersion): FleetAssetBinding | string {
  const caps = ver.capabilities.planning;
  if (!caps?.ok) {
    const missing = (caps?.items ?? []).filter((i) => !i.ok && i.key !== 'work_width').map((i) => i.label);
    return `这辆车还不能用于规划，缺：${missing.join('、') || '规划参数'}（在资产库的检查器里补齐）`;
  }
  const p = ver.meta.planning ?? {};
  const r = footprintRadius(p.footprint);
  const payload = p.payload === 'none' ? 'none' : 'load';
  if (!r || !p.speed_mps || (payload === 'load' && !p.capacity)) return '规划参数不完整（足迹、容量、车速）';
  const solver = caps.solver?.fleet_routing as { ignored?: string[] } | undefined;
  // only an adapter that spawns this very vehicle AND executes multi-vehicle plans counts here
  const chosen = (ver.meta.simulation?.adapter as string | null | undefined) ?? null;
  const opt = ver.capabilities.simulation?.adapters?.find((o) => o.id === chosen);
  const fleetExec = !!(ver.capabilities.simulation?.ok && opt?.ok && opt.problem_classes?.includes('fleet_routing'));
  return {
    // rounded UP to the millimetre: the planner must never inflate obstacles by less than the real body
    asset: refOf(a, ver, 'vehicle'), kinematics: p.kinematics ?? null, footprint: p.footprint ?? null, robot_radius_m: Math.ceil(r * 1000 - 1e-9) / 1000,
    capacity: payload === 'none' ? null : p.capacity!, payload, speed_mps: p.speed_mps, min_turn_radius_m: p.min_turn_radius_m ?? null, work_width_m: p.work_width_m ?? null,
    adapter: fleetExec ? chosen : null,
    adapter_note: fleetExec ? undefined : opt?.ok ? `${opt.label} 只执行单车任务，不执行多车任务地图` : '没有能生成这辆车的仿真适配（缺项见资产检查器）',
    ignored: solver?.ignored ?? [], bound_utc: new Date().toISOString(),
  };
}

/** Use a vehicle asset for the open task map's fleet (homogeneous fleet: one vehicle type for every vehicle). */
export function bindVehicle(a: Asset, ver: AssetVersion): string | null {
  const cur = openFleet();
  if (typeof cur === 'string') return cur;
  const binding = fleetBindingOf(a, ver);
  if (typeof binding === 'string') return binding;
  edit((i) => ({
    ...i,
    robot_radius: binding.robot_radius_m,
    vehicles: { ...i.vehicles, capacity: binding.capacity ?? unconstrained(i), speed_mps: binding.speed_mps! },
    fleet: binding,
    asset_refs: upsertRef(i.asset_refs, binding.asset, true),
  }));
  return null;
}

/** A vehicle that carries no load gets a capacity no trip can exceed (the total demand). */
export const unconstrained = (i: { tasks: { demand: number }[] }) => Math.max(1, i.tasks.reduce((x, t) => x + t.demand, 0));

/** Remove the vehicle binding; the numbers stay as they are (they are ordinary fleet settings then). */
export function unbindVehicle() {
  edit((i) => {
    const { fleet: _drop, ...rest } = i;
    void _drop;
    return { ...rest, asset_refs: (i.asset_refs ?? []).filter((r) => r.role !== 'vehicle') };
  });
}

/** Differences between the bound vehicle asset and the fleet settings now in the task map. */
export function bindingDrift(inst: AssetAwareInstance): string[] {
  const b = inst.fleet;
  if (!b) return [];
  const out: string[] = [];
  if (Math.abs(inst.robot_radius - b.robot_radius_m) > 1e-6) out.push(`车体半径 ${inst.robot_radius} m（资产 ${b.robot_radius_m} m）`);
  if (b.capacity != null && inst.vehicles.capacity !== b.capacity) out.push(`容量 ${inst.vehicles.capacity}（资产 ${b.capacity}）`);
  if (b.capacity == null && inst.vehicles.capacity < unconstrained(inst)) out.push(`容量 ${inst.vehicles.capacity}（资产不载货，不应有容量约束）`);
  if (b.speed_mps != null && Math.abs(inst.vehicles.speed_mps - b.speed_mps) > 1e-9) out.push(`车速 ${inst.vehicles.speed_mps} m/s（资产 ${b.speed_mps} m/s）`);
  return out;
}

/** Put a facility (building, greenhouse, pole …) into the open task map as an obstacle with its planning footprint. */
export function placeFacility(a: Asset, ver: AssetVersion, at?: XY): string | null {
  const cur = openFleet();
  if (typeof cur === 'string') return cur;
  const p = ver.meta.planning ?? {};
  const size = ver.meta.display?.size_m;
  const fp = p.footprint ?? (size ? { type: 'rect' as const, length_m: size.length_m, width_m: size.width_m } : null);
  if (!fp) return '这个设施还没有规划占地（在检查器里填长 × 宽）';
  const c = at ?? centroid(cur.inst.boundary);
  let polygon: XY[];
  if (fp.type === 'circle' && fp.radius_m) {
    polygon = Array.from({ length: 20 }, (_, k) => {
      const t = (k / 20) * Math.PI * 2;
      return [c[0] + fp.radius_m! * Math.cos(t), c[1] + fp.radius_m! * Math.sin(t)] as XY;
    });
  } else if (fp.type === 'polygon' && fp.points?.length) {
    polygon = fp.points.map(([x, y]) => [c[0] + x, c[1] + y] as XY);
  } else {
    const hl = (fp.length_m ?? 1) / 2, hw = (fp.width_m ?? 1) / 2;
    polygon = [[c[0] - hl, c[1] - hw], [c[0] + hl, c[1] - hw], [c[0] + hl, c[1] + hw], [c[0] - hl, c[1] + hw]];
  }
  polygon = polygon.map(([x, y]) => [Math.round(x * 100) / 100, Math.round(y * 100) / 100] as XY);
  const kind = (p.obstacle_kind && p.obstacle_kind in OBSTACLE_STYLE ? p.obstacle_kind : 'other') as ObstacleKind;
  const ref = refOf(a, ver, 'facility');
  edit((i) => {
    const ob: FleetObstacle & { asset?: AssetRef } = { id: nextObstacleId(i.obstacles), kind, name: a.name, polygon, asset: ref };
    return { ...i, obstacles: [...i.obstacles, ob], asset_refs: upsertRef(i.asset_refs, ref, false) };
  });
  return null;
}

/** Background layer from a map asset version (raster, vector or calibrated image) in task-map metres. */
export function backgroundOf(a: Asset, ver: AssetVersion): BackgroundLayer | string {
  const ref = refOf(a, ver, 'map');
  const m = ver.meta;
  if (a.subtype === 'ros_grid') {
    if (!m.confirmed?.frame || !m.frame) return '先在预览里确认这张栅格地图的分辨率、原点与单位';
    return { asset: ref, type: 'raster', file: 'derived/preview.png', affine: m.frame.affine, size_px: [m.frame.width_px, m.frame.height_px], opacity: 0.6 };
  }
  if (a.subtype === 'vector') {
    if (!m.confirmed?.frame) return '先在预览里确认坐标换算';
    return { asset: ref, type: 'vector', file: m.features ?? 'derived/features_local.json', opacity: 0.7 };
  }
  if (a.subtype === 'image') {
    if (!m.calibration || !m.confirmed?.calibration) return '图片还没有标定：先在预览里用已知距离或控制点标定';
    return { asset: ref, type: 'image', file: m.image ?? m.primary ?? '', affine: m.calibration.matrix, size_px: m.size_px ?? undefined, opacity: 0.75 };
  }
  return '这种地图不能作为任务地图底图（Gazebo 世界只作仿真参考）';
}

/** Store the background on the open (user) scenario; it is display-only and never reaches the solver. */
export async function setBackground(layer: BackgroundLayer | null): Promise<string | null> {
  const st = useStudio.getState();
  if (!st.scenario) return '先在「任务规划」里打开一个任务地图';
  await flushSave();
  const sc = useStudio.getState().scenario!;
  if ((sc as { origin?: string }).origin !== 'user') return '内置或资源库场景不能直接修改：先在地图上做任意修改，它会自动另存为“我的场景”';
  const layers = { ...(sc.layers ?? {}) } as Record<string, unknown>;
  if (layer) layers.background = layer;
  else delete layers.background;
  try {
    const stored = await studio.saveScenario(sc.id, { layers });
    useStudio.setState({ scenario: stored as unknown as Scenario });
    if (layer) edit((i) => ({ ...i, asset_refs: upsertRef(i.asset_refs, layer.asset, true) }));
    return null;
  } catch (e) {
    return (e as Error).message;
  }
}

export function openTaskMap(id: string) {
  useStudio.getState().setWorkspace('plan');
  navigate(`#/plan/${encodeURIComponent(id)}`);
}
