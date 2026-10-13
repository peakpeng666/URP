/**
 * Types for the static interface documented in docs/DATA_API.md (schema v1,
 * produced by scripts/convert_data.py). `null` means "not recorded / role not
 * applicable" and must never be read as zero.
 */
export type Split = 'train' | 'confirmation' | 'risk';
export type Order = 'random' | 'ascending' | 'descending';
export type Family =
  | 'weibull_3_45'
  | 'uniform_1_100'
  | 'small_beta_2_5'
  | 'large_beta_5_2'
  | 'normal_50_15'
  | 'bimodal_20_30_70_80';
export type Policy = 'BF' | 'BF_then_EoH' | 'published_EoH' | 'SELECTOR';
export type Branch = 'BF' | 'BF_then_EoH';
export type OraclePreference = Branch | 'tie';

export interface SourceRef {
  path: string;
  url: string;
  bytes: number;
  sha256: string;
}

export interface RunDescriptor {
  run_id: string;
  policy: Policy;
  branch: Branch | 'published_EoH';
  used_bins: number;
  status: string;
  steps: number;
  data_url: string;
  sha256: string;
  source: Record<string, SourceRef>;
}

/** One row of analysis/<split>_per_stream.csv. Train rows lack selector fields. */
export interface StreamResults {
  instance_id: string;
  group_id: string;
  split: Split;
  family: Family;
  replicate: number;
  order: Order;
  BF: number;
  BF_then_EoH: number;
  published_EoH?: number | null;
  SELECTOR?: number | null;
  SBS: number;
  branch_oracle: number;
  oracle_preferred: OraclePreference;
  SBS_regret: number;
  selected_branch?: Branch | null;
  selector_minus_SBS?: number | null;
  selector_regret?: number | null;
  full_run_oracle?: number | null;
  selector_minus_full_EoH?: number | null;
}

export interface Stream {
  instance_id: string;
  group_id: string;
  family: Family;
  split: Split;
  order: Order;
  replicate: number;
  n: number;
  capacity: number;
  multiset_sha256: string;
  results: StreamResults;
  runs: RunDescriptor[];
  source: SourceRef;
  input_url: string;
  decision_url?: string | null;
}

export interface Catalog {
  schema_version: number;
  streams: Stream[];
}

export interface MeanBins {
  BF: number;
  BF_then_EoH: number;
  SBS: number;
  SELECTOR: number;
  branch_oracle: number;
  full_run_oracle: number;
  published_EoH: number;
}

export interface SplitSummary {
  n: number;
  mean_bins: MeanBins;
  selector_minus_SBS_mean: number;
  SBS_oracle_headroom: number;
  selector_oracle_regret: number;
  headroom_recovered_fraction: number | null;
  W_T_L_vs_SBS: [number, number, number];
  worst_harm_vs_SBS: number;
  best_gain_vs_SBS: number;
  choices: Record<Branch, number>;
  oracle_preferences: Record<OraclePreference, number>;
  cluster_bootstrap_95_percentile_CI?: [number, number];
}

export interface RiskGroupSummary {
  group: string;
  choice: Branch;
  oracle_preferences: OraclePreference[];
  selector_regrets: number[];
  oracle_preference_reverses: boolean;
}

export interface Summary {
  bootstrap: { interpretation: string; replicates: number; seed: string; unit: string };
  compute: {
    check: Record<string, unknown> & { passed: boolean; scope: string };
    fit_cpu_seconds: number;
    run: Record<string, unknown>;
  };
  confirmation: SplitSummary;
  risk: { groups: RiskGroupSummary[]; summary: SplitSummary };
  training: {
    SBS_oracle_headroom: number;
    branch_oracle_mean: number;
    mean_bins: [number, number];
    n: number;
    sbs: Branch;
  };
}

export interface Model {
  k: number;
  mean: number[];
  scale: number[];
  x: number[][];
  y: number[][];
  sbs_index: number;
}

export interface ValidationCheck {
  name: string;
  status: string;
  seconds?: number;
  [key: string]: unknown;
}

export interface ProjectValidation {
  schemaVersion?: number;
  status: 'PASS' | 'FAIL' | 'PENDING' | string;
  passed?: boolean;
  generatedAt?: string;
  scope?: string;
  environment?: Record<string, string>;
  coverage?: Record<string, number>;
  tolerances?: Record<string, string | number>;
  checks?: ValidationCheck[];
  failures?: unknown[];
  metrics?: unknown;
}

export interface ImportValidation {
  status: string;
  created_utc: string;
  archive_sha256: string;
  archive_bytes: number;
  zip_members: number;
  manifest_entries: number;
  manifest_sha256: string;
  count_note: string;
  scope: string;
}

export interface Meta {
  schema_version: number;
  counts: {
    streams: number;
    runs: number;
    streams_by_split: Record<Split, number>;
    runs_by_split: Record<Split, number>;
  };
  summary: Summary;
  protocol: Record<string, unknown> & {
    capacity: number;
    n: number;
    switch_after: number;
    families: Family[];
    orders: Order[];
    features: { names: string[]; [k: string]: unknown };
    selector: Record<string, string | number>;
    status: string;
    question: string;
  };
  model: Model;
  training_rows: string[];
  sources: Record<string, SourceRef>;
  historical_audit: Record<string, unknown> & {
    scientific_result_status: string;
    historical_total_900_cpu_compliance: string;
  };
  import_validation: ImportValidation;
  project_validation: ProjectValidation;
}

export interface Cell {
  family: Family;
  order: Order;
  n: number;
  BF: number;
  BF_then_EoH: number;
  published_EoH: number;
  SELECTOR: number;
  SBS: number;
  branch_oracle: number;
  full_run_oracle: number;
  selector_minus_SBS: number;
  SBS_headroom: number;
  selector_regret: number;
  BF_selections: number;
  EoH_selections: number;
  wins: number;
  ties: number;
  losses: number;
}

export interface NeighborRow {
  index: number;
  instance_id: string;
  family: Family;
  order: Order;
  labels: [number, number];
  squared_distance: number;
  source?: SourceRef;
}

export interface Decision {
  schema_version: number;
  instance_id: string;
  features: number[];
  feature_names: string[];
  neighbors: number[];
  squared_distances: number[];
  predicted_final_bins: [number, number];
  selected_index: number;
  neighbor_rows: NeighborRow[];
  selector_consumed_count: number;
  source: Record<string, SourceRef>;
}

/** Full run record from /data/runs/<run_id>.json (original fields + arrays). */
export interface RunRecord {
  schema_version: number;
  run_id: string;
  instance_id: string;
  policy: Policy;
  branch: Branch | 'published_EoH';
  status: string;
  error: string | null;
  steps: number;
  used_bins: number;
  capacity: number;
  items: number[];
  items_sha256: string;
  prefix_features: number[] | null;
  prefix_remaining_sha256: string | null;
  selector_consumed_count: number | null;
  trajectory_file: string;
  trajectory_sha256: string;
  decision: (Omit<Decision, 'schema_version' | 'instance_id' | 'source' | 'selector_consumed_count'>) | null;
  assignment: number[];
  pre_remaining: number[];
  post_remaining: number[];
  feasible_counts: number[];
  used_bins_after: number[];
  remaining: number[];
  source: Record<string, SourceRef>;
  cpu_loop_seconds?: number;
  cpu_selector_seconds?: number;
  wall_loop_seconds?: number;
}
