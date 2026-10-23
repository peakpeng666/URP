/** Live local API. Mutable job state is deliberately never promise-cached. */
export interface CvrpProblem {
  coordinates: [number, number][];
  demands: number[];
  capacity: number;
  K: number;
}

export interface JobRequest extends CvrpProblem {
  algorithm: string;
  seed: number;
  budget_seconds: number;
}

export interface JobResult {
  status: string;
  feasible: boolean;
  cost: number | null;
  routes: number[][] | null;
  process_wall_seconds?: number;
  cpu_seconds?: number;
  checker_wall_seconds?: number;
  checkpoint_checks?: { valid: boolean; errors: string[] }[];
  worker_error?: { message: string } | null;
}

export interface Job {
  id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'interrupted';
  scene_id: string;
  scene_revision: number;
  input_sha256: string;
  payload_sha256: string;
  source_sha256: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  request: JobRequest;
  result: JobResult | null;
  error: unknown;
}

export type JobSummary = Pick<Job, 'id' | 'status' | 'scene_id' | 'scene_revision' | 'created_at'> & {
  algorithm?: string;
  result_status?: string | null;
  feasible?: boolean | null;
  cost?: number | null;
};

export interface ExperimentSummary {
  id: string;
  title: string;
  revision: number;
  status: string;
  domain: string;
  routing?: unknown;
}

export interface RouteScene {
  experiment_id: string;
  revision: number;
  run_id: string;
  geometry_kind: string;
  simulation_ready: boolean;
  units: { coordinate: string | null; distance: string | null };
  depot: { node_id: number; x: number; y: number };
  task_nodes: { node_id: number; x: number; y: number }[];
  vehicles: { vehicle_id: number; visit_node_ids: number[]; polyline: [number, number][] }[];
  status: { solution_status: string; full_service_success: boolean; has_candidate: boolean };
  metrics: { total_distance: number | null; task_count: number; served_task_count: number | null };
  unserved_task_ids: number[] | null;
}

export class WorkspaceApiError extends Error {
  constructor(message: string, public status: number, public code: string) {
    super(message);
    this.name = 'WorkspaceApiError';
  }
}

export async function requestApi<T>(path: string, options: RequestInit = {}): Promise<T> {
  if (!path.startsWith('/api/') || path.includes('\\') || path.includes('#')) {
    throw new Error('API 地址必须使用本站 /api/ 路径。');
  }
  const response = await fetch(path, { ...options, cache: 'no-store', credentials: 'same-origin' });
  const contentType = response.headers.get('content-type') ?? '';
  if (!contentType.includes('application/json')) {
    throw new WorkspaceApiError('未收到后端 JSON 响应，请检查本地后端与前端代理是否已启动。', response.status, 'invalid_api_response');
  }
  const value = await response.json();
  if (!response.ok) {
    throw new WorkspaceApiError(value.message ?? `请求失败（HTTP ${response.status}）。`, response.status, value.error ?? 'request_failed');
  }
  return value as T;
}

const part = (value: string) => encodeURIComponent(value);
export const getHealth = (signal?: AbortSignal) => requestApi<{
  status: string; mode: string; executes_experiments: boolean;
}>('/api/health', { signal });
export const getAlgorithms = (signal?: AbortSignal) => requestApi<{
  algorithms: { id: string; available: boolean; reason: string | null; deterministic: boolean }[];
}>('/api/algorithms', { signal });
export const getJobs = (signal?: AbortSignal, offset = 0, limit = 50) => requestApi<{
  jobs: JobSummary[]; counts: Record<string, number>; total: number; limit: number; offset: number;
}>(`/api/jobs?limit=${limit}&offset=${offset}`, { signal });
export const getJob = (id: string, signal?: AbortSignal) => requestApi<Job>(`/api/jobs/${part(id)}`, { signal });
export const submitJob = (request: JobRequest) => requestApi<Job>('/api/jobs', {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request),
});
export const getExperiments = (signal?: AbortSignal) => requestApi<{ experiments: ExperimentSummary[] }>('/api/experiments', { signal });
export const getRuns = (experiment: string, revision: number, signal?: AbortSignal) => requestApi<{
  runs: { run_id: string; instance_id: string; solution_status: string }[];
}>(`/api/experiments/${part(experiment)}/runs?revision=${revision}`, { signal });
export const getRouteScene = (experiment: string, revision: number, run: string, signal?: AbortSignal) => requestApi<RouteScene>(
  `/api/v1/experiments/${part(experiment)}/runs/${part(run)}/route-scene?revision=${revision}`, { signal },
);

export const DEMO_PROBLEM: CvrpProblem = {
  coordinates: [[0, 0], [10, 8], [22, 5], [24, 20], [8, 23], [-5, 13]],
  demands: [0, 2, 3, 2, 4, 1], capacity: 7, K: 2,
};

export const DEMO_JSON = `{
  "coordinates": [[0, 0], [10, 8], [22, 5], [24, 20], [8, 23], [-5, 13]],
  "demands": [0, 2, 3, 2, 4, 1],
  "capacity": 7,
  "K": 2
}`;

/** Validate the supported mathematical task, without guessing map units. */
export function parseProblem(text: string): CvrpProblem {
  const value: unknown = JSON.parse(text);
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('任务必须是 JSON 对象。');
  const record = value as Record<string, unknown>;
  const keys = ['coordinates', 'demands', 'capacity', 'K'];
  if (Object.keys(record).some((key) => !keys.includes(key)) || keys.some((key) => !(key in record))) {
    throw new Error('任务需要且仅接受 coordinates、demands、capacity、K 四个字段。');
  }
  const { coordinates, demands, capacity, K } = record;
  if (!Array.isArray(coordinates) || coordinates.length < 2 || coordinates.length > 300
    || coordinates.some((xy) => !Array.isArray(xy) || xy.length !== 2
      || xy.some((v) => typeof v !== 'number' || !Number.isFinite(v) || Math.abs(v) > 1e9))) {
    throw new Error('需要 2 至 300 个有限 XY 坐标（第 0 个为仓库），坐标绝对值不超过 10⁹。');
  }
  if (typeof capacity !== 'number' || !Number.isInteger(capacity) || capacity < 1 || capacity > 1e9) {
    throw new Error('capacity 必须是 1 至 10⁹ 的整数。');
  }
  if (!Array.isArray(demands) || demands.length !== coordinates.length || demands[0] !== 0
    || demands.some((v) => typeof v !== 'number' || !Number.isInteger(v) || v < 0 || v > capacity)) {
    throw new Error('demands 须与坐标一一对应，仓库需求为 0，各点需求为不超过容量的非负整数。');
  }
  if (typeof K !== 'number' || !Number.isInteger(K) || K < 1 || K >= coordinates.length) {
    throw new Error('K 为车队上限，须在 1 至客户数之间。');
  }
  return { coordinates: coordinates as [number, number][], demands, capacity, K };
}

export function terminalJob(status: Job['status']): boolean {
  return status !== 'queued' && status !== 'running';
}

/** Isotropic XY projection; north/up is increasing Y, including degenerate maps. */
export function projectPoints(points: [number, number][], width = 760, height = 360, padding = 32) {
  if (!points.length || points.some((xy) => xy.length !== 2 || xy.some((v) => !Number.isFinite(v)))) return [];
  const xs = points.map((p) => p[0]), ys = points.map((p) => p[1]);
  const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
  const scale = Math.min((width - padding * 2) / Math.max(maxX - minX, 1), (height - padding * 2) / Math.max(maxY - minY, 1));
  return points.map(([x, y]) => [width / 2 + (x - (minX + maxX) / 2) * scale,
    height / 2 - (y - (minY + maxY) / 2) * scale] as [number, number]);
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : typeof error === 'string' ? error : JSON.stringify(error);
}
