import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Check,
  Code2,
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
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button, CopyableHash, IconButton, Segmented, Spinner } from "@/components/ui";
import { Field, Modal, TextInput } from "@/components/Modal";
import { Inspector } from "@/components/Inspector";
import { TableCanvas } from "@/components/TableCanvas";
import { CausalGraphEditor } from "@/components/CausalGraphEditor";
import { CausalInspector, type CausalSelection } from "@/components/CausalInspector";
import { SpecDrawer } from "@/components/SpecDrawer";
import { GenerationsDrawer } from "@/components/GenerationsPanel";
import { api, ApiError } from "@/lib/api";
import { getCausal, reconcileDerived } from "@/lib/causal";
import { starterFeature } from "@/lib/specDefaults";
import { useSpecHistory } from "@/lib/useHistory";
import { useChrome } from "@/store/chrome";
import { toast } from "@/store/toast";
import { clsx } from "@/lib/clsx";
import type { CausalGraph, Feature, Spec } from "@/lib/types";

export function Canvas() {
  const { id } = useParams<{ id: string }>();
  const nav = useNavigate();
  const setCrumbs = useChrome((s) => s.setCrumbs);

  const { data: dataset, isLoading } = useQuery({
    queryKey: ["dataset", id],
    queryFn: () => api.getDataset(id!),
    enabled: !!id,
  });

  const [selected, setSelected] = useState<string | null>(null);
  const [view, setView] = useState<"table" | "graph">("table");
  const [causalSel, setCausalSel] = useState<CausalSelection>(null);
  const [saved, setSaved] = useState(true);
  const [showPreview, setShowPreview] = useState(true);
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [genDrawerOpen, setGenDrawerOpen] = useState(false);
  const [generateOpen, setGenerateOpen] = useState(false);
  const [validation, setValidation] = useState<{ ok: boolean; message?: string; locator?: string | null } | null>(null);
  const [loaded, setLoaded] = useState(false);

  const save = useMutation({
    mutationFn: (next: Spec) => api.saveSpec(id!, next),
    onSuccess: () => setSaved(true),
  });

  const persist = useCallback(
    (next: Spec) => {
      setSaved(false);
      setValidation(null);
      save.mutate(next);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [id],
  );

  const hist = useSpecHistory(persist);
  const spec = hist.spec;

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
    mutationFn: async (name: string) => {
      const latest = hist.flush() ?? spec!;
      await save.mutateAsync(latest);
      return api.createRun(id!, { name });
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
    hist.set({ ...spec, features, causal });
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
    hist.set(next);
    if (selected === name) setSelected(Object.keys(features)[0] ?? null);
    if (causalSel?.kind === "node" && causalSel.name === name) setCausalSel(null);
    toast(`Deleted "${name}"`);
  }

  function reorder(names: string[]) {
    hist.set({ ...spec!, features: Object.fromEntries(names.map((n) => [n, spec!.features[n]])) });
  }

  function applyCausal(nextCausal: CausalGraph) {
    hist.set(reconcileDerived(spec!, nextCausal));
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
          <span className="flex items-center gap-1.5 text-xs text-text-faint">
            {saved ? <Check size={13} className="text-success" /> : <Spinner />}
            {saved ? "autosaved" : "saving…"}
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
          {view === "graph" ? (
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
          <div className="pointer-events-none absolute right-3 top-3 flex flex-wrap justify-end gap-2">
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
          {view === "graph" ? (
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
        pending={generate.isPending}
        onClose={() => setGenerateOpen(false)}
        onConfirm={(name) => generate.mutate(name)}
      />
    </div>
  );
}

function GenerateModal({
  open,
  defaultName,
  pending,
  onClose,
  onConfirm,
}: {
  open: boolean;
  defaultName: string;
  pending: boolean;
  onClose: () => void;
  onConfirm: (name: string) => void;
}) {
  const [name, setName] = useState("");

  useEffect(() => {
    if (open) {
      const stamp = new Date().toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
      setName(`${defaultName} · ${stamp}`);
    }
  }, [open, defaultName]);

  return (
    <Modal
      open={open}
      onClose={onClose}
      kicker="New generation"
      title="Name this generation"
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" disabled={!name.trim() || pending} onClick={() => onConfirm(name.trim())}>
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
            if (e.key === "Enter" && name.trim() && !pending) onConfirm(name.trim());
          }}
          placeholder="baseline-v1"
        />
      </Field>
    </Modal>
  );
}
