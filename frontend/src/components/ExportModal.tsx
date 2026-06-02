import { Download, FileText, Package } from "lucide-react";
import { Button } from "./ui";
import { Modal } from "./Modal";
import { api } from "@/lib/api";
import type { Artifact } from "@/lib/types";

function fmtBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

// In P1 a completed run has already written its artifacts (CSV + metadata +
// resolved spec) locally; Export surfaces them for download. The spec is the
// shareable, reproducible artifact, so it leads visually.
export function ExportModal({
  open,
  onClose,
  runId,
  artifacts,
}: {
  open: boolean;
  onClose: () => void;
  runId: string;
  artifacts: Artifact[];
}) {
  return (
    <Modal open={open} onClose={onClose} kicker="Take it with you" title="Export"
      footer={<Button onClick={onClose}>Done</Button>}>
      <div className="space-y-3">
        <a
          href={api.bundleUrl(runId)}
          className="flex items-center gap-3 rounded-control border-2 border-primary bg-primary-tint px-4 py-3"
        >
          <FileText size={18} className="text-primary" />
          <div className="flex-1">
            <div className="text-sm font-medium text-text">Download bundle</div>
            <div className="text-xs text-text-muted">
              data.csv + metadata.json + the resolved <span className="font-mono">spec.datadoom.yaml</span> — everything to regenerate identically.
            </div>
          </div>
          <Package size={16} className="text-primary" />
        </a>

        <div className="kicker pt-2">Individual files</div>
        {artifacts.map((a) => (
          <a
            key={a.artifact_id}
            href={api.downloadUrl(a.artifact_id)}
            className="flex items-center gap-3 rounded-control border border-border bg-surface-2 px-4 py-2.5 hover:border-border-strong"
          >
            <Download size={15} className="text-text-muted" />
            <span className="font-mono text-sm text-text">data.{a.format}</span>
            <span className="ml-auto font-mono text-xs text-text-faint tnum">{fmtBytes(a.size_bytes)}</span>
          </a>
        ))}
        <p className="pt-1 text-xs text-text-faint">
          Parquet/JSON exporters and train/test splits arrive in Phase 5.
        </p>
      </div>
    </Modal>
  );
}
