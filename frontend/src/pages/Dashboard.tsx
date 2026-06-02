import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, MoreHorizontal, Pencil, Plus, Search, Sparkles, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Button,
  Card,
  EmptyState,
  IconButton,
  Kicker,
  Menu,
  MenuItem,
  Spinner,
  StatusBadge,
} from "@/components/ui";
import { Field, Modal, TextInput } from "@/components/Modal";
import { api } from "@/lib/api";
import { starterSpec } from "@/lib/specDefaults";
import { useChrome } from "@/store/chrome";
import { toast } from "@/store/toast";
import type { DatasetSummary } from "@/lib/types";

function fmtBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

export function Dashboard() {
  const qc = useQueryClient();
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const [creating, setCreating] = useState(false);
  const [renaming, setRenaming] = useState<DatasetSummary | null>(null);
  const setCrumbs = useChrome((s) => s.setCrumbs);

  useEffect(() => setCrumbs([{ label: "Datasets" }]), [setCrumbs]);

  const { data, isLoading } = useQuery({
    queryKey: ["datasets", q],
    queryFn: () => api.listDatasets(q || undefined),
  });

  const del = useMutation({
    mutationFn: (id: string) => api.deleteDataset(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["datasets"] });
      toast("Dataset deleted", "success");
    },
  });
  const dup = useMutation({
    mutationFn: (id: string) => api.duplicateDataset(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["datasets"] });
      toast("Dataset duplicated", "success");
    },
  });

  const items = data?.items ?? [];

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-6xl px-8 py-12">
        <div className="flex flex-wrap items-end justify-between gap-5">
          <div>
            <Kicker>Your laboratory</Kicker>
            <h1 className="mt-2 font-display text-[40px] font-semibold leading-none tracking-tight">
              Datasets
            </h1>
            <p className="mt-2.5 max-w-md text-sm text-text-muted">
              Design a dataset once, regenerate it identically forever from its spec and seed.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search
                size={15}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-faint"
              />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search datasets…"
                className="ring-focus w-52 rounded-control border border-border bg-surface-1 py-2.5 pl-9 pr-3 text-sm shadow-soft outline-none transition-colors focus:border-primary"
              />
            </div>
            <Button variant="primary" onClick={() => setCreating(true)}>
              <Plus size={16} /> Create Dataset
            </Button>
          </div>
        </div>

        <hr className="my-8 border-border" />

        {isLoading ? (
          <div className="flex justify-center py-24">
            <Spinner className="h-6 w-6" />
          </div>
        ) : items.length === 0 ? (
          <EmptyState
            kicker={q ? "No matches" : "Empty laboratory"}
            title={q ? `Nothing matches "${q}"` : "Nothing in the lab yet"}
          >
            {!q && (
              <Button variant="primary" onClick={() => setCreating(true)}>
                <Sparkles size={16} /> Create your first dataset
              </Button>
            )}
          </EmptyState>
        ) : (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((d) => (
              <DatasetCard
                key={d.dataset_id}
                d={d}
                onOpen={() => nav(`/datasets/${d.dataset_id}`)}
                onRename={() => setRenaming(d)}
                onDuplicate={() => dup.mutate(d.dataset_id)}
                onDelete={() => {
                  if (confirm(`Delete dataset "${d.name}"? This removes its runs and artifacts.`))
                    del.mutate(d.dataset_id);
                }}
              />
            ))}
          </div>
        )}
      </div>

      <CreateModal
        open={creating}
        onClose={() => setCreating(false)}
        onCreated={(id) => nav(`/datasets/${id}`)}
      />
      <RenameModal dataset={renaming} onClose={() => setRenaming(null)} />
    </div>
  );
}

function DatasetCard({
  d,
  onOpen,
  onRename,
  onDuplicate,
  onDelete,
}: {
  d: DatasetSummary;
  onOpen: () => void;
  onRename: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
}) {
  return (
    <Card className="group relative flex flex-col p-5 transition-all duration-200 hover:-translate-y-1 hover:border-border-strong hover:shadow-lift">
      <div className="flex items-start justify-between gap-2">
        <button onClick={onOpen} className="ring-focus min-w-0 rounded text-left">
          <h3 className="truncate font-display text-xl font-semibold leading-tight tracking-tight text-text transition-colors group-hover:text-primary">
            {d.name}
          </h3>
        </button>
        <div className="flex shrink-0 items-center gap-1.5">
          <StatusBadge status={d.status} />
          <Menu trigger={({ toggle }) => <IconButton onClick={toggle} className="h-7 w-7"><MoreHorizontal size={16} /></IconButton>}>
            {(close) => (
              <>
                <MenuItem icon={<Pencil size={14} />} onClick={() => { close(); onRename(); }}>
                  Rename
                </MenuItem>
                <MenuItem icon={<Copy size={14} />} onClick={() => { close(); onDuplicate(); }}>
                  Duplicate
                </MenuItem>
                <MenuItem icon={<Trash2 size={14} />} danger onClick={() => { close(); onDelete(); }}>
                  Delete
                </MenuItem>
              </>
            )}
          </Menu>
        </div>
      </div>
      {d.description && (
        <p className="mt-1.5 line-clamp-2 text-sm text-text-muted">{d.description}</p>
      )}

      <div className="mt-5 flex items-end justify-between">
        <div className="flex gap-6">
          <Metric label="Rows" value={d.rows != null ? d.rows.toLocaleString() : "—"} />
          <Metric label="Features" value={d.features != null ? String(d.features) : "—"} />
        </div>
        <div className="text-right">
          <div className="font-display text-2xl font-semibold tnum text-text">
            {d.compliance_score != null ? `${Math.round(d.compliance_score * 100)}%` : "—"}
          </div>
          <div className="kicker mt-0.5">Compliance</div>
        </div>
      </div>

      <button
        onClick={onOpen}
        className="ring-focus mt-5 w-full rounded-control border border-border bg-surface-1 py-2 text-sm font-medium text-text-muted transition-colors hover:border-primary hover:bg-primary-tint hover:text-primary"
      >
        Open Canvas →
      </button>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="font-mono text-sm tnum text-text">{value}</div>
      <div className="kicker mt-0.5">{label}</div>
    </div>
  );
}

function RenameModal({ dataset, onClose }: { dataset: DatasetSummary | null; onClose: () => void }) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (dataset) {
      setName(dataset.name);
      setDescription(dataset.description ?? "");
      setErr(null);
    }
  }, [dataset]);

  const save = useMutation({
    mutationFn: () => api.updateDataset(dataset!.dataset_id, { name, description: description || null }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["datasets"] });
      toast("Dataset renamed", "success");
      onClose();
    },
    onError: (e: Error) => setErr(e.message),
  });

  return (
    <Modal
      open={!!dataset}
      onClose={onClose}
      kicker="Edit details"
      title="Rename dataset"
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" disabled={!name || save.isPending} onClick={() => save.mutate()}>
            {save.isPending ? "Saving…" : "Save changes"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Name" hint="Slug-friendly: letters, numbers, _ and -.">
          <TextInput autoFocus value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label="Description (optional)">
          <TextInput value={description} onChange={(e) => setDescription(e.target.value)} />
        </Field>
        {err && <p className="text-sm text-hazard">{err}</p>}
      </div>
    </Modal>
  );
}

function CreateModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (id: string) => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [rows, setRows] = useState(10000);
  const [seed, setSeed] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      api.createDataset({
        name,
        description: description || undefined,
        spec: starterSpec(name, rows, seed ? Number(seed) : undefined),
      }),
    onSuccess: (ds) => {
      reset();
      onCreated(ds.dataset_id);
    },
    onError: (e: Error) => setErr(e.message),
  });

  function reset() {
    setName("");
    setDescription("");
    setRows(10000);
    setSeed("");
    setErr(null);
  }

  const sliderToRows = (v: number) => Math.round(1000 * Math.pow(1000, v / 100));
  const rowsToSlider = (r: number) => Math.round((Math.log(r / 1000) / Math.log(1000)) * 100);
  const estBytes = rows * 24;

  return (
    <Modal
      open={open}
      onClose={onClose}
      kicker="New experiment"
      title="Create dataset"
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" disabled={!name || create.isPending} onClick={() => create.mutate()}>
            {create.isPending ? "Creating…" : "Create & open Canvas"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Name" hint="Slug-friendly: letters, numbers, _ and -.">
          <TextInput autoFocus value={name} onChange={(e) => setName(e.target.value)} placeholder="fraud-demo" />
        </Field>
        <Field label="Description (optional)">
          <TextInput value={description} onChange={(e) => setDescription(e.target.value)} />
        </Field>
        <Field label={`Rows — ${rows.toLocaleString()}`} hint={`estimate · ~${fmtBytes(estBytes)} CSV`}>
          <input
            type="range"
            min={0}
            max={100}
            value={rowsToSlider(rows)}
            onChange={(e) => setRows(sliderToRows(Number(e.target.value)))}
            className="mt-2 w-full accent-[var(--primary)]"
          />
        </Field>
        <Field label="Seed (optional)" hint="Leave blank for a recorded deterministic seed.">
          <TextInput value={seed} onChange={(e) => setSeed(e.target.value.replace(/[^0-9]/g, ""))} placeholder="auto" />
        </Field>
        {err && <p className="text-sm text-hazard">{err}</p>}
      </div>
    </Modal>
  );
}
