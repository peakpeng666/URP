/** Asset library client (/lab/api/assets). */
import { LabApiError } from '../../lab/api';
import type { Scenario, XY } from '../../lab/types';

const BASE = '/lab/api';

export type AssetKind = 'map' | 'vehicle' | 'facility' | 'scenario';
export type Level = 'simulation' | 'planning' | 'display' | 'incomplete' | undefined;
export type Affine = [[number, number, number], [number, number, number]];

export interface CheckItem { key: string; label: string; ok: boolean; value?: string | number | null; detail?: string }
export interface Capabilities {
  display?: { ok: boolean; items: CheckItem[] };
  planning?: { ok: boolean; items: CheckItem[]; solver?: Record<string, { ignored: string[] } & Record<string, unknown>> };
  simulation?: { ok: boolean; items: CheckItem[]; adapters?: { id: string; label: string; ok: boolean; reason: string; problem_classes?: string[] }[] };
  level?: Level;
}
export interface PlanningProfile {
  footprint?: { type: 'rect' | 'circle' | 'polygon'; length_m?: number | null; width_m?: number | null; radius_m?: number | null; points?: XY[] } | null;
  capacity?: number | null;
  /** none: inspection / sampling vehicle that carries no load (no capacity constraint) */
  payload?: 'none' | 'load' | null;
  speed_mps?: number | null;
  kinematics?: 'differential' | 'skid_steer' | 'tracked' | 'omni' | 'ackermann' | 'articulated' | null;
  min_turn_radius_m?: number | null;
  work_width_m?: number | null;
  footprint_source?: string | null;
  obstacle_kind?: string;
  height_m?: number | null;
}
export interface DisplayMeta {
  model?: string | null; urdf?: string | null; sdf?: string | null; builtin?: string;
  forward?: string; up?: string; scale?: number; size_m?: { length_m: number; width_m: number; height_m: number } | null; confirmed?: boolean;
}
export interface MapFrame {
  resolution: number; origin: [number, number, number]; width_px: number; height_px: number; width_m: number; height_m: number;
  affine: Affine; bounds: [number, number, number, number]; units: 'm'; frame_id: string;
}
export interface Calibration { model: string; matrix: Affine; rmse_m: number | null; residuals_m: number[]; scale_m_per_px: number; rotation_deg: number; points: number; warnings: string[]; control?: { px: XY; world: XY }[] }
export interface VersionMeta {
  inspection?: Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
  primary?: string;
  frame?: MapFrame; stats?: Record<string, number>; occupancy?: string; image?: string; confirmed?: Record<string, boolean>;
  transform?: Record<string, any>; crs?: Record<string, any>; summary?: Record<string, any>; features?: string; // eslint-disable-line @typescript-eslint/no-explicit-any
  size_px?: [number, number] | null; calibration?: Calibration | null;
  display?: DisplayMeta; planning?: PlanningProfile; simulation?: Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
  scenario?: Scenario; problem_class?: string; asset_refs?: AssetRef[]; summary_text?: string;
  [k: string]: unknown;
}
export interface AssetVersion {
  v: number; created_utc: string; sha256: string; files: { path: string; size: number; sha256: string }[];
  source: { type: string; uri?: string; license?: string; attribution?: string; authors?: string[]; retrieved_utc?: string; original_files?: string[] };
  meta: VersionMeta; validation: { errors: string[]; warnings: string[] }; preview: string | null; locked: boolean; locked_utc: string | null;
  based_on: number | null; capabilities: Capabilities; urls: { preview: string | null; base: string };
}
export interface AssetSummary {
  id: string; kind: AssetKind; subtype: string; name: string; category: string; tags: string[]; archived: boolean; builtin: boolean;
  current: number; versions: number; locked: boolean; updated_utc: string; created_utc: string; thumb: string | null;
  license?: string; source_type?: string; level?: Level; errors: number; warnings: number;
  /** map frame / image calibration / model orientation confirmed by the user (null: nothing to confirm) */
  confirmed?: boolean | null;
}
export interface Asset extends Omit<AssetSummary, 'versions'> { versions: AssetVersion[]; notes: string; summary: AssetSummary; thumb: string | null }
export interface AssetRef { role: 'map' | 'vehicle' | 'facility' | 'template'; id: string; version: number; sha256: string; name?: string }
export interface ImportReport {
  token: string; files: { path: string; size: number; kind: string }[]; warnings: string[]; errors: string[];
  subtype: string | null; kind: AssetKind | null; primary: string | null; inspection: Record<string, any>; others: string[]; // eslint-disable-line @typescript-eslint/no-explicit-any
  preview: string | null; thumb: string | null;
}
export interface References { scenarios: { id: string; title: string; version: number | null; role?: string }[]; runs: { run_id: string; scenario_id: string; version: number; algorithm?: string; created_utc?: string }[]; total: number; by_version: Record<string, number> }
export interface LocalCatalog {
  fuel_models: { root: string; path: string; sdf: string; owner: string; name: string; title: string; version: number; description: string; authors: string[]; thumbnails: string[]; size_bytes: number; source_uri: string }[];
  ros_descriptions: { root: string; package: string; entries: string[]; meshes: number }[];
  gazebo_worlds: { root: string; path: string; name: string; group: string; size_bytes: number }[];
}
export interface PlanningGeometry { boundary: XY[] | null; plots: { id: string; name: string; crop: string; rows_deg: number; polygon: XY[] }[]; obstacles: { id: string; kind: string; name: string; polygon: XY[] }[]; tasks: { id: number; xy: XY; demand: number; label: string; service_s: number }[]; depot: XY | null; notes: string[]; stats?: Record<string, number | string> }

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      method, cache: 'no-store',
      headers: body === undefined ? { Accept: 'application/json' } : { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new LabApiError('连接不上工作台服务（127.0.0.1:4100）', 'network', 0);
  }
  const text = await res.text();
  const data = text ? (JSON.parse(text) as unknown) : null;
  if (!res.ok) {
    const e = (data ?? {}) as { error?: string; message?: string };
    throw new LabApiError(e.message ?? `请求失败（HTTP ${res.status}）`, e.error ?? 'http_error', res.status);
  }
  return data as T;
}

/** Multipart upload; the header marks it as a deliberate in-app upload (the gateway refuses others). */
async function upload<T>(path: string, files: { file: File; path: string }[], fields: Record<string, string> = {}): Promise<T> {
  const form = new FormData();
  for (const f of files) form.append('files', f.file, f.file.name);
  form.append('paths', JSON.stringify(files.map((f) => f.path)));
  for (const [k, v] of Object.entries(fields)) form.append(k, v);
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { method: 'POST', body: form, headers: { 'X-Workbench-Upload': '1', Accept: 'application/json' } });
  } catch {
    throw new LabApiError('连接不上工作台服务（127.0.0.1:4100）', 'network', 0);
  }
  const text = await res.text();
  const data = text ? (JSON.parse(text) as unknown) : null;
  if (!res.ok) {
    const e = (data ?? {}) as { error?: string; message?: string };
    throw new LabApiError(e.message ?? `上传失败（HTTP ${res.status}）`, e.error ?? 'http_error', res.status);
  }
  return data as T;
}

export const assetsApi = {
  list: (kind?: AssetKind, q?: string, archived = false) => {
    const p = new URLSearchParams();
    if (kind) p.set('kind', kind);
    if (q) p.set('q', q);
    if (archived) p.set('archived', 'true');
    return call<{ assets: AssetSummary[]; kinds: Record<AssetKind, string> }>('GET', `/assets?${p}`);
  },
  get: (id: string) => call<Asset>('GET', `/assets/${id}`),
  patch: (id: string, body: Partial<Pick<Asset, 'name' | 'category' | 'tags' | 'notes' | 'archived'>>) => call<Asset>('PATCH', `/assets/${id}`, body),
  meta: (id: string, v: number, meta: Partial<VersionMeta>, source?: Record<string, unknown>) => call<Asset>('POST', `/assets/${id}/v/${v}/meta`, { meta, source }),
  lock: (id: string, v: number) => call<Asset>('POST', `/assets/${id}/v/${v}/lock`, {}),
  fork: (id: string, v: number, meta: Partial<VersionMeta> = {}) => call<Asset>('POST', `/assets/${id}/v/${v}/fork`, { meta }),
  setCurrent: (id: string, version: number) => call<Asset>('POST', `/assets/${id}/current`, { version }),
  references: (id: string) => call<References>('GET', `/assets/${id}/references`),
  remove: (id: string) => call<{ deleted: string }>('DELETE', `/assets/${id}`),
  inspect: (files: { file: File; path: string }[], kind = '', assumeMetres = false) =>
    upload<ImportReport>('/assets/inspect', files, { kind, assume_metres: String(assumeMetres) }),
  reinspect: (token: string, body: { kind?: string; assume_metres?: boolean }) => call<ImportReport>('POST', `/assets/staging/${token}/reinspect`, body),
  dropStaging: (token: string) => call<null>('DELETE', `/assets/staging/${token}`),
  commit: (body: { token: string; kind?: AssetKind; name?: string; category?: string; tags?: string[]; license?: string; attribution?: string; source_uri?: string; obstacle_kind?: string }) =>
    call<Asset>('POST', '/assets/commit', body),
  replace: (id: string, files: { file: File; path: string }[]) => upload<Asset>(`/assets/${id}/replace`, files),
  local: () => call<LocalCatalog>('GET', '/assets/local/catalog'),
  importLocal: (body: { root: string; path: string; kind?: AssetKind; name?: string; license?: string; attribution?: string; source_uri?: string }) =>
    call<Asset>('POST', '/assets/local/import', body),
  calibrate: (body: { points?: { px: XY; world: XY }[]; model?: 'similarity' | 'affine'; known_distance?: { p1: XY; p2: XY; distance_m: number; origin_px?: XY; rotation_deg?: number } }) =>
    call<Calibration>('POST', '/assets/calibrate', body),
  geometry: (id: string, v: number, body: { unknown_as?: 'obstacle' | 'free'; min_area_m2?: number; simplify_m?: number } = {}) =>
    call<PlanningGeometry>('POST', `/assets/${id}/v/${v}/planning-geometry`, body),
  saveTemplate: (scenario_id: string, name?: string) => call<Asset>('POST', '/assets/scenario-template', { scenario_id, name }),
  instantiate: (id: string, title?: string) => call<Scenario>('POST', `/assets/${id}/instantiate`, { title }),
};

export const assetUrl = (id: string, v: number, rel: string | null | undefined) => (rel ? `${BASE}/assets/${id}/v/${v}/file/${rel.split('/').map(encodeURIComponent).join('/')}` : null);
export const stagingUrl = (token: string, rel: string | null | undefined) => (rel ? `${BASE}/assets/staging/${token}/file/${rel.split('/').map(encodeURIComponent).join('/')}` : null);
export const localUrl = (root: string, rel: string) => `${BASE}/assets/local/file/${root}/${rel.split('/').map(encodeURIComponent).join('/')}`;

export const KIND_LABEL: Record<AssetKind, string> = { map: '地图', vehicle: '车辆', facility: '障碍物与设施', scenario: '场景' };
export const SUBTYPE_LABEL: Record<string, string> = {
  ros_grid: 'ROS 栅格地图', vector: '矢量田块 / 道路', image: '图片底图', gazebo_world: 'Gazebo 世界',
  gltf: 'glTF 模型', urdf: 'URDF 机器人', sdf_model: 'SDF 模型', mesh: '网格模型', builtin: '内置', task_map: '任务地图模板',
};
export const LEVEL_LABEL: Record<string, { text: string; tone: 'green' | 'blue' | 'gray' | 'orange' }> = {
  simulation: { text: '可仿真', tone: 'green' }, planning: { text: '可规划', tone: 'blue' }, display: { text: '仅展示', tone: 'gray' }, incomplete: { text: '待完善', tone: 'orange' },
};
export const SPDX = ['CC0-1.0', 'CC-BY-4.0', 'CC-BY-SA-4.0', 'CC-BY-NC-4.0', 'Apache-2.0', 'MIT', 'BSD-3-Clause', 'GPL-3.0-only', 'ODbL-1.0', 'Proprietary', '未声明'];

/** Pixel→world affine as an SVG matrix (inside a group that already draws world coordinates). */
export const svgMatrix = (a: Affine) => `matrix(${a[0][0]} ${a[1][0]} ${a[0][1]} ${a[1][1]} ${a[0][2]} ${a[1][2]})`;
export const applyAffine = (a: Affine, u: number, v: number): XY => [a[0][0] * u + a[0][1] * v + a[0][2], a[1][0] * u + a[1][1] * v + a[1][2]];
export function invertAffine(a: Affine): Affine {
  const [[p, q, r], [s, t, w]] = a;
  const det = p * t - q * s;
  return [[t / det, -q / det, (q * w - t * r) / det], [-s / det, p / det, (s * r - p * w) / det]];
}
