import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Check,
  Code2,
  Droplets,
  Eye,
  EyeOff,
  GitBranch,
  History,
  PanelRightClose,
  PanelRightOpen,
  Play,
  Redo2,
  Table2,
  Undo2,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button, CopyableHash, IconButton, Segmented, Spinner } from "@/components/ui";
import { Field, Modal, TextInput } from "@/components/Modal";
import { Inspector } from "@/components/Inspector";
import { TableCanvas } from "@/components/TableCanvas";
import { CausalGraphEditor } from "@/components/CausalGraphEditor";
import { CausalInspector, type CausalSelection } from "@/components/CausalInspector";
import { FailureConfigurator } from "@/components/FailureConfigurator";
import { FailureInspector } from "@/components/FailureInspector";
import { SpecDrawer } from "@/components/SpecDrawer";
import { GenerationsDrawer } from "@/components/GenerationsPanel";
import { api, ApiError } from "@/lib/api";
import { getCausal, reconcileDerived } from "@/lib/causal";
import { reconcileFailures } from "@/lib/failures";
import { loadLayout, saveLayout } from "@/lib/viewLayout";
import { starterFeature } from "@/lib/specDefaults";
import { useSpecHistory } from "@/lib/useHistory";
import { useChrome } from "@/store/chrome";
import { toast } from "@/store/toast";
import { clsx } from "@/lib/clsx";
import type { CausalGraph, Dataset, Failure, Feature, Spec } from "@/lib/types";

export function Canvas() {
  const { id } = useParams<{ id: string }>();
  const nav = useNavigate();
  const setCrumbs = useChrome((s) => s.setCrumbs);
  const qc = useQueryClient();

  const { data: dataset, isLoading } = useQuery({
    queryKey: ["dataset", id],
    queryFn: () => api.getDataset(id!),
    enabled: !!id,
  });

  const [selected, setSelected] = useState<string | null>(null);
  const [view, setView] = useState<"table" | "graph" | "failures">("table");
  const [causalSel, setCausalSel] = useState<CausalSelection>(null);
  const [failureSel, setFailureSel] = useState<number | null>(null);
  const [saved, setSaved] = useState(true);
  const [saveErr, setSaveErr] = useState<{ message: string; locator?: string | null } | null>(null);
  const [showPreview, setShowPreview] = useState(true);
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [genDrawerOpen, setGenDrawerOpen] = useState(false);
  const [generateOpen, setGenerateOpen] = useState(false);
  const [validation, setValidation] = useState<{ ok: boolean; message?: string; locator?: string | null } | null>(null);
  const [loaded, setLoaded] = useState(false);

  const save = useMutation({
    mutationFn: (next: Spec) => api.saveSpec(id!, next),
    // Keep the dataset cache in sync with the just-saved spec. Without this, a
    // remount (navigating back to the Canvas) would re-load the *stale* cached
    // spec and silently lose edits — and generate from an out-of-date spec.
    onError: (e: ApiError) => setSaveErr({ message: e.message, locator: e.locator }),
    onSuccess: (res, saved) => {
      setSaved(true);
      setSaveErr(null);
      qc.setQueryData<Dataset>(["dataset", id], (old) =>
        old?.current_spec
          ? {
              ...old,
              current_spec: {
                ...old.current_spec,
                body: saved,
                spec_hash: res.spec_hash,
                version: res.version,
                spec_id: res.spec_id,
              },
              updated_at: new Date().toISOString(),
            }
          : old,
      );
    },
  });

  const persist = useCallback(
    (next: Spec) => {
      setSaved(false);
      setSaveErr(null);
      setValidation(null);
      save.mutate(next);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [id],
  );

  const hist = useSpecHistory(persist);
  const spec = hist.spec;

  // Commit any pending (debounced) edit when the Canvas unmounts, so navigating
  // away within the autosave window still persists the last change.
  const flushRef = useRef(hist.flush);
  flushRef.current = hist.flush;
  useEffect(() => () => void flushRef.current(), []);

  // Re-arm the loader when switching datasets (React Router reuses this component
  // across :id changes, so without this it would keep showing the old spec).
  useEffect(() => {
    setLoaded(false);
    setSelected(null);
    setFailureSel(null);
  }, [id]);

  useEffect(() => {
    if (dataset?.current_spec?.body && !loaded) {
      hist.load(dataset.current_spec.body);
      setSelected(Object.keys(dataset.current_spec.body.features)[0] ?? null);
      setLoaded(true);
    }
  }, [dataset, loaded, hist]);

  useEffect(() => {
    if (spec) setCrumbs([{ label: "Datasets", to: "/datasets" }, { label: spec.name }, { label: "Canvas" }]);
  }, [spec, setCrumbs]);

  // Undo / redo keyboard shortcuts.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement;
      const typing = ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName) || el.isContentEditable;
      if (typing || !(e.metaKey || e.ctrlKey)) return;
      if (e.key.toLowerCase() === "z") {
        e.preventDefault();
        if (e.shiftKey) hist.redo();
        else hist.undo();
      } else if (e.key.toLowerCase() === "y") {
        e.preventDefault();
        hist.redo();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [hist]);

  const validate = useMutation({
    mutationFn: () => api.validate(spec!),
    onSuccess: (r) => setValidation({ ok: true, message: `Valid · ${r.spec_hash.slice(0, 12)}…` }),
    onError: (e: ApiError) => setValidation({ ok: false, message: e.message, locator: e.locator }),
  });

  const generate = useMutation({
    mutationFn: async ({ name, applyFailures }: { name: string; applyFailures: boolean }) => {
      const full = hist.flush() ?? spec!;
      const hasFailures = (full.failures?.length ?? 0) > 0;

      // Freeze the current graph arrangement under the run's id, so its Results
      // graph reflects the layout *at generation time* — later edits to the
      // Canvas graph won't retroactively change a past run's view.
      const snapshotLayout = (runId: string) =>
        saveLayout(runId, "graph-nodes", loadLayout(id!, "graph-nodes", {}));

      // "Generate without failures": snapshot a failures-stripped spec for this
      // one run (the run is an immutable snapshot), then restore the full spec so
      // the Canvas keeps its failure config. This runs a genuinely clean pipeline
      // — no injected output, no failures report — without losing any setup.
      if (hasFailures && !applyFailures) {
        const stripped: Spec = {
          ...full,
          failures: [],
          export: { ...(full.export ?? {}), versions: exportVersions().filter((v) => v !== "injected") },
        };
        await save.mutateAsync(stripped);
        try {
          const run = await api.createRun(id!, { name });
          snapshotLayout(run.run_id);
          return run;
        } finally {
          await save.mutateAsync(full); // restore the configured spec
        }
      }

      // With failures: make sure the injected variant is exported so Comparison
      // works. The clean dataset is always produced too.
      let latest = full;
      if (hasFailures) {
        const versions = Array.from(new Set([...exportVersions(), "injected"]));
        latest = { ...full, export: { ...(full.export ?? {}), versions } };
        hist.set(latest);
      }
      await save.mutateAsync(latest);
      const run = await api.createRun(id!, { name });
      snapshotLayout(run.run_id);
      return run;
    },
    onSuccess: (r) => nav(`/datasets/${id}/run/${r.run_id}`),
    onError: (e: ApiError) => {
      setGenerateOpen(false);
      setValidation({ ok: false, message: e.message, locator: e.locator });
    },
  });

  const featureNames = useMemo(() => (spec ? Object.keys(spec.features) : []), [spec]);

  if (isLoading || !spec) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  function renameFeature(oldName: string, nextName: string) {
    if (!spec || oldName === nextName) return;
    const features = Object.fromEntries(
      Object.entries(spec.features).map(([k, v]) => [k === oldName ? nextName : k, v]),
    );
    const c = spec.causal;
    const causal: CausalGraph | null | undefined = c
      ? {
          ...c,
          edges: c.edges.map((e) => ({
            ...e,
            from: e.from === oldName ? nextName : e.from,
            to: e.to === oldName ? nextName : e.to,
          })),
          noise: c.noise
            ? Object.fromEntries(Object.entries(c.noise).map(([k, v]) => [k === oldName ? nextName : k, v]))
            : c.noise,
          interventions: c.interventions?.map((iv) => ({
            do: Object.fromEntries(Object.entries(iv.do).map(([k, v]) => [k === oldName ? nextName : k, v])),
          })),
        }
      : c;
    const failures = reconcileFailures(spec.failures, { rename: { from: oldName, to: nextName } });
    hist.set({ ...spec, features, causal, failures });
    if (selected === oldName) setSelected(nextName);
    if (causalSel?.kind === "node" && causalSel.name === oldName) setCausalSel({ kind: "node", name: nextName });
  }

  function setFeature(name: string, f: Feature) {
    hist.set({ ...spec!, features: { ...spec!.features, [name]: f } });
  }

  function changeType(name: string, t: Feature["type"]) {
    const defaults: Record<Feature["type"], Feature> = {
      numeric: starterFeature(),
      categorical: { type: "categorical", categories: ["a", "b", "c"] },
      boolean: { type: "boolean", rate: 0.5 },
      datetime: { type: "datetime", start: "2020-01-01", end: "2024-12-31", granularity: "day" },
      text: { type: "text", generator: "lorem", length: { min: 5, max: 30 } },
    };
    setFeature(name, defaults[t]);
  }

  function addColumn() {
    const existing = new Set(featureNames);
    let n = featureNames.length + 1;
    let name = `feature_${n}`;
    while (existing.has(name)) name = `feature_${++n}`;
    hist.set({ ...spec!, features: { ...spec!.features, [name]: starterFeature() } });
    setSelected(name);
    if (view === "graph") setCausalSel({ kind: "node", name });
  }

  function deleteColumn(name: string) {
    if (!spec) return;
    if (featureNames.length <= 1) {
      toast("A dataset needs at least one column", "error");
      return;
    }
    const features = Object.fromEntries(Object.entries(spec.features).filter(([k]) => k !== name));
    const c = spec.causal;
    let next: Spec = { ...spec, features };
    if (c) {
      const causal: CausalGraph = {
        ...c,
        edges: c.edges.filter((e) => e.from !== name && e.to !== name),
        noise: c.noise ? Object.fromEntries(Object.entries(c.noise).filter(([k]) => k !== name)) : c.noise,
        interventions: c.interventions
          ?.map((iv) => ({ do: Object.fromEntries(Object.entries(iv.do).filter(([k]) => k !== name)) }))
          .filter((iv) => Object.keys(iv.do).length > 0),
      };
      next = reconcileDerived(next, causal);
    }
    next = { ...next, failures: reconcileFailures(next.failures, { remove: name }) };
    hist.set(next);
    if (selected === name) setSelected(Object.keys(features)[0] ?? null);
    if (causalSel?.kind === "node" && causalSel.name === name) setCausalSel(null);
    setFailureSel(null);
    toast(`Deleted "${name}"`);
  }

  function reorder(names: string[]) {
    hist.set({ ...spec!, features: Object.fromEntries(names.map((n) => [n, spec!.features[n]])) });
  }

  function applyCausal(nextCausal: CausalGraph) {
    hist.set(reconcileDerived(spec!, nextCausal));
  }

  function exportVersions(): string[] {
    const v = (spec!.export as { versions?: string[] } | null | undefined)?.versions;
    return Array.isArray(v) && v.length ? v : ["clean"];
  }
  const exportInjected = exportVersions().includes("injected");

  function setExportVersions(versions: string[]) {
    const exp = { ...(spec!.export ?? {}), versions };
    hist.set({ ...spec!, export: exp });
  }

  function setFailures(failures: Failure[]) {
    const wasEmpty = (spec!.failures?.length ?? 0) === 0;
    let next: Spec = { ...spec!, failures };
    // Adding the *first* failure auto-enables the injected export so Comparison
    // works — but a later manual toggle-off is respected (we only nudge once).
    if (wasEmpty && failures.length && !exportInjected) {
      const versions = Array.from(new Set([...exportVersions(), "injected"]));
      next = { ...next, export: { ...(spec!.export ?? {}), versions } };
    }
    hist.set(next);
  }

  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3 border-b border-border bg-surface-1 px-6 py-2.5">
        <Segmented
          value={view}
          onChange={setView}
          options={[
            { value: "table", label: <><Table2 size={14} /> Table</> },
            { value: "graph", label: <><GitBranch size={14} /> Graph</> },
            {
              value: "failures",
              label: (
                <>
                  <Droplets size={14} /> Failures
                  {(spec.failures?.length ?? 0) > 0 && (
                    <span className="ml-0.5 rounded-pill bg-primary px-1.5 text-[10px] font-semibold leading-tight text-white tnum">
                      {spec.failures!.length}
                    </span>
                  )}
                </>
              ),
            },
          ]}
        />

        <div className="flex items-center rounded-control border border-border">
          <IconButton title="Undo (⌘/Ctrl+Z)" disabled={!hist.canUndo} onClick={hist.undo} className="rounded-r-none">
            <Undo2 size={15} />
          </IconButton>
          <span className="h-5 w-px bg-border" />
          <IconButton title="Redo (⌘/Ctrl+Shift+Z)" disabled={!hist.canRedo} onClick={hist.redo} className="rounded-l-none">
            <Redo2 size={15} />
          </IconButton>
        </div>

        {view === "table" && (
          <IconButton
            title={showPreview ? "Hide data preview" : "Show data preview"}
            active={showPreview}
            onClick={() => setShowPreview((v) => !v)}
          >
            {showPreview ? <Eye size={15} /> : <EyeOff size={15} />}
          </IconButton>
        )}

        <div className="ml-auto flex items-center gap-2">
          <span
            className={clsx(
              "flex items-center gap-1.5 text-xs",
              saveErr ? "text-hazard" : "text-text-faint",
            )}
            title={saveErr ? `${saveErr.message}${saveErr.locator ? ` @ ${saveErr.locator}` : ""}` : undefined}
          >
            {saveErr ? (
              <AlertTriangle size={13} />
            ) : saved ? (
              <Check size={13} className="text-success" />
            ) : (
              <Spinner />
            )}
            {saveErr ? "can’t save — fix errors" : saved ? "autosaved" : "saving…"}
          </span>
          <Button onClick={() => setGenDrawerOpen(true)}>
            <History size={15} /> Generations
          </Button>
          <Button onClick={() => setDrawerOpen(true)}>
            <Code2 size={15} /> View Spec
          </Button>
          <Button onClick={() => validate.mutate()}>Validate</Button>
          <Button variant="primary" disabled={generate.isPending} onClick={() => setGenerateOpen(true)}>
            <Play size={15} /> Generate
          </Button>
          <IconButton
            title={inspectorOpen ? "Hide inspector" : "Show inspector"}
            onClick={() => setInspectorOpen((v) => !v)}
          >
            {inspectorOpen ? <PanelRightClose size={16} /> : <PanelRightOpen size={16} />}
          </IconButton>
        </div>
      </div>

      {validation && (
        <div
          className={clsx(
            "px-6 py-2 text-sm",
            validation.ok ? "bg-success-tint text-success" : "bg-hazard-tint text-hazard",
          )}
        >
          {validation.ok ? "✓ " : "✗ "}
          {validation.message}
          {validation.locator && <span className="ml-2 font-mono text-xs">@ {validation.locator}</span>}
        </div>
      )}

      {/* Body */}
      <div className="grid min-h-0 flex-1 grid-cols-1" style={{ gridTemplateColumns: inspectorOpen ? "1fr 372px" : "1fr 0px" }}>
        <div className="relative min-h-0">
          {view === "failures" ? (
            <FailureConfigurator
              spec={spec}
              selected={failureSel}
              onSelect={setFailureSel}
              onChange={setFailures}
              exportInjected={exportInjected}
              onExportInjected={(on) =>
                setExportVersions(
                  on
                    ? Array.from(new Set([...exportVersions(), "injected"]))
                    : exportVersions().filter((v) => v !== "injected"),
                )
              }
            />
          ) : view === "graph" ? (
            <CausalGraphEditor
              spec={spec}
              datasetId={id}
              selection={causalSel}
              onSelect={setCausalSel}
              onCausalChange={applyCausal}
              onDeleteColumn={deleteColumn}
            />
          ) : (
            <TableCanvas
              spec={spec}
              datasetId={id}
              selected={selected}
              showPreview={showPreview}
              onSelect={setSelected}
              onRename={renameFeature}
              onDelete={deleteColumn}
              onReorder={reorder}
              onAddColumn={addColumn}
            />
          )}

          {/* Floating spec hashes */}
          <div
            className={clsx(
              "pointer-events-none absolute right-3 top-3 flex flex-wrap justify-end gap-2",
              view === "failures" && "hidden",
            )}
          >
            <div className="pointer-events-auto">
              <CopyableHash label="rows" value={spec.rows.toLocaleString()} />
            </div>
            {dataset?.current_spec && (
              <div className="pointer-events-auto">
                <CopyableHash label="spec_hash" value={dataset.current_spec.spec_hash} />
              </div>
            )}
          </div>
        </div>

        <aside
          className={clsx(
            "min-h-0 overflow-hidden border-l border-border bg-surface-1 transition-opacity",
            inspectorOpen ? "opacity-100" : "pointer-events-none opacity-0",
          )}
        >
          {view === "failures" ? (
            failureSel != null && spec.failures?.[failureSel] ? (
              <FailureInspector
                failure={spec.failures[failureSel]}
                index={failureSel}
                spec={spec}
                onChange={(f) =>
                  setFailures(spec.failures!.map((x, j) => (j === failureSel ? f : x)))
                }
                onDelete={() => {
                  setFailures(spec.failures!.filter((_, j) => j !== failureSel));
                  setFailureSel(null);
                }}
              />
            ) : (
              <div className="p-6 text-sm text-text-faint">
                Select a failure step to configure it, or add one to begin.
              </div>
            )
          ) : view === "graph" ? (
            <CausalInspector
              spec={spec}
              causal={getCausal(spec)}
              selection={causalSel}
              onCausalChange={applyCausal}
              onSelect={setCausalSel}
            />
          ) : selected && spec.features[selected] ? (
            <Inspector
              name={selected}
              feature={spec.features[selected]}
              siblingNames={featureNames.filter((n) => n !== selected)}
              onRename={(next) => renameFeature(selected, next)}
              onChange={(f) => setFeature(selected, f)}
              onChangeType={(t) => changeType(selected, t)}
              onDelete={() => deleteColumn(selected)}
              locatorError={
                validation && !validation.ok && validation.locator?.includes(selected)
                  ? validation.message
                  : null
              }
            />
          ) : (
            <div className="p-6 text-sm text-text-faint">Select a column to edit it.</div>
          )}
        </aside>
      </div>

      <SpecDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} spec={spec} />
      <GenerationsDrawer open={genDrawerOpen} onClose={() => setGenDrawerOpen(false)} datasetId={id} />
      <GenerateModal
        open={generateOpen}
        defaultName={spec.name}
        hasFailures={(spec.failures?.length ?? 0) > 0}
        defaultApply={exportInjected}
        pending={generate.isPending}
        onClose={() => setGenerateOpen(false)}
        onConfirm={(name, applyFailures) => generate.mutate({ name, applyFailures })}
      />
    </div>
  );
}

function GenerateModal({
  open,
  defaultName,
  hasFailures,
  defaultApply,
  pending,
  onClose,
  onConfirm,
}: {
  open: boolean;
  defaultName: string;
  hasFailures: boolean;
  defaultApply: boolean;
  pending: boolean;
  onClose: () => void;
  onConfirm: (name: string, applyFailures: boolean) => void;
}) {
  const [name, setName] = useState("");
  const [applyFailures, setApplyFailures] = useState(true);

  useEffect(() => {
    if (open) {
      const stamp = new Date().toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
      setName(`${defaultName} · ${stamp}`);
      setApplyFailures(defaultApply);
    }
  }, [open, defaultName, defaultApply]);

  return (
    <Modal
      open={open}
      onClose={onClose}
      kicker="New generation"
      title="Name this generation"
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" disabled={!name.trim() || pending} onClick={() => onConfirm(name.trim(), applyFailures)}>
            <Play size={15} /> {pending ? "Starting…" : "Generate"}
          </Button>
        </>
      }
    >
      <Field label="Generation name" hint="Required — every generation is named so you can find it later.">
        <TextInput
          autoFocus
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && name.trim() && !pending) onConfirm(name.trim(), applyFailures);
          }}
          placeholder="baseline-v1"
        />
      </Field>

      {hasFailures && (
        <label className="mt-4 flex cursor-pointer items-start gap-2.5 rounded-control border border-border bg-surface-2 px-3.5 py-3">
          <input
            type="checkbox"
            checked={applyFailures}
            onChange={(e) => setApplyFailures(e.target.checked)}
            className="mt-0.5 h-4 w-4 accent-[var(--primary)]"
          />
          <span className="text-sm">
            <span className="font-medium text-text">Inject failures</span>
            <span className="mt-0.5 block text-xs text-text-faint">
              {applyFailures
                ? "Produces both the clean baseline and the corrupted variant (with Comparison)."
                : "Produces the clean dataset only — failures stay configured but aren’t applied this run."}
            </span>
          </span>
        </label>
      )}
    </Modal>
  );
}
