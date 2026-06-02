import { useEffect } from "react";
import { EmptyState } from "@/components/ui";
import { useChrome } from "@/store/chrome";

export function Placeholder({
  kicker,
  title,
  body,
}: {
  kicker: string;
  title: string;
  body: string;
}) {
  const setCrumbs = useChrome((s) => s.setCrumbs);
  // Leaving the dataset workspace — drop the breadcrumb trail entirely.
  useEffect(() => setCrumbs([]), [setCrumbs]);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl px-8 py-12">
        <EmptyState kicker={kicker} title={title}>
          <p className="max-w-md text-text-muted">{body}</p>
        </EmptyState>
      </div>
    </div>
  );
}
