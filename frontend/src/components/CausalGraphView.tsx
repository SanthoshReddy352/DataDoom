import { useMemo } from "react";
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MarkerType,
  Position,
  type Edge,
  type Node,
  type NodeProps,
} from "reactflow";
import "reactflow/dist/style.css";
import { Crosshair } from "lucide-react";
import { topoLayers } from "@/lib/causal";
import { edgeFnLabel, edgeParamRows, featureSettings, type SettingRow } from "@/lib/summary";
import { loadLayout } from "@/lib/viewLayout";
import { TypeChip } from "./ui";
import { FailureBadges } from "./FailureBadges";
import type { Failure, CausalTruth, Spec } from "@/lib/types";

type SavedNode = { x: number; y: number; width?: number; height?: number };

interface ViewNodeData {
  label: string;
  ftype?: string;
  derived: boolean;
  intervened: boolean;
  rows: SettingRow[];
  failures?: Failure[];
}

// Mirrors the editor's FeatureNode (read-only): same header/body/scroll structure
// so a node at the same width/height renders identically.
function ViewNode({ data }: NodeProps<ViewNodeData>) {
  return (
    <div className="flex h-full w-full flex-col overflow-hidden rounded-card border border-border bg-surface-1 shadow-card">
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <div className="flex items-center gap-1.5 border-b border-border bg-surface-2 px-2.5 py-1.5">
        <span className="min-w-0 flex-1 truncate font-display text-sm font-semibold tracking-tight text-text">
          {data.label}
        </span>
        {data.intervened && (
          <span className="inline-flex items-center gap-0.5 text-[10px] text-primary" title="intervened (do)">
            <Crosshair size={10} /> do
          </span>
        )}
      </div>
      <div className="min-h-0 flex-1 overflow-auto px-2.5 py-2">
        <div className="flex items-center gap-2">
          {data.ftype && <TypeChip type={data.ftype} />}
          <span className="text-[10px] uppercase tracking-wide text-text-faint">
            {data.derived ? "derived" : "root"}
          </span>
        </div>
        <FailureBadges failures={data.failures} column={data.label} className="mt-1.5" />
        {data.rows.length > 0 && (
          <dl className="mt-1.5 space-y-0.5">
            {data.rows.map((s, i) => (
              <div key={i} className="flex items-start justify-between gap-2 text-[11px] leading-snug">
                <dt className="shrink-0 text-text-faint">{s.label}</dt>
                <dd
                  className="break-words text-right font-mono"
                  style={{ color: s.tone === "accent" ? "var(--primary)" : "var(--text-muted)" }}
                >
                  {s.value}
                </dd>
              </div>
            ))}
          </dl>
        )}
      </div>
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  );
}

const nodeTypes = { view: ViewNode };

export function CausalGraphView({
  truth,
  spec,
  datasetId,
  runId,
  empirical,
}: {
  truth: CausalTruth;
  spec?: Spec | null;
  datasetId?: string;
  runId?: string;
  empirical?: Record<string, { mean?: number; std?: number }>;
}) {
  const names = useMemo(() => {
    if (truth.nodes && truth.nodes.length) return truth.nodes;
    const s = new Set<string>();
    truth.edges.forEach((e) => {
      s.add(e.from);
      s.add(e.to);
    });
    return [...s];
  }, [truth]);

  const nodes: Node<ViewNodeData>[] = useMemo(() => {
    // The arrangement frozen for *this run* at generation time (positions +
    // widths), so editing the Canvas graph afterwards never changes a past run's
    // view. Falls back to the dataset's live layout (older runs without a
    // snapshot), then to a topological layout (e.g. a CLI-authored spec).
    const datasetLayout = loadLayout<Record<string, SavedNode>>(datasetId, "graph-nodes", {});
    const saved = loadLayout<Record<string, SavedNode>>(runId, "graph-nodes", datasetLayout);
    const layers = topoLayers(
      names,
      truth.edges.map((e) => ({ from: e.from, to: e.to, fn: e.fn })),
    );
    const perLayer: Record<number, number> = {};
    const incoming = (name: string) => truth.edges.filter((e) => e.to === name);
    return names.map((name) => {
      const layer = layers[name] ?? 0;
      const row = perLayer[layer] ?? 0;
      perLayer[layer] = row + 1;
      const s = saved[name];

      const feat = spec?.features[name];
      const rows: SettingRow[] = [];
      if (feat) featureSettings(feat).forEach((r) => rows.push(r));
      for (const e of incoming(name)) edgeParamRows(e).forEach((r) => rows.push(r));
      const emp = empirical?.[name];
      if (emp && (emp.mean != null || emp.std != null)) {
        rows.push({
          label: "realized",
          value: `x̄=${emp.mean?.toFixed(2) ?? "—"} s=${emp.std?.toFixed(2) ?? "—"}`,
        });
      }

      const width = s?.width ?? 216;
      return {
        id: name,
        type: "view",
        position: s ? { x: s.x, y: s.y } : { x: layer * 300 + 24, y: row * 184 + 24 },
        width: s?.width,
        // Height auto (content-driven) — same as the editor, so every row shows.
        style: { width },
        data: {
          label: name,
          ftype: feat?.type,
          derived: incoming(name).length > 0,
          intervened: name in (truth.interventions ?? {}),
          rows,
          failures: spec?.failures,
        },
        draggable: false,
      };
    });
  }, [names, truth, spec, empirical, datasetId, runId]);

  const edges: Edge[] = useMemo(
    () =>
      truth.edges.map((e, i) => ({
        id: `t${i}`,
        source: e.from,
        target: e.to,
        type: "smoothstep",
        label: edgeFnLabel(e),
        style: {
          stroke: "var(--border-strong)",
          strokeWidth: 1.5,
          strokeDasharray: e.active ? undefined : "4 3",
          opacity: e.active ? 1 : 0.4,
        },
        labelStyle: { fontSize: 10, fill: "var(--text-muted)", fontWeight: 500 },
        labelBgStyle: { fill: "var(--surface-1)", fillOpacity: 0.92 },
        labelBgPadding: [4, 2] as [number, number],
        labelBgBorderRadius: 4,
        markerEnd: { type: MarkerType.ArrowClosed, color: "var(--border-strong)" },
      })),
    [truth],
  );

  return (
    <div className="h-[460px] bg-bg">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        fitView
        minZoom={0.3}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="var(--border)" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
