import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowRight, Sparkles, Trophy } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, EmptyState, Kicker, Spinner } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useChrome } from "@/store/chrome";
import { toast } from "@/store/toast";
import type { TemplateSummary } from "@/lib/types";

export function Templates() {
  const setCrumbs = useChrome((s) => s.setCrumbs);
  useEffect(() => setCrumbs([]), [setCrumbs]);
  const nav = useNavigate();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["templates"],
    queryFn: api.listTemplates,
  });

  const use = useMutation({
    mutationFn: async (t: TemplateSummary) => {
      const detail = await api.getTemplate(t.id);
      return api.createDataset({ name: detail.name, description: detail.description, spec: detail.spec });
    },
    onSuccess: (ds) => nav(`/datasets/${ds.dataset_id}`),
    onError: (e: ApiError) => toast(e.message, "error"),
  });

  const [level, setLevel] = useState<"all" | "hackathon" | "starter">("all");

  // Hackathon flagships first, then by domain/name.
  const all = [...(data ?? [])].sort((a, b) => {
    if (a.level !== b.level) return a.level === "hackathon" ? -1 : 1;
    return a.domain === b.domain ? a.name.localeCompare(b.name) : a.domain.localeCompare(b.domain);
  });
  const templates = level === "all" ? all : all.filter((t) => t.level === level);
  const domainCount = new Set(templates.map((t) => t.domain)).size;
  const hackathonCount = all.filter((t) => t.level === "hackathon").length;

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-6xl px-8 py-12">
        <header className="mb-8">
          <Kicker>Collections</Kicker>
          <h1 className="mt-1 font-serif text-3xl text-text">Templates</h1>
          <p className="mt-2 max-w-2xl text-text-muted">
            Curated, ready-to-run domain datasets. Start from one in a click — it opens in the
            Canvas as a new dataset you can edit, then generate. <span className="text-text">Hackathon</span>{" "}
            challenges are enterprise-grade ML problems — deep causal structure, a hidden
            confounder, realistic data-quality failures and a calibrated difficulty band.
          </p>
          {!isLoading && !isError && (
            <div className="mt-4 flex items-center gap-4">
              <div className="inline-flex rounded-pill border border-border bg-surface p-0.5 text-sm">
                {(["all", "hackathon", "starter"] as const).map((l) => (
                  <button
                    key={l}
                    onClick={() => setLevel(l)}
                    className={
                      "rounded-pill px-3 py-1 capitalize transition-colors " +
                      (level === l ? "bg-primary text-white" : "text-text-muted hover:text-text")
                    }
                  >
                    {l === "hackathon" ? `Hackathon (${hackathonCount})` : l}
                  </button>
                ))}
              </div>
              <p className="text-sm text-text-faint">
                {templates.length} templates across {domainCount} domains
              </p>
            </div>
          )}
        </header>

        {isLoading && (
          <div className="flex items-center gap-2 text-text-muted">
            <Spinner /> Loading templates…
          </div>
        )}
        {isError && (
          <EmptyState kicker="Unavailable" title="Couldn't load templates">
            <p className="text-text-muted">The templates endpoint did not respond.</p>
          </EmptyState>
        )}

        {!isLoading && !isError && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {templates.map((t) => (
              <TemplateCard key={t.id} t={t} busy={use.isPending} onUse={() => use.mutate(t)} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function TemplateCard({
  t,
  busy,
  onUse,
}: {
  t: TemplateSummary;
  busy: boolean;
  onUse: () => void;
}) {
  return (
    <Card className="flex h-full flex-col gap-3 p-5">
      <div className="flex items-center justify-between">
        <span className="rounded-pill bg-primary-tint px-2.5 py-0.5 text-[11px] font-medium text-primary">
          {t.domain}
        </span>
        {t.level === "hackathon" && (
          <span className="inline-flex items-center gap-1 rounded-pill bg-warning-tint px-2.5 py-0.5 text-[11px] font-medium text-text">
            <Trophy size={12} /> Hackathon
          </span>
        )}
      </div>
      <div>
        <h2 className="font-serif text-lg leading-tight text-text">{t.name}</h2>
        <p className="mt-1.5 text-sm leading-relaxed text-text-muted">{t.description}</p>
      </div>
      <div className="mt-auto flex flex-col gap-3 pt-1">
        <div className="flex flex-wrap gap-1.5">
          {t.tags.map((tag) => (
            <span
              key={tag}
              className="rounded-pill bg-surface-2 px-2 py-0.5 font-mono text-[10px] text-text-muted"
            >
              {tag}
            </span>
          ))}
        </div>
        <Button variant="primary" className="w-full justify-center" disabled={busy} onClick={onUse}>
          <Sparkles size={15} /> Use this template <ArrowRight size={15} />
        </Button>
      </div>
    </Card>
  );
}
