import type { Route, Scenario, Solution, XY } from '../lab/types';

export type ObstacleKind = 'pond' | 'building' | 'greenhouse' | 'tree' | 'ditch' | 'rock' | 'other';

export interface FleetTask {
  id: number;
  xy: XY;
  demand: number;
  label: string;
  plot?: string | null;
  service_s?: number;
}

export interface FleetObstacle {
  id: string;
  kind: ObstacleKind;
  name?: string;
  polygon: XY[];
}

export interface FleetPlot {
  id: string;
  name: string;
  crop?: string;
  rows_deg?: number;
  polygon: XY[];
}

export interface FleetVehicles {
  count: number;
  capacity: number;
  speed_mps: number;
  trips: 'single' | 'multi';
  names?: string[];
}

export interface FleetInstance {
  boundary: XY[];
  plots: FleetPlot[];
  obstacles: FleetObstacle[];
  depot: XY;
  tasks: FleetTask[];
  vehicles: FleetVehicles;
  objective: 'total_distance' | 'makespan';
  robot_radius: number;
  units: 'm';
  meta?: { task_word?: string; margin_m?: number; road_m?: number };
}

export interface FleetRoute extends Route {
  vehicle_name: string;
  color: string;
  trips: number[][];
  duration_s: number;
}

export interface PerVehicle {
  vehicle: string;
  color: string;
  tasks: number;
  trips: number;
  load: number;
  length_m: number;
  duration_s: number;
}

export interface ComposeCard {
  key: string;
  label: string;
  value: string;
}

export interface ParseResult {
  spec: Record<string, unknown>;
  found: { key: string; label: string; value: unknown; text: string }[];
  defaults: { key: string; label: string; value: unknown }[];
  cards: ComposeCard[];
}

export interface FleetScenario extends Omit<Scenario, 'instance'> {
  instance: FleetInstance;
  origin?: string;
  compose?: { text: string; cards: ComposeCard[]; found: ParseResult['found']; defaults: ParseResult['defaults']; seed: number };
}

export type Selection =
  | { type: 'task'; id: number }
  | { type: 'obstacle'; id: string }
  | { type: 'plot'; id: string }
  | { type: 'depot' }
  | { type: 'boundary' }
  | null;

export type Tool = 'select' | 'pan' | 'task' | 'obstacle' | 'plot' | 'depot';

export interface Reference {
  key: string;
  type: string;
  title: string;
  authors: string[];
  year: number | null;
  venue: string | null;
  doi: string | null;
  url: string | null;
  tags: string[];
}

export interface CvrplibSet {
  id: string;
  problem: string;
  citation: string;
  year: number;
  link: string | null;
  ref: string | null;
  count: number;
  note: string;
  cite: string;
  supported: boolean;
}

export interface CvrplibInstance {
  name: string;
  set: string;
  problem: string;
  n: number | null;
  k: number | null;
  q: number | null;
  bks: number | null;
  optimal: boolean;
  cached: boolean;
  supported: boolean;
  scenario_id: string;
}

export interface FieldEntry {
  id: string;
  country: string;
  country_name: string;
  area_ha: number;
  perimeter_m: number;
  vertices: number;
  holes: number;
  convexity: number;
  size_m: [number, number];
  scenario_id: string;
  image: boolean;
}

export interface StudySpec {
  title: string;
  note?: string;
  scenarios: string[];
  algorithms: { id: string; params?: Record<string, unknown> }[];
  budgets?: number[];
  seeds?: number[];
}

export interface Study {
  study_id: string;
  title: string;
  note: string;
  created_utc: string;
  spec: StudySpec;
  design?: { scenario_id: string; algorithm_id: string; params: Record<string, unknown>; run_id: string; state?: string; status?: string; objective?: number | null }[];
  skipped: string[];
  progress: { total: number; finished: number; counts: Record<string, number>; state: 'done' | 'running' };
}

export interface AnalysisSummary {
  algorithm: string;
  id: string;
  name: string;
  source: string;
  instances: number;
  runs: number;
  successes: number;
  success_rate: number | null;
  gap_mean: number | null;
  gap_sd: number | null;
  gap_median: number | null;
  gap_best: number | null;
  time_mean: number | null;
  time_median: number | null;
  mean_rank: number | null;
  wins: number;
}

export interface Analysis {
  empty: boolean;
  n_runs: number;
  n_instances: number;
  n_complete_instances: number;
  algorithms: string[];
  summary: AnalysisSummary[];
  per_instance: { instance: string; scenario_id: string; title: string; reference: number | null; reference_kind: string; cells: Record<string, { mean: number | null; gap_mean: number | null; rank: number | null; runs: number; failures: number; time_mean: number | null }> }[];
  tests: {
    alpha: number;
    k: number;
    n: number;
    friedman?: { statistic?: number; p_value?: number; significant?: boolean; error?: string };
    nemenyi?: { q_alpha: number; critical_difference: number; mean_ranks: Record<string, number> };
    wilcoxon_holm: { a: string; b: string; n: number; a_better: number; b_better: number; ties: number; p_value?: number; p_holm?: number; significant?: boolean }[];
  };
  performance_profile: { taus: number[]; curves: Record<string, number[]> };
  ecdf: Record<string, number[]>;
  anytime: { grid: number[]; median: Record<string, (number | null)[]> };
  scatter: { algorithm: string; time: number | null; gap: number | null; instance: string; run_id: string }[];
  reference_note: string;
}

export interface InstanceSpace {
  points: { x: number; y: number; best: string | null; scenario_id: string; title: string }[];
  features?: string[];
  loadings?: number[][];
  explained_variance?: number[];
  footprints?: Record<string, XY[]>;
  method?: string;
  note?: string;
}

export type FleetSolution = Solution & { routes: FleetRoute[]; trace?: [number, number][] };

/* ------------------------------------------------------------ field sim -- */
export interface FieldVehicleState {
  name: string;
  label: string;
  color: string;
  state: 'waiting' | 'driving' | 'servicing' | 'done' | 'failed';
  pose: [number, number, number] | null;
  speed: number;
  progress: number;
  distance_m: number;
  path_length_m: number;
  tasks_done: number;
  tasks_total: number;
  cross_track_mean_m: number | null;
  cross_track_max_m: number | null;
  duration_s: number | null;
  planned_length_m: number | null;
  planned_duration_s: number | null;
}
export interface LiveWeb {
  ros?: { url: string; protocol: string };
  gazebo?: { url: string; key: string; world: string; bounds?: [number, number, number, number] };
}
export interface FieldSimMetrics {
  tasks_total: number;
  tasks_reached: number;
  vehicles_done: number;
  makespan_s: number | null;
  planned_makespan_s: number | null;
  total_distance_m: number;
  planned_total_distance_m: number | null;
  cross_track_mean_m: number;
  cross_track_max_m: number;
}
export interface FieldSimState {
  phase: 'idle' | 'starting' | 'ready' | 'running' | 'finished' | 'failed' | 'stopped';
  running: boolean;
  session_id?: string;
  run_id?: string;
  scenario_id?: string;
  algorithm?: string | null;
  world?: string;
  sim_time?: number;
  real_time_factor?: number | null;
  components: Record<string, string>;
  web: LiveWeb;
  vehicles: FieldVehicleState[];
  metrics?: Partial<FieldSimMetrics>;
  errors: string[];
  warnings: string[];
  result?: string | null;
}
export interface FieldSimSummary {
  session_id: string;
  run_id: string;
  scenario_id: string;
  algorithm: string | null;
  world: string;
  finished_utc: string;
  state: 'succeeded' | 'failed';
  metrics: FieldSimMetrics;
  real_time_factor: number | null;
  sim_time: number | null;
  vehicles: Pick<FieldVehicleState, 'name' | 'label' | 'color' | 'state' | 'distance_m' | 'duration_s' | 'planned_length_m' | 'planned_duration_s' | 'tasks_done' | 'tasks_total' | 'cross_track_mean_m' | 'cross_track_max_m'>[];
}
