// Failure-mode metadata + client helpers (mirrors the engine's `engine/failure`).
// Pure data/logic, no JSX — the configurator/inspector map these to controls.
// Impact estimates here are *declarative consequences of the knobs* (e.g. an
// MCAR rate → expected missing count, a leakage noise → corr = 1/√(1+η²)); they
// are NOT a re-simulation of the engine. The authoritative realized effect comes
// back in the run's report (the Comparison view).

import type { Failure, FailureType, Feature, Spec } from "./types";

export type FailureCategory = "Missingness" | "Noise" | "Shift" | "Leakage";

export interface FailureMeta {
  type: FailureType;
  label: string;
  category: FailureCategory;
  /** One-line plain-language description of the mechanism. */
  blurb: string;
  /** The honest math, shown in the inspector. */
  math: string;
  /** CSS color var for accents/badges. */
  accent: string;
}

export const FAILURE_META: Record<FailureType, FailureMeta> = {
  mcar: {
    type: "mcar",
    label: "Missing completely at random",
    category: "Missingness",
    blurb: "Blank out cells at random, independent of the data.",
    math: "mᵢ ~ Bernoulli(rate); value set to NaN where mᵢ = 1.",
    accent: "var(--info)",
  },
  mar: {
    type: "mar",
    label: "Missing at random",
    category: "Missingness",
    blurb: "Missingness depends on another observed column.",
    math: "P(missing | driver) = σ(a + strength·z(driver)); the intercept a is calibrated so the expected rate matches.",
    accent: "var(--info)",
  },
  mnar: {
    type: "mnar",
    label: "Missing not at random",
    category: "Missingness",
    blurb: "Missingness depends on the value itself (or a hidden driver).",
    math: "P(missing | X) = σ(a + strength·z(X)); higher |value| ⇒ more likely missing.",
    accent: "var(--info)",
  },
  label_noise: {
    type: "label_noise",
    label: "Label noise",
    category: "Noise",
    blurb: "Flip booleans / reassign categories to a different class.",
    math: "With probability rate: boolean flips; categorical is reassigned uniformly to one of the other classes.",
    accent: "var(--warning)",
  },
  feature_noise: {
    type: "feature_noise",
    label: "Feature noise",
    category: "Noise",
    blurb: "Add measurement jitter to a numeric column.",
    math: "x' = x + ε, ε ~ dist(params). Independent of x.",
    accent: "var(--warning)",
  },
  drift: {
    type: "drift",
    label: "Concept drift",
    category: "Shift",
    blurb: "A column's values ramp over the row index.",
    math: "x'[i] = x[i] + magnitude·g(i); g linear i/(n-1) ∈ [0,1] or a step.",
    accent: "var(--primary)",
  },
  covariate_shift: {
    type: "covariate_shift",
    label: "Covariate shift",
    category: "Shift",
    blurb: "Move a column's distribution toward target moments.",
    math: "Affine x' = (x-μ)(σₜ/σ) + μₜ — hits the target mean/std exactly while preserving shape.",
    accent: "var(--primary)",
  },
  leakage: {
    type: "leakage",
    label: "Target leakage",
    category: "Leakage",
    blurb: "Plant a near-perfect proxy column for the label.",
    math: "into = target + N(0, noise·σ); corr(into, target) = 1/√(1+noise²).",
    accent: "var(--hazard)",
  },
};

export const FAILURE_ORDER: FailureType[] = [
  "mcar",
  "mar",
  "mnar",
  "label_noise",
  "feature_noise",
  "drift",
  "covariate_shift",
  "leakage",
];

export const CATEGORY_ORDER: FailureCategory[] = ["Missingness", "Noise", "Shift", "Leakage"];

// --- column-kind helpers ------------------------------------------------------

export interface ColumnKinds {
  all: string[];
  numeric: string[];
  /** float-coercible — valid MAR/MNAR driver & leakage target. */
  numericOrBool: string[];
  /** boolean or categorical — valid label_noise target. */
  labelable: string[];
}

export function columnKinds(spec: Spec): ColumnKinds {
  const entries = Object.entries(spec.features) as [string, Feature][];
  return {
    all: entries.map(([n]) => n),
    numeric: entries.filter(([, f]) => f.type === "numeric").map(([n]) => n),
    numericOrBool: entries
      .filter(([, f]) => f.type === "numeric" || f.type === "boolean")
      .map(([n]) => n),
    labelable: entries
      .filter(([, f]) => f.type === "boolean" || f.type === "categorical")
      .map(([n]) => n),
  };
}

// --- defaults -----------------------------------------------------------------

/** A sensible new failure of `type`, wired to a compatible column when one exists. */
export function defaultFailure(type: FailureType, spec: Spec): Failure {
  const k = columnKinds(spec);
  const first = (xs: string[]) => xs[0] ?? "";
  switch (type) {
    case "mcar":
      return { type, columns: k.all.length ? [first(k.all)] : [], rate: 0.05 };
    case "mar":
      return { type, column: first(k.all), driver: first(k.numericOrBool), rate: 0.15, strength: 2 };
    case "mnar":
      return { type, column: first(k.numericOrBool), rate: 0.15, strength: 2 };
    case "label_noise":
      return { type, column: first(k.labelable), rate: 0.05 };
    case "feature_noise":
      return { type, column: first(k.numeric), dist: "normal", params: { mean: 0, std: 1 } };
    case "drift":
      return { type, column: first(k.numeric), schedule: { kind: "linear", magnitude: 1 } };
    case "covariate_shift":
      return { type, column: first(k.numeric), target: { mean: 0 } };
    case "leakage":
      return { type, target: first(k.numericOrBool), into: uniqueLeakName(spec), noise: 0.05 };
  }
}

function uniqueLeakName(spec: Spec): string {
  const taken = new Set(Object.keys(spec.features));
  for (const f of spec.failures ?? []) if (f.type === "leakage" && f.into) taken.add(f.into);
  let name = "leak";
  let i = 1;
  while (taken.has(name)) name = `leak_${++i}`;
  return name;
}

// `target` is overloaded: a moment spec for covariate_shift, a column name for
// leakage. These narrow it safely.
export function leakTarget(f: Failure): string {
  return typeof f.target === "string" ? f.target : "";
}
export function shiftTarget(f: Failure): { mean?: number; std?: number } {
  return f.target && typeof f.target === "object" ? f.target : {};
}

// --- summaries & impact -------------------------------------------------------

function pct(x: number | undefined): string {
  return `${Math.round((x ?? 0) * 100)}%`;
}
function num(x: number | undefined): string {
  if (x == null || !Number.isFinite(x)) return "—";
  return Number.isInteger(x) ? String(x) : x.toFixed(2);
}

/** Short header summary, e.g. "income · 12%". */
export function summarizeFailure(f: Failure): string {
  switch (f.type) {
    case "mcar":
      return `${(f.columns ?? []).join(", ") || "—"} · ${pct(f.rate)}`;
    case "mar":
      return `${f.column || "—"} · ${pct(f.rate)} ← ${f.driver || "?"}`;
    case "mnar":
      return `${f.column || "—"} · ${pct(f.rate)} self`;
    case "label_noise":
      return `${f.column || "—"} · ${pct(f.rate)}`;
    case "feature_noise":
      return `${f.column || "—"} · +${f.dist ?? "noise"}`;
    case "drift":
      return `${f.column || "—"} · ${f.schedule?.kind ?? "linear"} ${num(driftMagnitude(f))}`;
    case "covariate_shift":
      return `${f.column || "—"} → μ ${num(shiftTarget(f).mean)}`;
    case "leakage":
      return `${f.into || "leak"} ≈ ${leakTarget(f) || "?"}`;
  }
}

export function driftMagnitude(f: Failure): number {
  const s = f.schedule ?? {};
  if (s.magnitude != null) return s.magnitude;
  if (s.rate != null) return s.rate; // per-row slope; total depends on rows
  return 0;
}

export interface Impact {
  /** The headline consequence sentence. */
  line: string;
  /** Optional quantified chip, e.g. "≈600 rows". */
  metric?: string;
}

/** Declarative, honest estimate of a failure's effect for the given row count. */
export function impactEstimate(f: Failure, rows: number): Impact {
  switch (f.type) {
    case "mcar": {
      const cols = (f.columns ?? []).length;
      return {
        line: `Blank ≈${pct(f.rate)} of ${cols || "—"} column${cols === 1 ? "" : "s"}, at random.`,
        metric: `≈${Math.round((f.rate ?? 0) * rows).toLocaleString()} cells/col`,
      };
    }
    case "mar":
      return {
        line: `≈${pct(f.rate)} of ${f.column || "—"} goes missing, more often when ${f.driver || "the driver"} is high.`,
        metric: `≈${Math.round((f.rate ?? 0) * rows).toLocaleString()} rows`,
      };
    case "mnar":
      return {
        line: `≈${pct(f.rate)} of ${f.column || "—"} goes missing, biased toward its own extreme values.`,
        metric: `≈${Math.round((f.rate ?? 0) * rows).toLocaleString()} rows`,
      };
    case "label_noise":
      return {
        line: `Flip ≈${pct(f.rate)} of ${f.column || "—"} labels to a different class.`,
        metric: `≈${Math.round((f.rate ?? 0) * rows).toLocaleString()} rows`,
      };
    case "feature_noise":
      return {
        line: `Add ${f.dist ?? "noise"}(${Object.entries(f.params ?? {})
          .map(([k, v]) => `${k}=${num(v)}`)
          .join(", ")}) jitter to ${f.column || "—"}.`,
      };
    case "drift": {
      const m = driftMagnitude(f);
      const total = f.schedule?.magnitude != null ? m : m * Math.max(0, rows - 1);
      return {
        line: `${f.column || "—"} ramps by up to ${num(total)} across the dataset (${f.schedule?.kind ?? "linear"}).`,
        metric: `Δ ${num(total)}`,
      };
    }
    case "covariate_shift": {
      const t = shiftTarget(f);
      return {
        line: `Shift ${f.column || "—"} to mean ${num(t.mean)}${
          t.std != null ? `, std ${num(t.std)}` : ""
        } (exact moment-match).`,
      };
    }
    case "leakage": {
      const eta = f.noise ?? 0.05;
      const corr = 1 / Math.sqrt(1 + eta * eta);
      return {
        line: `Plant "${f.into || "leak"}" as a proxy of ${leakTarget(f) || "—"}.`,
        metric: `corr ≈ ${corr.toFixed(3)}`,
      };
    }
  }
}

export interface ColumnFailureChip {
  type: FailureType;
  text: string;
  /** True when the column is only *referenced* (driver/leak source), not corrupted. */
  secondary?: boolean;
}

/** Failures that involve a given column, for badges in the Table/Graph views. */
export function columnFailureChips(
  failures: Failure[] | undefined,
  name: string,
): ColumnFailureChip[] {
  const out: ColumnFailureChip[] = [];
  for (const f of failures ?? []) {
    switch (f.type) {
      case "mcar":
        if ((f.columns ?? []).includes(name)) out.push({ type: f.type, text: `${pct(f.rate)} missing` });
        break;
      case "mar":
        if (f.column === name) out.push({ type: f.type, text: `${pct(f.rate)} missing ← ${f.driver ?? "?"}` });
        else if (f.driver === name)
          out.push({ type: f.type, text: `drives ${f.column ?? "?"} missingness`, secondary: true });
        break;
      case "mnar":
        if (f.column === name) out.push({ type: f.type, text: `${pct(f.rate)} missing (self)` });
        break;
      case "label_noise":
        if (f.column === name) out.push({ type: f.type, text: `${pct(f.rate)} flipped` });
        break;
      case "feature_noise":
        if (f.column === name) out.push({ type: f.type, text: `+${f.dist ?? "noise"} noise` });
        break;
      case "drift":
        if (f.column === name) out.push({ type: f.type, text: `drift ${num(driftMagnitude(f))}` });
        break;
      case "covariate_shift":
        if (f.column === name) out.push({ type: f.type, text: `shift → μ ${num(shiftTarget(f).mean)}` });
        break;
      case "leakage":
        if (leakTarget(f) === name)
          out.push({ type: f.type, text: `→ ${f.into ?? "leak"} (proxy)`, secondary: true });
        break;
    }
  }
  return out;
}

/** Columns a failure reads/writes — used to highlight the Comparison diff. */
export function failureTouchedColumns(f: Failure): string[] {
  switch (f.type) {
    case "mcar":
      return f.columns ?? [];
    case "mar":
    case "mnar":
    case "label_noise":
    case "feature_noise":
    case "drift":
    case "covariate_shift":
      return f.column ? [f.column] : [];
    case "leakage":
      return f.into ? [f.into] : [];
  }
}

// --- client-side pre-flight validation ---------------------------------------

/** Inline pre-flight check (the server is authoritative). Returns a message or null. */
export function validateFailureClient(f: Failure, spec: Spec): string | null {
  const k = columnKinds(spec);
  const inRange = (r?: number) => r != null && r >= 0 && r <= 1;
  const has = (n?: string, list?: string[]) => !!n && (list ?? k.all).includes(n);
  switch (f.type) {
    case "mcar":
      if (!f.columns?.length) return "Pick at least one column to blank out.";
      if (f.columns.some((c) => !k.all.includes(c))) return "A selected column no longer exists.";
      if (!inRange(f.rate)) return "Rate must be between 0 and 1.";
      return null;
    case "mar":
      if (!has(f.column)) return "Pick the column to make missing.";
      if (!has(f.driver, k.numericOrBool)) return "Pick a numeric or boolean driver.";
      if (!inRange(f.rate)) return "Rate must be between 0 and 1.";
      return null;
    case "mnar":
      if (!has(f.column, k.numericOrBool)) return "Pick a numeric or boolean column (it drives its own missingness).";
      if (f.driver && !has(f.driver, k.numericOrBool)) return "Driver must be numeric or boolean.";
      if (!inRange(f.rate)) return "Rate must be between 0 and 1.";
      return null;
    case "label_noise":
      if (!has(f.column, k.labelable)) return "Pick a boolean or categorical column.";
      if (!inRange(f.rate)) return "Rate must be between 0 and 1.";
      return null;
    case "feature_noise":
      if (!has(f.column, k.numeric)) return "Pick a numeric column.";
      if (!f.dist) return "Pick a noise distribution.";
      return null;
    case "drift":
      if (!has(f.column, k.numeric)) return "Pick a numeric column.";
      return null;
    case "covariate_shift": {
      if (!has(f.column, k.numeric)) return "Pick a numeric column.";
      const t = shiftTarget(f);
      if (t.mean == null && t.std == null) return "Set a target mean and/or std.";
      return null;
    }
    case "leakage": {
      const tgt = leakTarget(f);
      if (!has(tgt, k.numericOrBool)) return "Pick a numeric or boolean target to leak.";
      if (!f.into?.trim()) return "Name the planted proxy column.";
      if (f.into === tgt) return "The proxy must differ from the target.";
      return null;
    }
  }
}

// --- reconciliation on column rename / delete --------------------------------

/** Rewrite failure column references when a feature is renamed or removed.
 * Failures whose essential column was removed are dropped (so generation can't
 * fail on a dangling reference). */
export function reconcileFailures(
  failures: Failure[] | undefined,
  change: { rename?: { from: string; to: string }; remove?: string },
): Failure[] {
  if (!failures?.length) return failures ?? [];
  const map = (n?: string): string | undefined => {
    if (n == null) return n;
    return change.rename && n === change.rename.from ? change.rename.to : n;
  };

  return failures
    .map((f) => {
      const next: Failure = { ...f };
      if (next.columns) {
        next.columns = next.columns.map((c) => map(c)!).filter((c) => c !== change.remove);
      }
      next.column = map(next.column);
      next.driver = map(next.driver);
      // leakage stores the label column on `target` as a string.
      if (typeof next.target === "string") next.target = map(next.target);
      return next;
    })
    .filter((f) => !essentialRefRemoved(f, change.remove));
}

function essentialRefRemoved(f: Failure, removed?: string): boolean {
  if (removed == null) return false;
  switch (f.type) {
    case "mcar":
      return (f.columns ?? []).length === 0;
    case "mar":
      return f.column === removed || f.driver === removed;
    case "mnar":
    case "label_noise":
    case "feature_noise":
    case "drift":
    case "covariate_shift":
      return f.column === removed;
    case "leakage":
      return leakTarget(f) === removed;
  }
}
