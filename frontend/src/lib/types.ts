// Mirrors the FastAPI response shapes (docs 06/08). In a fuller build these would
// be generated from /api/openapi.json; hand-typed here to keep the MVP dependency-free.

export type FeatureType = "numeric" | "categorical" | "boolean" | "datetime" | "text";

export interface NumericFeature {
  type: "numeric";
  dist?: string | null;
  params?: Record<string, number>;
  min?: number | null;
  max?: number | null;
  dtype?: "int" | "float";
  description?: string | null;
}
export interface CategoricalFeature {
  type: "categorical";
  categories: string[];
  weights?: number[] | null;
  description?: string | null;
}
export interface BooleanFeature {
  type: "boolean";
  rate: number;
  description?: string | null;
}
export interface DatetimeFeature {
  type: "datetime";
  start: string;
  end: string;
  granularity?: "second" | "minute" | "hour" | "day";
  dist?: string;
  description?: string | null;
}
export interface TextFeature {
  type: "text";
  generator?: string;
  length?: { min: number; max: number };
  description?: string | null;
}
export type Feature =
  | NumericFeature
  | CategoricalFeature
  | BooleanFeature
  | DatetimeFeature
  | TextFeature;

// Causal graph (04 §5). Edges use the spec's `from`/`to` aliases on the wire.
export interface CausalEdge {
  from: string;
  to: string;
  fn: string; // linear | logistic | polynomial | map | identity
  weight?: number | null;
  bias?: number | null;
  coeffs?: number[] | null;
  mapping?: Record<string, number> | null;
}
export interface NoiseSpec {
  dist: string; // "none" | a numeric distribution name
  params?: Record<string, number>;
}
export interface Intervention {
  do: Record<string, number>;
}
export interface CausalGraph {
  edges: CausalEdge[];
  noise?: Record<string, NoiseSpec>;
  interventions?: Intervention[];
}

export interface Spec {
  datadoom_version: string;
  name: string;
  description?: string | null;
  seed?: number | null;
  rows: number;
  features: Record<string, Feature>;
  causal?: CausalGraph | null;
  difficulty?: unknown;
  failures?: unknown[];
  export?: unknown;
  meta?: Record<string, unknown>;
}

export interface SpecDetail {
  spec_id: string;
  spec_hash: string;
  version: number;
  datadoom_version: string;
  created_at: string;
  body: Spec;
}

export interface LatestRun {
  run_id: string;
  status: string;
  compliance_score?: number | null;
}

export interface DatasetSummary {
  dataset_id: string;
  name: string;
  description?: string | null;
  status: string;
  rows?: number | null;
  features?: number | null;
  compliance_score?: number | null;
  created_at: string;
  updated_at: string;
}

export interface Dataset {
  dataset_id: string;
  name: string;
  description?: string | null;
  status: string;
  current_spec?: SpecDetail | null;
  latest_run?: LatestRun | null;
  created_at: string;
  updated_at: string;
}

export interface RunSummary {
  run_id: string;
  dataset_id: string;
  spec_id: string;
  name?: string | null;
  seed: number;
  status: string;
  stage?: string | null;
  progress_pct: number;
  compliance_score?: number | null;
  error?: Record<string, unknown> | null;
  metrics?: Record<string, unknown> | null;
  started_at?: string | null;
  finished_at?: string | null;
  created_at: string;
}

export interface Artifact {
  artifact_id: string;
  run_id: string;
  version: string;
  split?: string | null;
  format: string;
  size_bytes: number;
  checksum_sha256: string;
  created_at: string;
}

export interface FeatureCompliance {
  feature: string;
  dist: string;
  target_params: Record<string, number>;
  empirical: Record<string, number>;
  ks_statistic: number;
  p_value: number;
  passed: boolean | null; // null when KS is not applicable (int/discrete/clamped)
  clamped_fraction: number;
  applicable?: boolean;
  note?: string | null;
}

export interface CausalTruthEdge {
  from: string;
  to: string;
  fn: string;
  weight?: number;
  bias?: number;
  coeffs?: number[];
  mapping?: Record<string, number>;
  active: boolean;
}
export interface CausalTruth {
  nodes?: string[] | null;
  edges: CausalTruthEdge[];
  interventions: Record<string, number>;
  topological_order?: string[] | null;
}
export interface MatrixReport {
  method: string;
  units?: string;
  columns: string[];
  matrix: (number | null)[][];
}

export interface Report {
  report_id: string;
  run_id: string;
  compliance_score?: number | null;
  distribution?: {
    alpha: number;
    compliance_score: number;
    applicable_features?: number;
    assessed_features?: number;
    features: FeatureCompliance[];
  } | null;
  correlation?: MatrixReport | null;
  mutual_information?: MatrixReport | null;
  causal_truth?: CausalTruth | null;
  difficulty?: unknown;
  failures?: unknown;
  determinism?: {
    spec_hash: string;
    seed: number;
    namespace_key_digests: Record<string, string>;
    artifact_checksums: Record<string, string>;
  } | null;
}

export interface Preview {
  columns: string[];
  rows: unknown[][];
  total: number;
}

export interface Estimate {
  estimated_runtime_seconds: number;
  estimated_ram_mb: number;
  estimated_size_bytes: number;
  features: number;
  edges: number;
  gpu_required: boolean;
}

export interface ErrorEnvelope {
  error: { code: string; message: string; locator?: string | null };
}

// WebSocket progress events (08 §7).
export type RunEvent =
  | { type: "stage"; stage: string; status: "running" | "done"; pct: number }
  | { type: "log"; level: string; message: string }
  | { type: "completed"; run_id: string; compliance_score: number; report_id: string }
  | { type: "failed"; stage: string; message: string; traceback?: string }
  | { type: "cancelled"; run_id: string };
