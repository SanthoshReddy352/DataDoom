import { Download, FileCheck2, FileText, Package } from "lucide-react";
import { Button } from "./ui";
import { Modal } from "./Modal";
import { clsx } from "@/lib/clsx";
import { api } from "@/lib/api";
import type { Artifact } from "@/lib/types";

function fmtBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

// A short, human description + badge per artifact, keyed off its version so the
// clean and injected data files are never confused for one another.
const VERSION_META: Record<string, { badge: string; cls: string; desc: string }> = {
  clean: { badge: "clean", cls: "bg-success-tint text-success", desc: "the pristine generated data" },
  injected: { badge: "injected", cls: "bg-warning-tint text-warning", desc: "data with the failure modes applied" },
  spec: { badge: "locked spec", cls: "bg-primary-tint text-primary", desc: "exact spec + seed to regenerate" },
  audit: { badge: "audit", cls: "bg-info-tint text-info", desc: "human-readable report of this run" },
};

function describe(a: Artifact): string {
  if (a.filename === "metadata.json") return "run metadata + checksums";
  return VERSION_META[a.version]?.desc ?? a.format.toUpperCase() + " export";
}

// A completed run writes its data, metadata, the locked spec, and an audit report
// locally; Export surfaces them for download. The bundle (everything, zipped) and
// the audit report lead visually.
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
  const audit = artifacts.find((a) => a.version === "audit");
  // Order: clean data, injected data, then everything else — stable + readable.
  const order = (a: Artifact) => (a.version === "clean" ? 0 : a.version === "injected" ? 1 : a.filename === "metadata.json" ? 2 : 3);
  const files = [...artifacts].sort((a, b) => order(a) - order(b) || a.filename.localeCompare(b.filename));

  return (
    <Modal open={open} onClose={onClose} kicker="Take it with you" title="Export"
      footer={<Button onClick={onClose}>Done</Button>}>
      <div className="space-y-3">
        <a
          href={api.bundleUrl(runId)}
          className="flex items-center gap-3 rounded-control border-2 border-primary bg-primary-tint px-4 py-3"
        >
          <Package size={18} className="text-primary" />
          <div className="flex-1">
            <div className="text-sm font-medium text-text">Download bundle (.zip)</div>
            <div className="text-xs text-text-muted">
              data + <span className="font-mono">metadata.json</span> + the locked{" "}
              <span className="font-mono">spec.resolved.yaml</span> +{" "}
              <span className="font-mono">audit_report.md</span> — everything to regenerate and review.
            </div>
          </div>
        </a>

        {audit && (
          <a
            href={api.downloadUrl(audit.artifact_id)}
            className="flex items-center gap-3 rounded-control border border-info bg-info-tint/40 px-4 py-3"
          >
            <FileCheck2 size={18} className="text-info" />
            <div className="flex-1">
              <div className="text-sm font-medium text-text">Audit report</div>
              <div className="text-xs text-text-muted">
                Compliance, the column guide (stats + issues + ML advice), failures, and checksums — as Markdown.
              </div>
            </div>
            <Download size={15} className="text-info" />
          </a>
        )}

        <div className="kicker pt-2">Individual files</div>
        {files.map((a) => {
          const meta = VERSION_META[a.version];
          return (
            <a
              key={a.artifact_id}
              href={api.downloadUrl(a.artifact_id)}
              className="flex items-center gap-3 rounded-control border border-border bg-surface-2 px-4 py-2.5 hover:border-border-strong"
            >
              <FileText size={15} className="shrink-0 text-text-muted" />
              <span className="font-mono text-sm text-text">{a.filename}</span>
              {meta && a.filename !== "metadata.json" && (
                <span className={clsx("rounded-pill px-1.5 text-[10px] font-semibold", meta.cls)}>{meta.badge}</span>
              )}
              <span className="hidden text-xs text-text-faint sm:inline">{describe(a)}</span>
              <span className="ml-auto font-mono text-xs text-text-faint tnum">{fmtBytes(a.size_bytes)}</span>
            </a>
          );
        })}
        <p className="pt-1 text-xs text-text-faint">
          The <span className="font-mono">injected</span> file carries the configured failure modes; the{" "}
          <span className="font-mono">clean</span> file is the pristine baseline. Data formats follow the spec's{" "}
          <span className="font-mono">export.formats</span>.
        </p>
      </div>
    </Modal>
  );
}
