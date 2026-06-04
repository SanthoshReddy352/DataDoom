import { useQuery } from "@tanstack/react-query";
import { Boxes, Plug, Puzzle, Shuffle, SlidersHorizontal, Target } from "lucide-react";
import { useEffect } from "react";
import { Card, EmptyState, Kicker, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { clsx } from "@/lib/clsx";
import { SchemaFields } from "@/lib/schemaForm";
import { useChrome } from "@/store/chrome";
import type { PluginInfo } from "@/lib/types";

// Display order + metadata per plugin kind (mirrors the engine ABCs, 09 §2).
const KINDS: { kind: string; label: string; blurb: string; icon: typeof Plug }[] = [
  { kind: "distribution", label: "Distributions", blurb: "Sampling distributions for a feature's values.", icon: SlidersHorizontal },
  { kind: "structural_fn", label: "Structural functions", blurb: "Causal/SEM edge equations.", icon: Shuffle },
  { kind: "failure_mode", label: "Failure modes", blurb: "Corruption transforms (missingness, noise, drift…).", icon: Puzzle },
  { kind: "exporter", label: "Exporters", blurb: "Output formats and adapters.", icon: Boxes },
  { kind: "probe_model", label: "Probe models", blurb: "Difficulty baselines whose score sets the target.", icon: Target },
];

export function Plugins() {
  const setCrumbs = useChrome((s) => s.setCrumbs);
  useEffect(() => setCrumbs([]), [setCrumbs]);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["plugins"],
    queryFn: api.listPlugins,
  });

  const plugins = data ?? [];
  const thirdParty = plugins.filter((p) => !p.builtin).length;

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl px-8 py-12">
        <header className="mb-8">
          <Kicker>Ecosystem</Kicker>
          <h1 className="mt-1 font-serif text-3xl text-text">Plugins</h1>
          <p className="mt-2 max-w-2xl text-text-muted">
            Every capability available to a run — core built-ins plus plugins discovered from
            installed <code className="font-mono text-sm">datadoom-plugin-*</code> packages and
            your local plugins directory. Offline; no marketplace.
          </p>
          {!isLoading && !isError && (
            <p className="mt-3 text-sm text-text-faint">
              {plugins.length} capabilities · {plugins.length - thirdParty} core ·{" "}
              {thirdParty} third-party
            </p>
          )}
        </header>

        {isLoading && (
          <div className="flex items-center gap-2 text-text-muted">
            <Spinner /> Loading registry…
          </div>
        )}
        {isError && (
          <EmptyState kicker="Unavailable" title="Couldn't load plugins">
            <p className="text-text-muted">The plugin registry endpoint did not respond.</p>
          </EmptyState>
        )}

        {!isLoading && !isError && (
          <div className="flex flex-col gap-10">
            {KINDS.map(({ kind, label, blurb, icon: Icon }) => {
              const items = plugins.filter((p) => p.kind === kind);
              if (items.length === 0) return null;
              return (
                <section key={kind}>
                  <div className="mb-3 flex items-center gap-2.5">
                    <Icon size={18} className="text-text-muted" />
                    <h2 className="font-serif text-xl text-text">{label}</h2>
                    <span className="rounded-pill bg-surface-2 px-2 py-0.5 font-mono text-[11px] text-text-muted">
                      {items.length}
                    </span>
                  </div>
                  <p className="mb-4 text-sm text-text-faint">{blurb}</p>
                  <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                    {items.map((p) => (
                      <PluginCard key={`${p.kind}:${p.name}`} plugin={p} />
                    ))}
                  </div>
                </section>
              );
            })}

            <AuthoringHint />
          </div>
        )}
      </div>
    </div>
  );
}

function PluginCard({ plugin }: { plugin: PluginInfo }) {
  return (
    <Card className="flex flex-col gap-3 p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="font-mono text-sm font-medium text-text">{plugin.name}</div>
          {plugin.version && (
            <div className="mt-0.5 font-mono text-[11px] text-text-faint">v{plugin.version}</div>
          )}
        </div>
        <SourceBadge plugin={plugin} />
      </div>
      {plugin.schema ? (
        <div className="rounded-control border border-border bg-surface-1 p-3">
          <div className="mb-2 text-[11px] font-medium uppercase tracking-wide text-text-faint">
            Parameters
          </div>
          <SchemaFields schema={plugin.schema} disabled />
        </div>
      ) : (
        !plugin.builtin && (
          <p className="text-xs text-text-faint">No declared parameter schema.</p>
        )
      )}
    </Card>
  );
}

function SourceBadge({ plugin }: { plugin: PluginInfo }) {
  if (plugin.builtin) {
    return (
      <span className="shrink-0 rounded-pill bg-surface-2 px-2 py-0.5 text-[11px] font-medium text-text-muted">
        core
      </span>
    );
  }
  return (
    <span
      className={clsx(
        "shrink-0 rounded-pill px-2 py-0.5 text-[11px] font-medium",
        "bg-primary-tint text-primary",
      )}
      title={`Discovered via ${plugin.source === "local" ? "the local plugins directory" : "a Python entry point"}`}
    >
      plugin · {plugin.source}
    </span>
  );
}

function AuthoringHint() {
  return (
    <Card className="flex gap-4 p-5">
      <Plug size={20} className="mt-0.5 shrink-0 text-text-muted" />
      <div className="text-sm text-text-muted">
        <div className="font-medium text-text">Add a capability</div>
        <p className="mt-1 max-w-2xl">
          Scaffold a plugin with{" "}
          <code className="font-mono text-xs">datadoom plugin new &lt;kind&gt; &lt;name&gt;</code>,
          implement it against the engine ABC using the injected seeded RNG, then{" "}
          <code className="font-mono text-xs">pip install -e .</code> — it appears here and in the
          Canvas automatically. Drop a <code className="font-mono text-xs">.py</code> in{" "}
          <code className="font-mono text-xs">$DATADOOM_HOME/plugins/</code> for quick experiments.
          Validate with <code className="font-mono text-xs">datadoom plugin check</code>.
        </p>
      </div>
    </Card>
  );
}
