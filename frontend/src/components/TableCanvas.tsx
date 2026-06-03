import { GripVertical, Maximize2, Plus, Trash2, ZoomIn, ZoomOut } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { clsx } from "@/lib/clsx";
import { TypeChip } from "./ui";
import { FailureBadges } from "./FailureBadges";
import { causalSettings, featureSettings, type SettingRow } from "@/lib/summary";
import { getCausal } from "@/lib/causal";
import { previewNumeric } from "@/lib/sampling";
import { loadLayout, saveLayout } from "@/lib/viewLayout";
import type { Failure, Feature, Spec } from "@/lib/types";

const DEFAULT_W = 212;
const MIN_W = 132;
const PREVIEW_ROWS = 10;
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

interface Transform {
  x: number;
  y: number;
  scale: number;
}

export function TableCanvas({
  spec,
  datasetId,
  selected,
  showPreview,
  onSelect,
  onRename,
  onDelete,
  onReorder,
  onAddColumn,
}: {
  spec: Spec;
  datasetId?: string;
  selected: string | null;
  showPreview: boolean;
  onSelect: (name: string) => void;
  onRename: (oldName: string, next: string) => void;
  onDelete: (name: string) => void;
  onReorder: (names: string[]) => void;
  onAddColumn: () => void;
}) {
  const names = Object.keys(spec.features);
  const causal = getCausal(spec);

  const containerRef = useRef<HTMLDivElement>(null);
  const [tf, setTf] = useState<Transform>(() =>
    loadLayout<Transform>(datasetId, "table-view", { x: 36, y: 32, scale: 1 }),
  );
  const tfRef = useRef(tf);
  tfRef.current = tf;

  const [widths, setWidths] = useState<Record<string, number>>(() =>
    loadLayout<Record<string, number>>(datasetId, "table-cols", {}),
  );
  const widthOf = (name: string) => widths[name] ?? DEFAULT_W;

  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [over, setOver] = useState<{ index: number; before: boolean } | null>(null);
  const resizing = useRef<{ name: string; startX: number; startW: number } | null>(null);
  const pan = useRef<{ sx: number; sy: number; ox: number; oy: number } | null>(null);
  const [panning, setPanning] = useState(false);

  // persist transform (debounced) + widths
  useEffect(() => {
    const t = window.setTimeout(() => saveLayout(datasetId, "table-view", tf), 350);
    return () => window.clearTimeout(t);
  }, [tf, datasetId]);

  // Non-passive wheel: pan, or ⌘/Ctrl-zoom toward the cursor.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = el.getBoundingClientRect();
      const cx = e.clientX - rect.left;
      const cy = e.clientY - rect.top;
      if (e.ctrlKey || e.metaKey) {
        setTf((p) => {
          const ns = clamp(p.scale * Math.exp(-e.deltaY * 0.0016), 0.4, 2.4);
          const k = ns / p.scale;
          return { scale: ns, x: cx - (cx - p.x) * k, y: cy - (cy - p.y) * k };
        });
      } else {
        setTf((p) => ({ ...p, x: p.x - e.deltaX, y: p.y - e.deltaY }));
      }
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  // --- panning (pointer capture on the surface; cards stop propagation) ---
  function onSurfacePointerDown(e: React.PointerEvent) {
    if (e.button !== 0) return;
    pan.current = { sx: e.clientX, sy: e.clientY, ox: tfRef.current.x, oy: tfRef.current.y };
    setPanning(true);
    try {
      e.currentTarget.setPointerCapture(e.pointerId);
    } catch {
      /* ignore */
    }
  }
  function onSurfacePointerMove(e: React.PointerEvent) {
    const p0 = pan.current;
    if (!p0) return;
    // Capture targets now — the setTf updater runs later, by which time
    // pan.current may already be null (pointerup), which would throw.
    const nx = p0.ox + (e.clientX - p0.sx);
    const ny = p0.oy + (e.clientY - p0.sy);
    setTf((p) => ({ ...p, x: nx, y: ny }));
  }
  function endPan(e: React.PointerEvent) {
    if (!pan.current) return;
    pan.current = null;
    setPanning(false);
    try {
      e.currentTarget.releasePointerCapture(e.pointerId);
    } catch {
      /* ignore */
    }
  }

  // --- column resize (scale-aware) ---
  function startResize(e: React.PointerEvent, name: string) {
    e.preventDefault();
    e.stopPropagation();
    resizing.current = { name, startX: e.clientX, startW: widthOf(name) };
    const move = (ev: PointerEvent) => {
      const r = resizing.current;
      if (!r) return;
      const dx = (ev.clientX - r.startX) / tfRef.current.scale;
      const w = Math.max(MIN_W, r.startW + dx);
      setWidths((prev) => ({ ...prev, [r.name]: w }));
    };
    const up = () => {
      resizing.current = null;
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      setWidths((prev) => {
        saveLayout(datasetId, "table-cols", prev);
        return prev;
      });
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  }

  // --- reorder ---
  function commitReorder() {
    if (dragIndex == null || !over || over.index === dragIndex) return cleanup();
    const arr = [...names];
    const [item] = arr.splice(dragIndex, 1);
    let target = arr.indexOf(names[over.index]);
    if (!over.before) target += 1;
    arr.splice(target, 0, item);
    onReorder(arr);
    cleanup();
  }
  function cleanup() {
    setDragIndex(null);
    setOver(null);
  }

  function resetView() {
    setTf({ x: 36, y: 32, scale: 1 });
  }

  const previews = showPreview ? names.map((n) => previewValues(spec.features[n])) : [];

  return (
    <div
      ref={containerRef}
      onPointerDown={onSurfacePointerDown}
      onPointerMove={onSurfacePointerMove}
      onPointerUp={endPan}
      onPointerCancel={endPan}
      className={clsx("relative h-full overflow-hidden bg-bg", panning ? "cursor-grabbing" : "cursor-grab")}
      style={{
        backgroundImage: "radial-gradient(var(--border) 1px, transparent 1px)",
        backgroundSize: `${22 * tf.scale}px ${22 * tf.scale}px`,
        backgroundPosition: `${tf.x}px ${tf.y}px`,
      }}
    >
      <div
        className="absolute left-0 top-0 origin-top-left"
        style={{ transform: `translate(${tf.x}px, ${tf.y}px) scale(${tf.scale})` }}
        onDrop={commitReorder}
        onDragOver={(e) => e.preventDefault()}
      >
        <div className="inline-flex overflow-hidden rounded-card border border-border bg-surface-1 shadow-lift">
          {names.map((name, i) => (
            <ColumnHeader
              key={name}
              name={name}
              width={widthOf(name)}
              feature={spec.features[name]}
              rows={[...featureSettings(spec.features[name]), ...causalSettings(causal, name)]}
              failures={spec.failures}
              preview={showPreview ? previews[i] : null}
              selected={selected === name}
              dragging={dragIndex === i}
              insertBefore={over?.index === i && over.before}
              insertAfter={over?.index === i && !over.before}
              isLast={i === names.length - 1}
              siblings={names.filter((n) => n !== name)}
              onSelect={() => onSelect(name)}
              onRename={(next) => onRename(name, next)}
              onDelete={() => onDelete(name)}
              onDragStart={() => setDragIndex(i)}
              onDragEnd={cleanup}
              onDragOverCard={(before) => setOver({ index: i, before })}
              onResizeStart={(e) => startResize(e, name)}
            />
          ))}

          <button
            onClick={onAddColumn}
            onPointerDown={(e) => e.stopPropagation()}
            title="Add column"
            className="ring-focus flex w-14 shrink-0 flex-col items-center justify-center gap-1 bg-surface-1 text-text-faint transition-colors hover:bg-primary-tint hover:text-primary"
          >
            <Plus size={20} />
          </button>
        </div>
      </div>

      {/* Caption */}
      <div className="pointer-events-none absolute bottom-3 left-4 right-32 text-xs italic text-text-faint">
        Unlimited canvas · drag empty space to pan · ⌘/Ctrl-scroll to zoom · drag a column edge to resize ·{" "}
        <GripVertical size={11} className="mb-0.5 inline" /> to reorder
      </div>

      {/* Zoom controls */}
      <div className="absolute bottom-3 right-3 flex flex-col overflow-hidden rounded-control border border-border bg-surface-1 shadow-card">
        <ZoomBtn title="Zoom in" onClick={() => setTf((p) => ({ ...p, scale: clamp(p.scale * 1.15, 0.4, 2.4) }))}>
          <ZoomIn size={15} />
        </ZoomBtn>
        <ZoomBtn title="Zoom out" onClick={() => setTf((p) => ({ ...p, scale: clamp(p.scale / 1.15, 0.4, 2.4) }))}>
          <ZoomOut size={15} />
        </ZoomBtn>
        <ZoomBtn title="Reset view" onClick={resetView}>
          <Maximize2 size={14} />
        </ZoomBtn>
      </div>
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

function ColumnHeader({
  name,
  width,
  feature,
  rows,
  failures,
  preview,
  selected,
  dragging,
  insertBefore,
  insertAfter,
  isLast,
  siblings,
  onSelect,
  onRename,
  onDelete,
  onDragStart,
  onDragEnd,
  onDragOverCard,
  onResizeStart,
}: {
  name: string;
  width: number;
  feature: Feature;
  rows: SettingRow[];
  failures?: Failure[];
  preview: string[] | null;
  selected: boolean;
  dragging: boolean;
  insertBefore: boolean;
  insertAfter: boolean;
  isLast: boolean;
  siblings: string[];
  onSelect: () => void;
  onRename: (next: string) => void;
  onDelete: () => void;
  onDragStart: () => void;
  onDragEnd: () => void;
  onDragOverCard: (before: boolean) => void;
  onResizeStart: (e: React.PointerEvent) => void;
}) {
  return (
    <div
      className={clsx("relative flex shrink-0 flex-col", !isLast && "border-r border-border", dragging && "opacity-40")}
      style={{ width }}
      onPointerDown={(e) => e.stopPropagation()}
      onClick={onSelect}
      onDragOver={(e) => {
        e.preventDefault();
        const rect = e.currentTarget.getBoundingClientRect();
        onDragOverCard(e.clientX < rect.left + rect.width / 2);
      }}
    >
      {insertBefore && <Insertion side="left" />}
      {insertAfter && <Insertion side="right" />}

      <div className={clsx("flex flex-col", selected ? "bg-primary-tint" : "bg-surface-2")}>
        <div className="flex items-center gap-1 px-2 pt-2">
          <span
            draggable
            onDragStart={onDragStart}
            onDragEnd={onDragEnd}
            onClick={(e) => e.stopPropagation()}
            title="Drag to reorder"
            className="cursor-grab text-text-faint hover:text-text active:cursor-grabbing"
          >
            <GripVertical size={14} />
          </span>
          <InlineName name={name} siblings={siblings} onRename={onRename} />
          <button
            title="Delete column"
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="ring-focus rounded p-1 text-text-faint transition-colors hover:bg-hazard-tint hover:text-hazard"
          >
            <Trash2 size={13} />
          </button>
        </div>
        <div className="px-2.5 pb-2 pt-1.5">
          <TypeChip type={feature.type} />
          <FailureBadges failures={failures} column={name} className="mt-1.5" />
          <dl className="mt-2 space-y-1">
            {rows.map((s, i) => (
              <div key={i} className="flex items-start justify-between gap-2 text-[11px] leading-snug">
                <dt className="shrink-0 text-text-faint">{s.label}</dt>
                <dd
                  className={clsx(
                    "break-words text-right font-mono",
                    s.tone === "accent" ? "text-primary" : s.tone === "muted" ? "text-text-faint" : "text-text-muted",
                  )}
                >
                  {s.value}
                </dd>
              </div>
            ))}
            {rows.length === 0 && <div className="text-[11px] text-text-faint">no settings</div>}
          </dl>
        </div>
      </div>

      {preview && (
        <div className="border-t border-border">
          {preview.map((v, i) => (
            <div
              key={i}
              className={clsx(
                "truncate border-b border-border/60 px-2.5 py-1.5 font-mono text-[11px] text-text-muted tnum last:border-b-0",
                i % 2 === 1 && "bg-surface-2/40",
              )}
              title={v}
            >
              {v}
            </div>
          ))}
        </div>
      )}

      {!isLast && (
        <div
          onPointerDown={onResizeStart}
          onClick={(e) => e.stopPropagation()}
          className="absolute -right-1 top-0 z-10 h-full w-2 cursor-col-resize hover:bg-primary/20"
        />
      )}
    </div>
  );
}

function Insertion({ side }: { side: "left" | "right" }) {
  return (
    <span className={clsx("absolute top-0 z-20 h-full w-0.5 bg-primary", side === "left" ? "left-0" : "right-0")} />
  );
}

function InlineName({
  name,
  siblings,
  onRename,
}: {
  name: string;
  siblings: string[];
  onRename: (next: string) => void;
}) {
  const [draft, setDraft] = useState(name);
  useEffect(() => setDraft(name), [name]);
  function commit() {
    const next = draft.trim();
    if (!next || next === name || siblings.includes(next)) {
      setDraft(name);
      return;
    }
    onRename(next);
  }
  return (
    <input
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onClick={(e) => e.stopPropagation()}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") (e.target as HTMLInputElement).blur();
        if (e.key === "Escape") {
          setDraft(name);
          (e.target as HTMLInputElement).blur();
        }
      }}
      spellCheck={false}
      className="ring-focus min-w-0 flex-1 rounded bg-transparent font-display text-sm font-semibold tracking-tight text-text outline-none focus:bg-surface-1 focus:px-1"
    />
  );
}

function previewValues(f: Feature): string[] {
  switch (f.type) {
    case "numeric": {
      if (!f.dist) return Array(PREVIEW_ROWS).fill("· derived ·");
      const vals = previewNumeric(f.dist, f.params ?? {}, 128);
      return vals.slice(0, PREVIEW_ROWS).map((v) => {
        let x = v;
        if (f.min != null) x = Math.max(f.min, x);
        if (f.max != null) x = Math.min(f.max, x);
        return f.dtype === "int" ? String(Math.round(x)) : x.toFixed(3);
      });
    }
    case "categorical": {
      const cats = f.categories ?? [];
      return Array.from({ length: PREVIEW_ROWS }, (_, i) => cats[i % (cats.length || 1)] ?? "—");
    }
    case "boolean":
      return Array.from({ length: PREVIEW_ROWS }, (_, i) => (i % 3 === 0 ? "true" : "false"));
    case "datetime":
      return Array.from({ length: PREVIEW_ROWS }, () => f.start ?? "2020-01-01");
    case "text":
      return Array(PREVIEW_ROWS).fill("lorem ipsum…");
    default:
      return Array(PREVIEW_ROWS).fill("—");
  }
}
