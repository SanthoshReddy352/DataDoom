import type { CausalEdge, CausalGraph, Feature } from "./types";
import { inEdges, interventionMap } from "./causal";

export interface SettingRow {
  label: string;
  value: string;
  tone?: "default" | "accent" | "muted";
}

const num = (n: number | null | undefined): string =>
  n == null || Number.isNaN(n) ? "—" : Number.isInteger(n) ? String(n) : n.toFixed(2);

/** Every distribution/shape setting carried by a single feature, for display. */
export function featureSettings(feature: Feature): SettingRow[] {
  switch (feature.type) {
    case "numeric": {
      const rows: SettingRow[] = [];
      if (feature.dist) {
        rows.push({ label: "dist", value: feature.dist, tone: "accent" });
        const params = feature.params ?? {};
        for (const [k, v] of Object.entries(params)) rows.push({ label: k, value: num(v) });
      } else {
        rows.push({ label: "value", value: "derived (causal)", tone: "muted" });
      }
      if (feature.min != null || feature.max != null) {
        rows.push({
          label: "clamp",
          value: `${feature.min != null ? num(feature.min) : "−∞"} … ${feature.max != null ? num(feature.max) : "∞"}`,
        });
      }
      rows.push({ label: "dtype", value: feature.dtype ?? "float" });
      return rows;
    }
    case "categorical": {
      const cats = feature.categories ?? [];
      const weights = feature.weights ?? cats.map(() => 1);
      const total = weights.reduce((a, b) => a + b, 0) || 1;
      const rows: SettingRow[] = [{ label: "levels", value: String(cats.length), tone: "accent" }];
      cats.slice(0, 6).forEach((c, i) => {
        rows.push({ label: c, value: `${Math.round(((weights[i] ?? 1) / total) * 100)}%` });
      });
      if (cats.length > 6) rows.push({ label: "…", value: `+${cats.length - 6} more`, tone: "muted" });
      return rows;
    }
    case "boolean":
      return [{ label: "P(true)", value: (feature.rate ?? 0.5).toFixed(2), tone: "accent" }];
    case "datetime":
      return [
        { label: "from", value: feature.start ?? "—" },
        { label: "to", value: feature.end ?? "—" },
        { label: "grain", value: feature.granularity ?? "day" },
      ];
    case "text":
      return [
        { label: "generator", value: feature.generator ?? "lorem", tone: "accent" },
        { label: "length", value: `${feature.length?.min ?? 5}–${feature.length?.max ?? 30}` },
      ];
    default:
      return [];
  }
}

/** A compact, human-readable label for a structural function on an edge. */
export function edgeFnLabel(edge: Pick<CausalEdge, "fn" | "weight" | "bias" | "coeffs" | "mapping">): string {
  switch (edge.fn) {
    case "linear":
      return `linear · w=${num(edge.weight)}${edge.bias ? ` b=${num(edge.bias)}` : ""}`;
    case "logistic":
      return `logistic · w=${num(edge.weight)}${edge.bias ? ` b=${num(edge.bias)}` : ""}`;
    case "polynomial":
      return `poly · deg ${(edge.coeffs?.length ?? 1) - 1}`;
    case "map": {
      const entries = Object.entries(edge.mapping ?? {});
      const preview = entries.slice(0, 2).map(([k, v]) => `${k}→${num(v)}`).join(" ");
      return `map · ${preview}${entries.length > 2 ? " …" : ""}`;
    }
    case "identity":
      return "identity";
    default:
      return edge.fn;
  }
}

export interface NodeDerivation {
  derived: boolean;
  incoming: CausalEdge[];
  noise?: { dist: string; params?: Record<string, number> };
  intervenedValue?: number;
}

/** Causal facts about a node: its parents/edges, noise term, and any do() value. */
export function nodeDerivation(causal: CausalGraph, name: string): NodeDerivation {
  const incoming = inEdges(causal, name);
  const noise = causal.noise?.[name];
  const iv = interventionMap(causal);
  return {
    derived: incoming.length > 0,
    incoming,
    noise: noise && noise.dist !== "none" ? noise : undefined,
    intervenedValue: name in iv ? iv[name] : undefined,
  };
}

/** Causal settings as display rows (parents, structural fns, noise, do()). */
export function causalSettings(causal: CausalGraph, name: string): SettingRow[] {
  const d = nodeDerivation(causal, name);
  const rows: SettingRow[] = [];
  for (const e of d.incoming) {
    rows.push({ label: `← ${e.from}`, value: edgeFnLabel(e), tone: "accent" });
  }
  if (d.noise) {
    const ps = d.noise.params
      ? Object.entries(d.noise.params).map(([k, v]) => `${k}=${num(v)}`).join(" ")
      : "";
    rows.push({ label: "noise ε", value: `${d.noise.dist} ${ps}`.trim() });
  }
  if (d.intervenedValue !== undefined) {
    rows.push({ label: "do()", value: `= ${num(d.intervenedValue)}`, tone: "accent" });
  }
  return rows;
}
