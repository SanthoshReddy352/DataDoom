import { Plus, Trash2, X } from "lucide-react";
import { Kicker, TypeChip } from "./ui";
import {
  NOISE_DISTS,
  STRUCTURAL_FNS,
  fnAcceptsParent,
  inEdges,
  interventionMap,
  setIntervention,
} from "@/lib/causal";
import { DIST_PARAMS } from "@/lib/specDefaults";
import type { CausalEdge, CausalGraph, Spec } from "@/lib/types";

export type CausalSelection =
  | { kind: "edge"; index: number }
  | { kind: "node"; name: string }
  | null;

export function CausalInspector({
  spec,
  causal,
  selection,
  onCausalChange,
  onSelect,
}: {
  spec: Spec;
  causal: CausalGraph;
  selection: CausalSelection;
  onCausalChange: (next: CausalGraph) => void;
  onSelect: (sel: CausalSelection) => void;
}) {
  if (!selection) {
    return (
      <div className="p-6 text-sm text-text-faint">
        <Kicker>Causal inspector</Kicker>
        <p className="mt-3 text-text-muted">
          Drag from one column's handle to another to add a dependency. Click an edge to choose its
          structural function, or click a node to add noise or an intervention.
        </p>
      </div>
    );
  }
  if (selection.kind === "edge") {
    return (
      <EdgeEditor
        spec={spec}
        causal={causal}
        index={selection.index}
        onCausalChange={onCausalChange}
        onSelect={onSelect}
      />
    );
  }
  return <NodeEditor spec={spec} causal={causal} name={selection.name} onCausalChange={onCausalChange} />;
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="mb-3 block">
      <span className="text-xs font-medium text-text-muted">{label}</span>
      {children}
    </label>
  );
}

function NumInput({
  value,
  onChange,
  placeholder,
}: {
  value: number | undefined;
  onChange: (n: number) => void;
  placeholder?: string;
}) {
  return (
    <input
      type="number"
      value={value ?? ""}
      placeholder={placeholder}
      onChange={(e) => onChange(Number(e.target.value))}
      className="mt-1 w-full rounded-control border border-border bg-surface-2 px-2.5 py-1.5 font-mono text-sm outline-none focus:border-primary"
    />
  );
}

// --- Edge: structural-function editor -----------------------------------------------

function EdgeEditor({
  spec,
  causal,
  index,
  onCausalChange,
  onSelect,
}: {
  spec: Spec;
  causal: CausalGraph;
  index: number;
  onCausalChange: (next: CausalGraph) => void;
  onSelect: (sel: CausalSelection) => void;
}) {
  const edge = causal.edges[index];
  if (!edge) return null;
  const parent = spec.features[edge.from];

  function patch(next: Partial<CausalEdge>) {
    const edges = causal.edges.map((e, i) => (i === index ? { ...e, ...next } : e));
    onCausalChange({ ...causal, edges });
  }

  function changeFn(fn: string) {
    // Reset params to the chosen fn's shape.
    const base: CausalEdge = { from: edge.from, to: edge.to, fn };
    if (fn === "linear" || fn === "logistic") {
      base.weight = edge.weight ?? 1;
      base.bias = edge.bias ?? 0;
    } else if (fn === "polynomial") {
      base.coeffs = edge.coeffs ?? [0, 1];
    } else if (fn === "map") {
      const mapping: Record<string, number> = {};
      (parent?.type === "categorical" ? parent.categories ?? [] : []).forEach(
        (c, i) => (mapping[c] = edge.mapping?.[c] ?? i),
      );
      base.mapping = mapping;
    }
    const edges = causal.edges.map((e, i) => (i === index ? base : e));
    onCausalChange({ ...causal, edges });
  }

  function remove() {
    onCausalChange({ ...causal, edges: causal.edges.filter((_, i) => i !== index) });
    onSelect(null);
  }

  const bad = !fnAcceptsParent(edge.fn, parent);

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border p-4">
        <Kicker>Edge</Kicker>
        <div className="mt-1 flex items-center gap-2 font-display text-lg font-semibold">
          <span>{edge.from}</span>
          <span className="text-text-faint">→</span>
          <span>{edge.to}</span>
        </div>
        {parent && (
          <div className="mt-1">
            <span className="text-xs text-text-faint">parent is </span>
            <TypeChip type={parent.type} />
          </div>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-4">
        <Row label="Structural function">
          <select
            value={edge.fn}
            onChange={(e) => changeFn(e.target.value)}
            className="mt-1 w-full rounded-control border border-border bg-surface-2 px-2.5 py-1.5 text-sm outline-none focus:border-primary"
          >
            {STRUCTURAL_FNS.map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </select>
        </Row>

        {bad && (
          <div className="mb-3 rounded-control border border-hazard bg-hazard-tint px-3 py-2 text-xs text-hazard">
            {edge.fn === "map"
              ? "map needs a categorical parent."
              : `${edge.fn} needs a numeric/boolean parent — use 'map' for categorical.`}
          </div>
        )}

        {(edge.fn === "linear" || edge.fn === "logistic") && (
          <div className="grid grid-cols-2 gap-2">
            <Row label="weight">
              <NumInput value={edge.weight ?? undefined} onChange={(n) => patch({ weight: n })} />
            </Row>
            <Row label="bias">
              <NumInput value={edge.bias ?? undefined} onChange={(n) => patch({ bias: n })} />
            </Row>
          </div>
        )}

        {edge.fn === "logistic" && (
          <p className="mb-3 text-xs italic text-text-faint">
            σ(weight·parent + bias) → a probability; a boolean child is then a Bernoulli draw.
          </p>
        )}

        {edge.fn === "polynomial" && (
          <PolyEditor coeffs={edge.coeffs ?? [0, 1]} onChange={(coeffs) => patch({ coeffs })} />
        )}

        {edge.fn === "map" && (
          <MapEditor
            mapping={edge.mapping ?? {}}
            categories={parent?.type === "categorical" ? parent.categories ?? [] : []}
            onChange={(mapping) => patch({ mapping })}
          />
        )}

        {edge.fn === "identity" && (
          <p className="text-sm text-text-muted">Pass-through: the child gets the parent's value.</p>
        )}

        <button
          onClick={remove}
          className="mt-4 inline-flex items-center gap-1.5 text-xs text-text-faint hover:text-hazard"
        >
          <Trash2 size={14} /> Delete edge
        </button>
      </div>
    </div>
  );
}

function PolyEditor({ coeffs, onChange }: { coeffs: number[]; onChange: (c: number[]) => void }) {
  return (
    <div>
      <Kicker>Coefficients · Σ cᵢ·parentⁱ</Kicker>
      <div className="mt-2 space-y-1.5">
        {coeffs.map((c, i) => (
          <div key={i} className="flex items-center gap-2">
            <span className="w-12 font-mono text-[11px] text-text-faint">c{i} (x^{i})</span>
            <input
              type="number"
              value={c}
              onChange={(e) => {
                const next = [...coeffs];
                next[i] = Number(e.target.value);
                onChange(next);
              }}
              className="flex-1 rounded-control border border-border bg-surface-2 px-2 py-1 font-mono text-xs outline-none focus:border-primary"
            />
            <button
              onClick={() => onChange(coeffs.filter((_, j) => j !== i))}
              className="text-text-faint hover:text-hazard"
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
      <button
        onClick={() => onChange([...coeffs, 0])}
        className="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:underline"
      >
        <Plus size={13} /> Add term
      </button>
    </div>
  );
}

function MapEditor({
  mapping,
  categories,
  onChange,
}: {
  mapping: Record<string, number>;
  categories: string[];
  onChange: (m: Record<string, number>) => void;
}) {
  if (categories.length === 0) {
    return <p className="text-xs italic text-text-faint">Parent has no categories to map.</p>;
  }
  return (
    <div>
      <Kicker>Category → contribution</Kicker>
      <div className="mt-2 space-y-1.5">
        {categories.map((c) => (
          <div key={c} className="flex items-center gap-2">
            <span className="w-24 truncate font-mono text-xs text-text-muted">{c}</span>
            <input
              type="number"
              value={mapping[c] ?? 0}
              onChange={(e) => onChange({ ...mapping, [c]: Number(e.target.value) })}
              className="flex-1 rounded-control border border-border bg-surface-2 px-2 py-1 font-mono text-xs outline-none focus:border-primary"
            />
          </div>
        ))}
      </div>
    </div>
  );
}

// --- Node: noise + intervention -----------------------------------------------------

function NodeEditor({
  spec,
  causal,
  name,
  onCausalChange,
}: {
  spec: Spec;
  causal: CausalGraph;
  name: string;
  onCausalChange: (next: CausalGraph) => void;
}) {
  const feature = spec.features[name];
  const isDerived = inEdges(causal, name).length > 0;
  const noise = causal.noise?.[name] ?? { dist: "none" };
  const ivMap = interventionMap(causal);
  const intervened = name in ivMap;

  function setNoise(next: { dist: string; params?: Record<string, number> }) {
    const nextNoise = { ...(causal.noise ?? {}) };
    if (next.dist === "none") nextNoise[name] = { dist: "none" };
    else nextNoise[name] = next;
    onCausalChange({ ...causal, noise: nextNoise });
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border p-4">
        <Kicker>Node</Kicker>
        <div className="mt-1 font-display text-xl font-semibold tracking-tight">{name}</div>
        <div className="mt-1 flex items-center gap-2">
          {feature && <TypeChip type={feature.type} />}
          <span className="text-[11px] text-text-faint">{isDerived ? "derived" : "root (sampled)"}</span>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-4">
        {isDerived ? (
          <>
            <Row label="Node noise ε">
              <select
                value={noise.dist}
                onChange={(e) =>
                  setNoise(
                    e.target.value === "none"
                      ? { dist: "none" }
                      : { dist: e.target.value, params: DIST_PARAMS[e.target.value] ?? {} },
                  )
                }
                className="mt-1 w-full rounded-control border border-border bg-surface-2 px-2.5 py-1.5 text-sm outline-none focus:border-primary"
              >
                {NOISE_DISTS.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </Row>
            {noise.dist !== "none" && noise.params && (
              <div className="grid grid-cols-2 gap-2">
                {Object.keys(noise.params).map((k) => (
                  <Row key={k} label={k}>
                    <NumInput
                      value={noise.params![k]}
                      onChange={(n) => setNoise({ dist: noise.dist, params: { ...noise.params, [k]: n } })}
                    />
                  </Row>
                ))}
              </div>
            )}
          </>
        ) : (
          <p className="mb-4 text-sm text-text-muted">
            This is a root feature — its distribution is edited in the Table view's Inspector. Add an
            incoming edge to make it derived.
          </p>
        )}

        <div className="mt-2 border-t border-border pt-4">
          <Kicker>Intervention · do({name})</Kicker>
          <label className="mt-2 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={intervened}
              onChange={(e) => onCausalChange(setIntervention(causal, name, e.target.checked ? 0 : null))}
              className="accent-[var(--primary)]"
            />
            Fix this node to a constant (detach its parents)
          </label>
          {intervened && (
            <Row label="value">
              <NumInput
                value={ivMap[name]}
                onChange={(n) => onCausalChange(setIntervention(causal, name, n))}
              />
            </Row>
          )}
        </div>
      </div>
    </div>
  );
}
