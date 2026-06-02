import { Copy, X } from "lucide-react";
import { Kicker } from "./ui";
import type { Spec } from "@/lib/types";

// Minimal YAML-ish renderer for the read-only spec drawer (CodeMirror is overkill
// for P1). The spec is the shareable, reproducible artifact — show it plainly.
function toYaml(value: unknown, indent = 0): string {
  const pad = "  ".repeat(indent);
  if (value === null || value === undefined) return "null";
  if (Array.isArray(value)) {
    if (value.length === 0) return "[]";
    return "\n" + value.map((v) => `${pad}- ${toYaml(v, indent + 1).replace(/^\n/, "")}`).join("\n");
  }
  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>);
    if (entries.length === 0) return "{}";
    return (
      "\n" +
      entries
        .map(([k, v]) => {
          const rendered = toYaml(v, indent + 1);
          const inline = typeof v !== "object" || v === null;
          return `${pad}${k}:${inline ? " " + rendered : rendered}`;
        })
        .join("\n")
    );
  }
  if (typeof value === "string") return value;
  return String(value);
}

export function SpecDrawer({ open, onClose, spec }: { open: boolean; onClose: () => void; spec: Spec }) {
  if (!open) return null;
  const yaml = toYaml(spec).replace(/^\n/, "");
  return (
    <div className="fixed inset-0 z-40 flex animate-fade-in justify-end">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-[2px]" onClick={onClose} aria-hidden />
      <div className="relative z-10 flex h-full w-full max-w-md animate-slide-up flex-col border-l border-border bg-surface-1 shadow-pop">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div>
            <Kicker>Spec · read-only</Kicker>
            <div className="font-mono text-sm text-text">{spec.name}.datadoom.yaml</div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigator.clipboard?.writeText(yaml)}
              className="text-text-faint hover:text-text"
              title="Copy"
            >
              <Copy size={16} />
            </button>
            <button onClick={onClose} className="text-text-faint hover:text-text" aria-label="Close">
              <X size={18} />
            </button>
          </div>
        </div>
        <pre className="min-h-0 flex-1 overflow-auto bg-surface-2 p-4 font-mono text-xs leading-relaxed text-text-muted">
          {yaml}
        </pre>
      </div>
    </div>
  );
}
