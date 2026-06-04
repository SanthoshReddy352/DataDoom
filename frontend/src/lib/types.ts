// Mirrors the FastAPI response shapes (docs 06/08). In a fuller build these would
// be generated from /api/openapi.json; hand-typed here to keep the MVP dependency-free.

export type FeatureType = "numeric" | "categorical" | "boolean" | "datetime" | "text" | "timeseries";

// `emit: false` marks a latent feature: it drives sampling/the SEM and the true
// causal graph, but is NOT shipped (excluded from the data, probe, compliance).
export interface NumericFeature {
  type: "numeric";
  dist?: string | null;
  params?: Record<string, number>;
  min?: number | null;
  max?: number | null;
  dtype?: "int" | "float";
  description?: string | null;
  emit?: boolean | null;
}
export interface CategoricalFeature {
  type: "categorical";
  categories: string[];
  weights?: number[] | null;
  description?: string | null;
  emit?: boolean | null;
}
export interface BooleanFeature {
  type: "boolean";
  rate: number;
  description?: string | null;
  emit?: boolean | null;
}
export interface DatetimeFeature {
  type: "datetime";
  start: string;
  end: string;
  granularity?: "second" | "minute" | "hour" | "day";
  dist?: string;
  description?: string | null;
  emit?: boolean | null;
}
export interface TextFeature {
  type: "text";
  generator?: string; // "lorem" | a realistic provider key (name, email, …)
  locale?: string; // mimesis locale for realistic generators (default "en")
  length?: { min: number; max: number };
  description?: string | null;
  emit?: boolean | null;
}
// Ordered additive series Xt = trend + Σ seasonality + AR(p) + noise (05 §6).
export interface TimeseriesTrend {
  slope?: number;
  intercept?: number;
}
export interface TimeseriesSeason {
  amplitude: number;
  period: number; // > 0
  phase?: number;
}
export interface TimeseriesFeature {
  type: "timeseries";
  trend?: TimeseriesTrend | null;
  seasonality?: TimeseriesSeason[];
  ar?: number[]; // AR coefficients; sum(|ar|) must be < 1 (stationarity)
  noise_std?: number; // sigma of the Gaussian innovations (>= 0)
  min?: number | null;
  max?: number | null;
  dtype?: "int" | "float";
  description?: string | null;
  emit?: boolean | null;
}

/** A latent feature (`emit: false`) is computed but not shipped. */
export function isLatent(feat: Feature): boolean {
  return feat.emit === false;
}

// Realistic-but-deterministic text providers (mimesis), grouped for the Inspector.
// Mirrors engine/dist/providers.py — keep in sync.
export const TEXT_GENERATORS: { group: string; keys: string[] }[] = [
  { group: "Filler", keys: ["lorem"] },
  { group: "People", keys: ["name", "first_name", "last_name", "email", "username", "phone", "occupation", "title", "nationality"] },
  { group: "Places", keys: ["address", "street", "city", "state", "country", "postal_code"] },
  { group: "Business", keys: ["company", "currency", "price"] },
  { group: "Internet", keys: ["url", "hostname", "ipv4"] },
  { group: "Generic text", keys: ["word", "sentence", "color"] },
];

export const TEXT_LOCALES = ["en", "de", "fr", "es", "it", "pt", "ru", "nl", "pl", "sv", "ja", "zh"] as const;
export type Feature =
  | NumericFeature
  | CategoricalFeature
  | BooleanFeature
  | DatetimeFeature
  | TextFeature
  | TimeseriesFeature;

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

// Failure injection (04 §7). One flat shape covers all builtins; the configurator
// only surfaces the fields a given `type` uses. Mirrors the engine's loose
// `extra="allow"` failure model.
export type FailureType =
  | "mcar"
  | "mar"
  | "mnar"
  | "label_noise"
  | "feature_noise"
  | "drift"
  | "covariate_shift"
  | "leakage";

export interface DriftSchedule {
  kind?: "linear" | "step";
  magnitude?: number;
  rate?: number;
  at?: number;
}
export interface ShiftTarget {
  mean?: number;
  std?: number;
}
export interface Failure {
  type: FailureType;
  column?: string;
  columns?: string[];
  rate?: number;
  driver?: string;
  strength?: number;
  dist?: string;
  params?: Record<string, number>;
  schedule?: DriftSchedule;
  // `target` is a moment spec for covariate_shift, but a column name for leakage
  // (the engine keys both on `target`).
  target?: ShiftTarget | string;
  into?: string;
  noise?: number;
}

export type DifficultyTier = "beginner" | "intermediate" | "advanced" | "kaggle";
export type DifficultyProbe = "logreg" | "tree";
export type DifficultyKnob = "noise" | "label_noise";

export interface DifficultyBand {
  task?: string;
  metric?: string;
  band: [number, number];
}
export interface Difficulty {
  target: DifficultyTier | DifficultyBand;
  label: string;
  probe: DifficultyProbe;
  max_iters: number;
  knobs: DifficultyKnob[];
}

export interface Spec {
  datadoom_version: string;
  name: string;
  description?: string | null;
  seed?: number | null;
  rows: number;
  features: Record<string, Feature>;
  causal?: CausalGraph | null;
  difficulty?: Difficulty | null;
  failures?: Failure[];
  export?: { formats?: string[]; versions?: string[]; [k: string]: unknown } | null;
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
  spec_hash?: string | null;
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
  version: string; // clean | injected | spec | audit
  split?: string | null;
  format: string;
  filename: string; // authoritative on-disk name (data.csv, data.injected.csv, …)
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
  p_value: number; // p-value of the decisive test (KS or chi-square GoF)
  passed: boolean | null; // null only when no valid test could be formed (abstain)
  clamped_fraction: number;
  applicable?: boolean;
  note?: string | null;
  // Which test decided pass/fail: "ks" (continuous), "chi2_gof" (int/discrete/
  // clamped — judged against the effective PMF), or "none" (abstained).
  test?: "ks" | "chi2_gof" | "none";
  gof?: { statistic: number; dof: number; bins: number; p_value: number } | null;
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

// One entry per injected failure, carrying the realized (authoritative) effect
// the engine measured. Fields beyond the common ones vary by mechanism.
export interface FailureDiff {
  index: number;
  type: FailureType;
  mechanism?: string;
  column?: string;
  driver?: string;
  rate?: number;
  target_rate?: number;
  realized_rate?: number;
  nullified_fraction?: Record<string, number>;
  flipped_fraction?: number;
  realized_noise_std?: number;
  realized_mean_shift?: number;
  total_shift?: number;
  mean_shift_second_vs_first_half?: number;
  before?: { mean: number; std: number };
  after?: { mean: number; std: number };
  target?: string;
  into?: string;
  realized_correlation?: number | null;
  self_dependent?: boolean;
  [k: string]: unknown;
}
export interface FailuresReport {
  count: number;
  modes: FailureDiff[];
}

export interface DifficultyReport {
  target: { tier: string | null; task: string; metric: string; band: [number, number] };
  achieved_metric: number;
  metric_name: string;
  probe: string;
  iterations: number;
  band_met: boolean;
  dial: number;
  feature_noise: number;
  label_flip: number;
  knobs_requested: string[];
  knobs_active: string[];
  reference: {
    linear_separability: number;
    class_balance: number;
    noise_to_signal: number;
    probe_features: number;
    rows: number;
  };
  trace: { dial: number; metric: number }[];
  note: string | null;
}

// Per-column data profile (the "Column Guide" — EDA made simple). The engine knows
// the ground truth of every column, so each carries its stats plus the issues it
// has (failure modes that hit it, class imbalance) with ML-handling advice.
export type IssueSeverity = "critical" | "high" | "medium" | "low";

export interface ColumnIssue {
  mode: string; // failure mechanism or "class_imbalance"
  title: string;
  severity: IssueSeverity;
  magnitude: string; // realized effect, human-readable
  explanation: string;
  recommendation: string;
  techniques: string[];
  detail: Record<string, unknown>;
}

export interface ColumnCategory {
  value: string;
  count: number;
  pct: number;
}

export interface ColumnProfile {
  name: string;
  role: "feature" | "label" | "derived" | "leakage_proxy";
  feature_type: string;
  dtype: string;
  count: number;
  missing: number;
  missing_pct: number;
  unique: number;
  derived: boolean;
  parents: string[];
  description?: string | null;
  stats?: {
    mean: number | null;
    std: number | null;
    min: number | null;
    p25: number | null;
    median: number | null;
    p75: number | null;
    max: number | null;
    skew: number | null;
  } | null;
  categories?: ColumnCategory[] | null;
  imbalance?: { classes: number; majority_pct: number; minority_pct: number; ratio: number | null } | null;
  injected?: { missing_pct: number; mean?: number | null; std?: number | null } | null;
  issues: ColumnIssue[];
}

export interface ProfileReport {
  summary: {
    n_rows: number;
    n_columns: number;
    label: string | null;
    columns_with_issues: number;
    total_issues: number;
    critical_issues: number;
    high_issues: number;
  };
  columns: ColumnProfile[];
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
  difficulty?: DifficultyReport | null;
  failures?: FailuresReport | null;
  profile?: ProfileReport | null;
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

// Built-in domain templates (08 §10, 09 §4.6).
export interface TemplateSummary {
  id: string;
  name: string;
  domain: string;
  description: string;
  tags: string[];
  level: "starter" | "hackathon";
}

export interface TemplateDetail extends TemplateSummary {
  spec: Spec;
}

// Plugin registry (09, 08 §10) — core built-ins + discovered plugins.
export type PluginKind =
  | "distribution"
  | "structural_fn"
  | "failure_mode"
  | "exporter"
  | "probe_model";

export interface JsonSchemaProperty {
  type?: string;
  title?: string;
  description?: string;
  minimum?: number;
  maximum?: number;
  enum?: (string | number)[];
  default?: unknown;
}

export interface JsonSchemaFragment {
  type?: string;
  properties?: Record<string, JsonSchemaProperty>;
  required?: string[];
}

export interface PluginInfo {
  name: string;
  kind: PluginKind | string;
  version: string | null;
  schema: JsonSchemaFragment | null;
  source: "builtin" | "entrypoint" | "local";
  builtin: boolean;
  enabled: boolean;
}

// WebSocket progress events (08 §7).
export type RunEvent =
  | { type: "stage"; stage: string; status: "running" | "done"; pct: number }
  | { type: "log"; level: string; message: string }
  | { type: "completed"; run_id: string; compliance_score: number; report_id: string }
  | { type: "failed"; stage: string; message: string; traceback?: string }
  | { type: "cancelled"; run_id: string };
