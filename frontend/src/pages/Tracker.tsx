import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Loader2, Terminal, XCircle } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button, CopyableHash, Kicker } from "@/components/ui";
import { StageStepper, type StageStatus } from "@/components/StageStepper";
import { api } from "@/lib/api";
import { subscribeRun } from "@/lib/runSocket";
import { useChrome } from "@/store/chrome";
import { clsx } from "@/lib/clsx";
import type { RunEvent } from "@/lib/types";

export function Tracker() {
  const { id, runId } = useParams<{ id: string; runId: string }>();
  const nav = useNavigate();
  const setCrumbs = useChrome((s) => s.setCrumbs);

  const { data: run } = useQuery({
    queryKey: ["run", runId],
    queryFn: () => api.getRun(runId!),
    enabled: !!runId,
  });

  const [statuses, setStatuses] = useState<Record<string, StageStatus>>({});
  const [logs, setLogs] = useState<string[]>([]);
  const [pct, setPct] = useState(0);
  const [terminal, setTerminal] = useState<RunEvent | null>(null);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => setCrumbs([{ label: "Datasets", to: "/datasets" }, { label: "Generate" }]), [setCrumbs]);

  useEffect(() => {
    if (!runId) return;
    const dispose = subscribeRun(runId, (ev) => {
      if (ev.type === "stage") {
        setStatuses((s) => ({ ...s, [ev.stage]: ev.status === "done" ? "done" : "running" }));
        setPct(ev.pct);
      } else if (ev.type === "log") {
        setLogs((l) => [...l, `[${ev.level.toUpperCase()}] ${ev.message}`]);
      } else if (ev.type === "completed") {
        setStatuses((s) => ({ ...s, packaging: "done" }));
        setPct(100);
        setTerminal(ev);
      } else if (ev.type === "failed") {
        setStatuses((s) => ({ ...s, [ev.stage]: "failed" }));
        setTerminal(ev);
        setLogs((l) => [...l, `[ERROR] ${ev.message}`]);
      } else if (ev.type === "cancelled") {
        setTerminal(ev);
      }
    });
    return dispose;
  }, [runId]);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logs]);

  const done = terminal?.type === "completed";
  const failed = terminal?.type === "failed";
  const cancelled = terminal?.type === "cancelled";

  const StatusIcon = done ? CheckCircle2 : failed || cancelled ? XCircle : Loader2;
  const statusTone = done ? "text-success" : failed ? "text-hazard" : cancelled ? "text-text-faint" : "text-primary";

  return (
    <div className="flex h-full flex-col px-8 py-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <StatusIcon size={26} className={clsx(statusTone, !terminal && "animate-spin")} />
          <div>
            <Kicker>{done ? "Complete" : failed ? "Failed" : cancelled ? "Cancelled" : "Generating"}</Kicker>
            <h1 className="font-display text-2xl font-semibold tracking-tight">
              {done ? "Generation complete" : failed ? "Generation failed" : "Run in progress"}
            </h1>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          {run && <CopyableHash label="seed" value={run.seed} />}
          {run && <CopyableHash label="spec_id" value={run.spec_id} />}
        </div>
      </div>

      {/* Progress bar */}
      <div className="mt-5 flex items-center gap-3">
        <div className="h-1.5 flex-1 overflow-hidden rounded-pill bg-surface-2">
          <div
            className={clsx("h-full rounded-pill transition-[width] duration-300", failed ? "bg-hazard" : "bg-primary")}
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="font-mono text-sm tnum text-text-muted">{pct}%</span>
      </div>

      {/* Body: steps | console — fills remaining height, no page scroll */}
      <div className="mt-5 grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[minmax(300px,380px)_1fr]">
        <div className="flex min-h-0 flex-col rounded-card border border-border bg-surface-1 shadow-card">
          <div className="border-b border-border px-4 py-2.5">
            <Kicker>Pipeline stages</Kicker>
          </div>
          <div className="min-h-0 flex-1 overflow-auto p-3">
            <StageStepper statuses={statuses} />
          </div>
        </div>

        <div className="flex min-h-0 flex-col overflow-hidden rounded-card border border-border bg-[#15140f] shadow-card">
          <div className="flex items-center gap-2 border-b border-white/10 px-4 py-2.5 text-white/70">
            <Terminal size={14} />
            <span className="kicker !text-white/40">Console</span>
            <span className="ml-auto font-mono text-xs text-white/40">{logs.length} lines</span>
          </div>
          <div
            ref={logRef}
            className="min-h-0 flex-1 overflow-auto p-4 font-mono text-xs leading-relaxed text-white/75"
          >
            {logs.length === 0 ? (
              <span className="text-white/30">waiting for output…</span>
            ) : (
              logs.map((l, i) => (
                <div key={i} className={l.startsWith("[ERROR]") ? "text-hazard" : ""}>
                  <span className="select-none text-white/25">{String(i + 1).padStart(2, "0")} </span>
                  {l}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Pinned action bar */}
      <div className="mt-5 flex items-center justify-between gap-3">
        <p className="text-sm text-text-faint">
          Reproducible from <span className="font-mono">spec_hash + seed</span> — identical bytes, forever.
        </p>
        <div className="flex gap-3">
          {!terminal && (
            <Button variant="destructive" onClick={() => runId && api.cancelRun(runId)}>
              Cancel run
            </Button>
          )}
          {done && (
            <Button variant="primary" onClick={() => nav(`/datasets/${id}/results/${runId}`)}>
              View Results →
            </Button>
          )}
          {failed && (
            <>
              <Button onClick={() => nav(`/datasets/${id}`)}>Edit spec</Button>
              <Button variant="primary" onClick={() => nav(`/datasets/${id}`)}>
                Retry
              </Button>
            </>
          )}
          {cancelled && <Button onClick={() => nav(`/datasets/${id}`)}>Back to Canvas</Button>}
        </div>
      </div>
    </div>
  );
}
