import { AlertTriangle, ChevronDown, ChevronUp, Droplets, Plus, ShieldCheck, Trash2 } from "lucide-react";
import { Button, Kicker, Menu, MenuItem } from "./ui";
import { FailureIcon } from "./FailureBadges";
import {
  CATEGORY_ORDER,
  FAILURE_META,
  FAILURE_ORDER,
  defaultFailure,
  impactEstimate,
  summarizeFailure,
  validateFailureClient,
} from "@/lib/failures";
import { clsx } from "@/lib/clsx";
import type { Failure, FailureType, Spec } from "@/lib/types";

export function FailureConfigurator({
  spec,
  selected,
  onSelect,
  onChange,
  exportInjected,
  onExportInjected,
}: {
  spec: Spec;
  selected: number | null;
  onSelect: (i: number | null) => void;
  onChange: (failures: Failure[]) => void;
  exportInjected: boolean;
  onExportInjected: (on: boolean) => void;
}) {
  const failures = spec.failures ?? [];

  function add(type: FailureType) {
    const next = [...failures, defaultFailure(type, spec)];
    onChange(next);
    onSelect(next.length - 1);
  }
  function remove(i: number) {
    onChange(failures.filter((_, j) => j !== i));
    onSelect(null);
  }
  function move(i: number, dir: -1 | 1) {
    const j = i + dir;
    if (j < 0 || j >= failures.length) return;
    const next = [...failures];
    [next[i], next[j]] = [next[j], next[i]];
    onChange(next);
    onSelect(j);
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-2xl px-6 py-7">
        <div className="flex items-start justify-between gap-4">
          <div>
            <Kicker>Failure pipeline</Kicker>
            <h2 className="mt-1.5 font-display text-2xl font-semibold tracking-tight">
              Inject realistic data quality failures
            </h2>
            <p className="mt-2 max-w-lg text-sm text-text-muted">
              Corruptions apply in order, after a pristine baseline is captured. The clean dataset is
              always preserved alongside the injected one.
            </p>
          </div>
          <AddMenu onAdd={add} />
        </div>

        {/* Clean-baseline guarantee */}
        <div className="mt-5 flex items-center gap-2.5 rounded-control border border-success bg-success-tint px-3.5 py-2.5 text-sm text-success">
          <ShieldCheck size={16} className="shrink-0" />
          <span>
            The <strong>clean</strong> baseline is never modified — every failure runs on a copy, so you
            can always compare against the uncorrupted data.
          </span>
        </div>

        {failures.length === 0 ? (
          <Empty onAdd={add} />
        ) : (
          <>
            <ol className="mt-5 space-y-2.5">
              {failures.map((f, i) => (
                <FailureCard
                  key={i}
                  failure={f}
                  index={i}
                  total={failures.length}
                  active={selected === i}
                  rows={spec.rows}
                  error={validateFailureClient(f, spec)}
                  onSelect={() => onSelect(i)}
                  onMove={(dir) => move(i, dir)}
                  onRemove={() => remove(i)}
                />
              ))}
            </ol>

            {/* Export toggle */}
            <label className="mt-5 flex cursor-pointer items-start gap-2.5 rounded-control border border-border bg-surface-1 px-3.5 py-3">
              <input
                type="checkbox"
                checked={exportInjected}
                onChange={(e) => onExportInjected(e.target.checked)}
                className="mt-0.5 h-4 w-4 accent-[var(--primary)]"
              />
              <span className="text-sm">
                <span className="font-medium text-text">Export the corrupted variant</span>
                <span className="mt-0.5 block text-xs text-text-faint">
                  Writes <span className="font-mono">data.injected.csv</span> next to the clean output, and
                  unlocks the clean-vs-injected Comparison in Results. Recommended.
                </span>
              </span>
            </label>
          </>
        )}
      </div>
    </div>
  );
}

function FailureCard({
  failure,
  index,
  total,
  active,
  rows,
  error,
  onSelect,
  onMove,
  onRemove,
}: {
  failure: Failure;
  index: number;
  total: number;
  active: boolean;
  rows: number;
  error: string | null;
  onSelect: () => void;
  onMove: (dir: -1 | 1) => void;
  onRemove: () => void;
}) {
  const meta = FAILURE_META[failure.type];
  const impact = impactEstimate(failure, rows);

  return (
    <li
      onClick={onSelect}
      className={clsx(
        "ring-focus group relative cursor-pointer rounded-card border bg-surface-1 p-3.5 shadow-card transition-all",
        active ? "border-primary ring-1 ring-primary" : "border-border hover:border-border-strong",
      )}
    >
      <div className="flex items-center gap-3">
        {/* order index */}
        <div className="flex flex-col items-center gap-0.5">
          <span className="font-mono text-[11px] text-text-faint tnum">{index + 1}</span>
        </div>

        {/* icon */}
        <span
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-control"
          style={{ color: meta.accent, background: `color-mix(in srgb, ${meta.accent} 14%, transparent)` }}
        >
          <FailureIcon type={failure.type} size={17} />
        </span>

        {/* title + summary */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate font-medium text-text">{meta.label}</span>
            {error && (
              <span title={error} className="shrink-0 text-warning">
                <AlertTriangle size={13} />
              </span>
            )}
          </div>
          <div className="mt-0.5 truncate font-mono text-xs text-text-muted">{summarizeFailure(failure)}</div>
        </div>

        {/* impact metric */}
        {impact.metric && (
          <span
            className="hidden shrink-0 rounded-pill px-2 py-0.5 font-mono text-[11px] font-semibold sm:inline"
            style={{ color: meta.accent, background: `color-mix(in srgb, ${meta.accent} 12%, transparent)` }}
          >
            {impact.metric}
          </span>
        )}

        {/* controls */}
        <div
          className="flex items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            disabled={index === 0}
            onClick={() => onMove(-1)}
            title="Move earlier"
            className="ring-focus rounded p-1 text-text-faint hover:bg-surface-2 hover:text-text disabled:opacity-30"
          >
            <ChevronUp size={15} />
          </button>
          <button
            disabled={index === total - 1}
            onClick={() => onMove(1)}
            title="Move later"
            className="ring-focus rounded p-1 text-text-faint hover:bg-surface-2 hover:text-text disabled:opacity-30"
          >
            <ChevronDown size={15} />
          </button>
          <button
            onClick={onRemove}
            title="Remove"
            className="ring-focus rounded p-1 text-text-faint hover:bg-hazard-tint hover:text-hazard"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>
    </li>
  );
}

function AddMenu({ onAdd }: { onAdd: (t: FailureType) => void }) {
  return (
    <Menu
      align="right"
      trigger={({ toggle }) => (
        <Button variant="primary" onClick={toggle}>
          <Plus size={15} /> Add failure
        </Button>
      )}
    >
      {(close) => (
        <div className="w-[270px]">
          {CATEGORY_ORDER.map((cat) => (
            <div key={cat} className="mb-1 last:mb-0">
              <div className="px-2.5 pb-1 pt-1.5 text-[10px] font-semibold uppercase tracking-wider text-text-faint">
                {cat}
              </div>
              {FAILURE_ORDER.filter((t) => FAILURE_META[t].category === cat).map((t) => {
                const meta = FAILURE_META[t];
                return (
                  <MenuItem
                    key={t}
                    icon={
                      <span style={{ color: meta.accent }}>
                        <FailureIcon type={t} size={15} />
                      </span>
                    }
                    onClick={() => {
                      onAdd(t);
                      close();
                    }}
                  >
                    <span title={meta.blurb} className="block truncate whitespace-nowrap text-text">
                      {meta.label}
                    </span>
                  </MenuItem>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </Menu>
  );
}

function Empty({ onAdd }: { onAdd: (t: FailureType) => void }) {
  return (
    <div className="dotgrid mt-5 flex flex-col items-center justify-center rounded-card border border-dashed border-border p-12 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-surface-2 text-text-faint">
        <Droplets size={22} />
      </span>
      <h3 className="mt-4 font-display text-xl font-semibold">No failures yet</h3>
      <p className="mt-1.5 max-w-sm text-sm text-text-muted">
        Add missingness, label/feature noise, distribution drift, or a leakage trap to stress-test
        models against realistic, imperfect data.
      </p>
      <div className="mt-5">
        <AddMenu onAdd={onAdd} />
      </div>
    </div>
  );
}
