// Difficulty-targeting metadata + helpers for the Canvas configurator and the
// Results report (mirrors engine/difficulty). Difficulty is an *empirical*
// target: a dataset is "as hard as" the AUROC a baseline probe achieves on it.

import type {
  Difficulty,
  DifficultyBand,
  DifficultyKnob,
  DifficultyTier,
  Feature,
  Spec,
} from "./types";

export interface TierMeta {
  tier: DifficultyTier;
  label: string;
  band: [number, number];
  blurb: string;
}

// Bands mirror engine/difficulty/calibrate.py TIER_BANDS (05 §5.3).
export const TIERS: TierMeta[] = [
  { tier: "beginner", label: "Beginner", band: [0.9, 0.99], blurb: "Almost separable — a baseline aces it." },
  { tier: "intermediate", label: "Intermediate", band: [0.8, 0.9], blurb: "Clear signal with real overlap." },
  { tier: "advanced", label: "Advanced", band: [0.72, 0.8], blurb: "Hard — strong probes only edge ahead." },
  { tier: "kaggle", label: "Kaggle", band: [0.62, 0.72], blurb: "Brutal — near the noise floor." },
];

export const TIER_BY_NAME: Record<string, TierMeta> = Object.fromEntries(
  TIERS.map((t) => [t.tier, t]),
);

export const PROBES: { value: "logreg" | "tree"; label: string; blurb: string }[] = [
  { value: "logreg", label: "Logistic regression", blurb: "Linear baseline — the default." },
  { value: "tree", label: "Decision tree", blurb: "Captures simple non-linear splits." },
];

export const KNOB_META: Record<DifficultyKnob, { label: string; blurb: string }> = {
  noise: {
    label: "Feature noise",
    blurb: "Adds Gaussian observation noise to numeric predictors. Primary lever; leaves the causal graph intact.",
  },
  label_noise: {
    label: "Label flips",
    blurb: "Flips a fraction of the label. Deep-end lever, engaged only when feature noise saturates.",
  },
};

export const ALL_KNOBS: DifficultyKnob[] = ["noise", "label_noise"];

/** A feature usable as a binary-classification label (boolean or 2-class categorical). */
export function isLabelable(feat: Feature): boolean {
  if (feat.emit === false) return false; // latent — not shipped, can't be the label
  return feat.type === "boolean" || (feat.type === "categorical" && feat.categories.length === 2);
}

export function labelableColumns(spec: Spec): string[] {
  return Object.entries(spec.features)
    .filter(([, f]) => isLabelable(f))
    .map(([name]) => name);
}

export function isTier(target: Difficulty["target"]): target is DifficultyTier {
  return typeof target === "string";
}

export function bandOf(target: Difficulty["target"]): [number, number] {
  return isTier(target) ? TIER_BY_NAME[target].band : (target as DifficultyBand).band;
}

/** A sensible default difficulty block for a spec, or null if no binary label exists. */
export function defaultDifficulty(spec: Spec): Difficulty | null {
  const labels = labelableColumns(spec);
  if (labels.length === 0) return null;
  return {
    target: "advanced",
    label: labels[0],
    probe: "logreg",
    max_iters: 8,
    knobs: [...ALL_KNOBS],
  };
}

export function summarizeDifficulty(d: Difficulty): string {
  const [a, b] = bandOf(d.target);
  const name = isTier(d.target) ? TIER_BY_NAME[d.target].label : "custom";
  return `${name} · AUROC ${a.toFixed(2)}–${b.toFixed(2)} on ${d.label} (${d.probe})`;
}

/** Client pre-flight validation mirroring engine/spec/validate._check_difficulty. */
export function validateDifficultyClient(d: Difficulty, spec: Spec): string | null {
  const feat = spec.features[d.label];
  if (!feat) return `Label "${d.label}" is not a column.`;
  if (!isLabelable(feat)) {
    return `Label "${d.label}" must be boolean or a 2-class categorical (binary classification).`;
  }
  if (!isTier(d.target)) {
    const [a, b] = d.target.band;
    if (!(a >= 0 && a <= b && b <= 1)) return "Custom band must satisfy 0 ≤ low ≤ high ≤ 1.";
  }
  if (d.knobs.length === 0) return "Enable at least one knob so the loop can adjust difficulty.";
  return null;
}
