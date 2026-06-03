import { useEffect, useMemo, useRef, useState } from "react";
import ReactFlow, {
  Background,
  BackgroundVariant,
  Handle,
  MarkerType,
  NodeResizer,
  Position,
  useNodesState,
  useReactFlow,
  type Connection,
  type ConnectionLineComponentProps,
  type Edge,
  type Node,
  type NodeProps,
} from "reactflow";
import "reactflow/dist/style.css";
import { AlertTriangle, Crosshair, Maximize2, Trash2, ZoomIn, ZoomOut } from "lucide-react";
import type { CausalSelection } from "./CausalInspector";
import { TypeChip } from "./ui";
import { FailureBadges } from "./FailureBadges";
import { causalSettings, edgeFnLabel, featureSettings, type SettingRow } from "@/lib/summary";
import { defaultEdge, derivedNames, getCausal, interventionMap, topoLayers, wouldCycle } from "@/lib/causal";
import { loadLayout, saveLayout } from "@/lib/viewLayout";
import type { CausalGraph, Failure, Spec } from "@/lib/types";

type SavedNode = { x: number; y: number; width?: number; height?: number };

interface FeatureNodeData {
  label: string;
  ftype: string;
  derived: boolean;
  intervened: boolean;
  selected: boolean;
  rows: SettingRow[];
  failures?: Failure[];
  onDelete: () => void;
}

function FeatureNode({ data }: NodeProps<FeatureNodeData>) {
  return (
    <>
      <NodeResizer isVisible={data.selected} minWidth={168} minHeight={72} lineClassName="!border-primary" handleClassName="!h-2 !w-2 !rounded-[2px] !border-primary !bg-surface-1" />
      <div
        className="group flex h-full w-full flex-col overflow-hidden rounded-card border bg-surface-1 shadow-card"
        style={{
          borderColor: data.selected ? "var(--primary)" : "var(--border)",
          boxShadow: data.selected ? "0 0 0 2px var(--primary), var(--shadow-lift)" : undefined,
        }}
      >
        <Handle
          type="target"
          position={Position.Left}
          className="!h-3.5 !w-3.5 !border-2 !border-surface-1 !bg-border-strong hover:!bg-primary"
        />

        <div className="flex items-center gap-1.5 border-b border-border bg-surface-2 px-2.5 py-1.5">
          <span className="min-w-0 flex-1 truncate font-display text-sm font-semibold tracking-tight text-text">
            {data.label}
          </span>
          {data.intervened && (
            <span className="inline-flex items-center gap-0.5 text-[10px] text-primary" title="intervened (do)">
              <Crosshair size={10} /> do
            </span>
          )}
          <button
            title="Delete column"
            onClick={(e) => {
              e.stopPropagation();
              data.onDelete();
            }}
            className="rounded p-0.5 text-text-faint opacity-0 transition-opacity hover:bg-hazard-tint hover:text-hazard group-hover:opacity-100"
          >
            <Trash2 size={12} />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-auto px-2.5 py-2">
          <div className="flex items-center gap-2">
            <TypeChip type={data.ftype} />
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

        <Handle
          type="source"
          position={Position.Right}
          className="!h-3.5 !w-3.5 !border-2 !border-surface-1 !bg-primary hover:!scale-125"
        />
      </div>
    </>
  );
}

const nodeTypes = { feature: FeatureNode };

/** Zoom in / out / reset — identical look & position to the Table canvas. */
function GraphZoomControls() {
  const { zoomIn, zoomOut, fitView } = useReactFlow();
  return (
    <div className="absolute bottom-3 right-3 z-10 flex flex-col overflow-hidden rounded-control border border-border bg-surface-1 shadow-card">
      <ZoomBtn title="Zoom in" onClick={() => zoomIn({ duration: 150 })}>
        <ZoomIn size={15} />
      </ZoomBtn>
      <ZoomBtn title="Zoom out" onClick={() => zoomOut({ duration: 150 })}>
        <ZoomOut size={15} />
      </ZoomBtn>
      <ZoomBtn title="Reset view" onClick={() => fitView({ duration: 200, padding: 0.2 })}>
        <Maximize2 size={14} />
      </ZoomBtn>
    </div>
  );
}

function ZoomBtn({ children, onClick, title }: { children: React.ReactNode; onClick: () => void; title: string }) {
  return (
    <button
      title={title}
      onClick={onClick}
      onPointerDown={(e) => e.stopPropagation()}
      className="flex h-8 w-8 items-center justify-center border-b border-border text-text-muted last:border-b-0 hover:bg-surface-2 hover:text-text"
    >
      {children}
    </button>
  );
}

function ConnectionLine({ fromX, fromY, toX, toY }: ConnectionLineComponentProps) {
  const angle = Math.atan2(toY - fromY, toX - fromX);
  const a = 7;
  return (
    <g>
      <path
        d={`M${fromX},${fromY} C ${fromX + 70},${fromY} ${toX - 70},${toY} ${toX},${toY}`}
        stroke="var(--primary)"
        strokeWidth={2}
        fill="none"
        strokeDasharray="6 4"
      />
      <polygon
        points={`0,0 ${-a * 1.4},${-a * 0.7} ${-a * 1.4},${a * 0.7}`}
        transform={`translate(${toX},${toY}) rotate(${(angle * 180) / Math.PI})`}
        fill="var(--primary)"
      />
    </g>
  );
}

export function CausalGraphEditor({
  spec,
  datasetId,
  selection,
  onSelect,
  onCausalChange,
  onDeleteColumn,
}: {
  spec: Spec;
  datasetId?: string;
  selection: CausalSelection;
  onSelect: (sel: CausalSelection) => void;
  onCausalChange: (next: CausalGraph) => void;
  onDeleteColumn: (name: string) => void;
}) {
  const causal = useMemo(() => getCausal(spec), [spec]);
  const featureNames = useMemo(() => Object.keys(spec.features), [spec]);
  const [toast, setToast] = useState<string | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<FeatureNodeData>([]);
  const savedRef = useRef<Record<string, SavedNode>>(loadLayout(datasetId, "graph-nodes", {}));

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 2600);
    return () => window.clearTimeout(t);
  }, [toast]);

  const derived = useMemo(() => derivedNames(causal), [causal]);
  const ivMap = useMemo(() => interventionMap(causal), [causal]);

  // Sync node *data* while preserving user-set positions and sizes.
  useEffect(() => {
    setNodes((cur) => {
      const curMap = new Map(cur.map((n) => [n.id, n]));
      const layers = topoLayers(featureNames, causal.edges);
      const perLayer: Record<number, number> = {};
      return featureNames.map((name) => {
        const ex = curMap.get(name);
        const saved = savedRef.current[name];
        const layer = layers[name] ?? 0;
        const row = perLayer[layer] ?? 0;
        perLayer[layer] = row + 1;
        const fallback = saved ? { x: saved.x, y: saved.y } : { x: layer * 300 + 24, y: row * 184 + 24 };
        return {
          id: name,
          type: "feature",
          position: ex?.position ?? fallback,
          width: ex?.width ?? saved?.width,
          // Height is content-driven (auto) so every setting is always visible —
          // we persist width + position only, never a height that could clip rows.
          style: ex?.style ?? (saved?.width ? { width: saved.width } : { width: 216 }),
          draggable: true,
          data: {
            label: name,
            ftype: spec.features[name].type,
            derived: derived.has(name),
            intervened: name in ivMap,
            selected: selection?.kind === "node" && selection.name === name,
            rows: [...featureSettings(spec.features[name]), ...causalSettings(causal, name)],
            failures: spec.failures,
            onDelete: () => onDeleteColumn(name),
          },
        } as Node<FeatureNodeData>;
      });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [spec, causal, derived, ivMap, selection, featureNames]);

  // Persist node positions/sizes (debounced) so dragged/resized layouts survive.
  useEffect(() => {
    if (nodes.length === 0) return;
    const t = window.setTimeout(() => {
      const map: Record<string, SavedNode> = {};
      for (const n of nodes) {
        map[n.id] = {
          x: n.position.x,
          y: n.position.y,
          width: n.width ?? undefined,
        };
      }
      savedRef.current = map;
      saveLayout(datasetId, "graph-nodes", map);
    }, 400);
    return () => window.clearTimeout(t);
  }, [nodes, datasetId]);

  const edges: Edge[] = useMemo(() => {
    return causal.edges.map((e, i) => {
      const targetIntervened = e.to in ivMap;
      const isSel = selection?.kind === "edge" && selection.index === i;
      return {
        id: `e${i}`,
        source: e.from,
        target: e.to,
        label: edgeFnLabel(e),
        type: "smoothstep",
        animated: !targetIntervened,
        updatable: true,
        selected: isSel,
        style: {
          stroke: isSel ? "var(--primary)" : "var(--border-strong)",
          strokeWidth: isSel ? 2.5 : 1.5,
          strokeDasharray: targetIntervened ? "4 3" : undefined,
          opacity: targetIntervened ? 0.45 : 1,
        },
        labelStyle: { fontSize: 10, fill: "var(--text-muted)", fontWeight: 500 },
        labelBgStyle: { fill: "var(--surface-1)", fillOpacity: 0.92 },
        labelBgPadding: [4, 2] as [number, number],
        labelBgBorderRadius: 4,
        markerEnd: { type: MarkerType.ArrowClosed, color: isSel ? "var(--primary)" : "var(--border-strong)" },
      };
    });
  }, [causal.edges, ivMap, selection]);

  function tryAddEdge(source: string, target: string): boolean {
    if (source === target) {
      setToast("A feature can't depend on itself.");
      return false;
    }
    if (causal.edges.some((e) => e.from === source && e.to === target)) {
      setToast(`${source} → ${target} already exists.`);
      return false;
    }
    if (wouldCycle(causal.edges, source, target)) {
      setToast(`${source} → ${target} would create a cycle — rejected.`);
      return false;
    }
    return true;
  }

  function onConnect(c: Connection) {
    if (!c.source || !c.target) return;
    if (!tryAddEdge(c.source, c.target)) return;
    const edge = defaultEdge(c.source, c.target, spec.features[c.source]);
    const next = { ...causal, edges: [...causal.edges, edge] };
    onCausalChange(next);
    onSelect({ kind: "edge", index: next.edges.length - 1 });
  }

  function onEdgeUpdate(oldEdge: Edge, conn: Connection) {
    if (!conn.source || !conn.target) return;
    const index = Number(oldEdge.id.slice(1));
    const without = causal.edges.filter((_, i) => i !== index);
    if (conn.source === conn.target) return setToast("A feature can't depend on itself.");
    if (without.some((e) => e.from === conn.source && e.to === conn.target))
      return setToast(`${conn.source} → ${conn.target} already exists.`);
    if (wouldCycle(without, conn.source, conn.target))
      return setToast(`${conn.source} → ${conn.target} would create a cycle — rejected.`);
    const moved = { ...causal.edges[index], from: conn.source, to: conn.target };
    onCausalChange({ ...causal, edges: causal.edges.map((e, i) => (i === index ? moved : e)) });
  }

  if (featureNames.length < 2) {
    return (
      <div className="dotgrid flex h-full items-center justify-center bg-bg p-10 text-center text-text-faint">
        <div className="max-w-xs">
          <p className="font-display text-lg font-semibold text-text-muted">Wire up causality</p>
          <p className="mt-1 text-sm">Add at least two columns (in Table view) to draw dependencies between them.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-full bg-bg">
      {toast && (
        <div className="absolute left-1/2 top-3 z-10 -translate-x-1/2 animate-slide-up rounded-pill border border-hazard bg-hazard-tint px-3 py-1.5 text-xs text-hazard shadow-card">
          <span className="inline-flex items-center gap-1.5">
            <AlertTriangle size={13} /> {toast}
          </span>
        </div>
      )}
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onConnect={onConnect}
        onEdgeUpdate={onEdgeUpdate}
        connectionLineComponent={ConnectionLine}
        onNodeClick={(_, n) => onSelect({ kind: "node", name: n.id })}
        onEdgeClick={(_, e) => onSelect({ kind: "edge", index: Number(e.id.slice(1)) })}
        onPaneClick={() => onSelect(null)}
        fitView
        minZoom={0.3}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="var(--border)" />
        <GraphZoomControls />
      </ReactFlow>
      <div className="pointer-events-none absolute bottom-3 left-3 text-xs italic text-text-faint">
        Drag a node to move it · drag its right dot to another node to link · drag an edge end to reconnect.
      </div>
    </div>
  );
}
