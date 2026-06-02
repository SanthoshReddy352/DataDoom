import type { CausalEdge, CausalGraph, Feature, Spec } from "./types";

// Structural functions and the params each one carries (mirrors engine/causal).
export const STRUCTURAL_FNS = ["linear", "logistic", "polynomial", "map", "identity"] as const;
export type StructuralFn = (typeof STRUCTURAL_FNS)[number];

export const NOISE_DISTS = ["none", "normal", "lognormal", "uniform", "exponential"] as const;

export function emptyCausal(): CausalGraph {
  return { edges: [], noise: {}, interventions: [] };
}

export function getCausal(spec: Spec): CausalGraph {
  return spec.causal ?? emptyCausal();
}

/** Feature names that are causal targets (have ≥1 incoming edge). */
export function derivedNames(causal: CausalGraph | null | undefined): Set<string> {
  return new Set((causal?.edges ?? []).map((e) => e.to));
}

/** Incoming edges for a node, in author order. */
export function inEdges(causal: CausalGraph, node: string): CausalEdge[] {
  return causal.edges.filter((e) => e.to === node);
}

/** A default edge for a freshly-drawn connection, based on the parent type. */
export function defaultEdge(from: string, to: string, parent: Feature): CausalEdge {
  if (parent.type === "categorical") {
    const mapping: Record<string, number> = {};
    (parent.categories ?? []).forEach((c, i) => (mapping[c] = i));
    return { from, to, fn: "map", mapping };
  }
  return { from, to, fn: "linear", weight: 1, bias: 0 };
}

/** Would adding edge from→to create a cycle (or a self-loop)? */
export function wouldCycle(edges: CausalEdge[], from: string, to: string): boolean {
  if (from === to) return true;
  // Does `from` already reach... is `to` an ancestor of `from`? i.e. can we get
  // from `to` back to `from` following existing edges? If so, adding from→to closes a loop.
  const adj = new Map<string, string[]>();
  for (const e of edges) {
    if (!adj.has(e.from)) adj.set(e.from, []);
    adj.get(e.from)!.push(e.to);
  }
  const stack = [to];
  const seen = new Set<string>();
  while (stack.length) {
    const n = stack.pop()!;
    if (n === from) return true;
    if (seen.has(n)) continue;
    seen.add(n);
    for (const c of adj.get(n) ?? []) stack.push(c);
  }
  return false;
}

/**
 * Longest-path topological layering: layer(node) = max(layer(parents)) + 1.
 * Returns a layer index per feature (roots = 0). Assumes acyclic.
 */
export function topoLayers(featureNames: string[], edges: CausalEdge[]): Record<string, number> {
  const parents = new Map<string, string[]>();
  featureNames.forEach((n) => parents.set(n, []));
  for (const e of edges) parents.get(e.to)?.push(e.from);

  const layer: Record<string, number> = {};
  const visiting = new Set<string>();
  const compute = (n: string): number => {
    if (layer[n] !== undefined) return layer[n];
    if (visiting.has(n)) return 0; // cycle guard (validation rejects these)
    visiting.add(n);
    const ps = parents.get(n) ?? [];
    const l = ps.length ? Math.max(...ps.map(compute)) + 1 : 0;
    visiting.delete(n);
    layer[n] = l;
    return l;
  };
  featureNames.forEach(compute);
  return layer;
}

/** Whether a structural fn can consume a given parent feature type. */
export function fnAcceptsParent(fn: string, parent: Feature | undefined): boolean {
  if (!parent) return true;
  if (fn === "map") return parent.type === "categorical";
  return parent.type === "numeric" || parent.type === "boolean";
}

/**
 * Keep a spec valid as edges change: a numeric feature that becomes a causal
 * target must shed its `dist` (it is now derived); one that loses its last
 * incoming edge gets a default distribution back so it stays samplable.
 */
export function reconcileDerived(spec: Spec, causal: CausalGraph): Spec {
  const targets = derivedNames(causal);
  const features = { ...spec.features };
  for (const [name, feat] of Object.entries(features)) {
    if (feat.type !== "numeric") continue;
    const isTarget = targets.has(name);
    const hasDist = feat.dist != null;
    if (isTarget && hasDist) {
      const { dist: _d, params: _p, ...rest } = feat;
      features[name] = { ...rest, type: "numeric" };
    } else if (!isTarget && !hasDist) {
      features[name] = { ...feat, dist: "normal", params: { mean: 0, std: 1 } };
    }
  }
  return { ...spec, features, causal };
}

export function interventionMap(causal: CausalGraph | null | undefined): Record<string, number> {
  const out: Record<string, number> = {};
  for (const iv of causal?.interventions ?? []) {
    for (const [k, v] of Object.entries(iv.do ?? {})) out[k] = v;
  }
  return out;
}

export function setIntervention(causal: CausalGraph, node: string, value: number | null): CausalGraph {
  const map = interventionMap(causal);
  if (value === null) delete map[node];
  else map[node] = value;
  const interventions = Object.entries(map).map(([k, v]) => ({ do: { [k]: v } }));
  return { ...causal, interventions };
}
