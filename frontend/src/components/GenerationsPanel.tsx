import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FolderClock, MoreHorizontal, Pencil, Trash2, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, IconButton, Kicker, Menu, MenuItem, Spinner, StatusBadge } from "./ui";
import { Field, Modal, TextInput } from "./Modal";
import { api } from "@/lib/api";
import { toast } from "@/store/toast";
import { clsx } from "@/lib/clsx";
import type { RunSummary } from "@/lib/types";

export function GenerationsPanel({
  datasetId,
  currentRunId,
  onOpenRun,
  dense,
}: {
  datasetId?: string;
  currentRunId?: string;
  onOpenRun?: (runId: string) => void;
  dense?: boolean;
}) {
  const nav = useNavigate();
  const qc = useQueryClient();
  const [renaming, setRenaming] = useState<RunSummary | null>(null);

  const runs = useQuery({
    queryKey: ["runs", datasetId],
    queryFn: () => api.listRuns(datasetId!),
    enabled: !!datasetId,
  });

  const del = useMutation({
    mutationFn: (runId: string) => api.deleteRun(runId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["runs", datasetId] });
      toast("Generation deleted", "success");
    },
    onError: (e: Error) => toast(e.message, "error"),
  });

  const items = useMemo(
    () => (runs.data ?? []).slice().sort((a, b) => (a.created_at < b.created_at ? 1 : -1)),
    [runs.data],
  );

  function open(runId: string) {
    if (onOpenRun) onOpenRun(runId);
    else nav(`/datasets/${datasetId}/results/${runId}`);
  }

  if (runs.isLoading) {
    return (
      <div className="flex justify-center py-10">
        <Spinner className="h-5 w-5" />
      </div>
    );
  }
  if (items.length === 0) {
    return (
      <div className="rounded-card border border-dashed border-border p-8 text-center text-sm text-text-faint">
        No generations yet. Hit <span className="font-medium text-text-muted">Generate</span> to make one — it'll be
        tracked here forever.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {!dense && (
        <p className="text-sm text-text-muted">
          Every generation of this dataset is kept — even across different configs — so you can revisit, rename, or
          download any of them at any time.
        </p>
      )}
      {items.map((r) => {
        const isCurrent = r.run_id === currentRunId;
        const label = r.name || `${r.run_id.slice(0, 8)}…`;
        return (
          <Card
            key={r.run_id}
            className={clsx(
              "overflow-hidden p-4 transition-colors",
              isCurrent ? "border-primary ring-1 ring-primary" : "hover:border-border-strong",
            )}
          >
            {/* Top: identity + status */}
            <div className="flex items-start gap-3">
              <div
                className={clsx(
                  "flex h-9 w-9 shrink-0 items-center justify-center rounded-control",
                  isCurrent ? "bg-primary-tint text-primary" : "bg-surface-2 text-text-faint",
                )}
              >
                <FolderClock size={17} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h4 className="truncate font-display text-[15px] font-semibold leading-tight tracking-tight text-text">
                    {label}
                  </h4>
                  {isCurrent && (
                    <span className="shrink-0 rounded-pill bg-primary-tint px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-primary">
                      viewing
                    </span>
                  )}
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-xs text-text-faint">
                  <span>{new Date(r.created_at).toLocaleString()}</span>
                  <Dot />
                  <span className="font-mono">seed {r.seed}</span>
                  {r.compliance_score != null && (
                    <>
                      <Dot />
                      <span>{Math.round(r.compliance_score * 100)}% compliance</span>
                    </>
                  )}
                </div>
              </div>
              <StatusBadge status={r.status} />
            </div>

            {/* Bottom: actions */}
            <div className="mt-3.5 flex items-center justify-end gap-2 border-t border-border pt-3">
              {!isCurrent && r.status === "completed" && (
                <Button className="px-3 py-1.5 text-xs" onClick={() => open(r.run_id)}>
                  Open results
                </Button>
              )}
              {r.status === "completed" && (
                <a href={api.bundleUrl(r.run_id)} download>
                  <Button variant="ghost" className="px-3 py-1.5 text-xs">
                    <Download size={14} /> Download
                  </Button>
                </a>
              )}
              <Menu trigger={({ toggle }) => <IconButton onClick={toggle}><MoreHorizontal size={16} /></IconButton>}>
                {(close) => (
                  <>
                    <MenuItem icon={<Pencil size={14} />} onClick={() => { close(); setRenaming(r); }}>
                      Rename
                    </MenuItem>
                    <MenuItem
                      icon={<Trash2 size={14} />}
                      danger
                      onClick={() => {
                        close();
                        if (confirm(`Delete generation "${label}"? Its artifacts are removed.`)) del.mutate(r.run_id);
                      }}
                    >
                      Delete
                    </MenuItem>
                  </>
                )}
              </Menu>
            </div>
          </Card>
        );
      })}

      <RenameRunModal run={renaming} datasetId={datasetId} onClose={() => setRenaming(null)} />
    </div>
  );
}

function Dot() {
  return <span className="h-0.5 w-0.5 rounded-full bg-text-faint" />;
}

function RenameRunModal({
  run,
  datasetId,
  onClose,
}: {
  run: RunSummary | null;
  datasetId?: string;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  useEffect(() => {
    if (run) setName(run.name ?? "");
  }, [run]);

  const save = useMutation({
    mutationFn: () => api.renameRun(run!.run_id, name.trim()),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["runs", datasetId] });
      qc.invalidateQueries({ queryKey: ["run", run!.run_id] });
      toast("Generation renamed", "success");
      onClose();
    },
    onError: (e: Error) => toast(e.message, "error"),
  });

  return (
    <Modal
      open={!!run}
      onClose={onClose}
      kicker="Generation"
      title="Rename generation"
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" disabled={!name.trim() || save.isPending} onClick={() => save.mutate()}>
            {save.isPending ? "Saving…" : "Save"}
          </Button>
        </>
      }
    >
      <Field label="Name" hint="A short, memorable label for this run.">
        <TextInput autoFocus value={name} onChange={(e) => setName(e.target.value)} placeholder="baseline-v1" />
      </Field>
    </Modal>
  );
}

/** Right-side drawer wrapper for the Canvas. */
export function GenerationsDrawer({
  open,
  onClose,
  datasetId,
}: {
  open: boolean;
  onClose: () => void;
  datasetId?: string;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-40 flex animate-fade-in justify-end">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-[2px]" onClick={onClose} aria-hidden />
      <div className="relative z-10 flex h-full w-full max-w-lg animate-slide-up flex-col border-l border-border bg-bg shadow-pop">
        <div className="flex items-center justify-between border-b border-border bg-surface-1 px-5 py-4">
          <div>
            <Kicker>History</Kicker>
            <div className="font-display text-lg font-semibold tracking-tight">Generations</div>
          </div>
          <button onClick={onClose} className="ring-focus rounded-control p-1 text-text-faint hover:bg-surface-2 hover:text-text" aria-label="Close">
            <X size={18} />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-auto p-4">
          <GenerationsPanel datasetId={datasetId} dense />
        </div>
      </div>
    </div>
  );
}
