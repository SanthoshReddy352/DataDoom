import type { Feature, Spec } from "./types";

export function slugify(name: string): string {
  return name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60) || "dataset";
}

export function starterFeature(): Feature {
  return { type: "numeric", dist: "normal", params: { mean: 0, std: 1 }, dtype: "float" };
}

export function starterSpec(name: string, rows: number, seed?: number): Spec {
  return {
    datadoom_version: "1",
    name: slugify(name),
    rows,
    ...(seed != null ? { seed } : {}),
    features: { feature_1: starterFeature() },
  };
}

// Default parameter sets when switching a numeric feature's distribution.
export const DIST_PARAMS: Record<string, Record<string, number>> = {
  normal: { mean: 0, std: 1 },
  lognormal: { mu: 0, sigma: 1 },
  poisson: { lam: 3 },
  pareto: { alpha: 3, xm: 1 },
  uniform: { low: 0, high: 1 },
  exponential: { scale: 1 },
};

export const NUMERIC_DISTS = Object.keys(DIST_PARAMS);
