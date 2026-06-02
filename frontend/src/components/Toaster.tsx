import { Check, Info, X } from "lucide-react";
import { useToasts } from "@/store/toast";
import { clsx } from "@/lib/clsx";

const TONE = {
  info: { icon: Info, cls: "text-text", dot: "text-primary" },
  success: { icon: Check, cls: "text-text", dot: "text-success" },
  error: { icon: X, cls: "text-text", dot: "text-hazard" },
} as const;

export function Toaster() {
  const toasts = useToasts((s) => s.toasts);
  const dismiss = useToasts((s) => s.dismiss);
  return (
    <div className="pointer-events-none fixed bottom-5 left-1/2 z-50 flex -translate-x-1/2 flex-col items-center gap-2">
      {toasts.map((t) => {
        const { icon: Icon, dot } = TONE[t.tone];
        return (
          <div
            key={t.id}
            className="pointer-events-auto flex animate-slide-up items-center gap-2.5 rounded-pill border border-border bg-surface-1 py-2 pl-3 pr-2 text-sm text-text shadow-pop"
          >
            <Icon size={15} className={clsx("shrink-0", dot)} />
            <span>{t.message}</span>
            <button
              onClick={() => dismiss(t.id)}
              className="ring-focus rounded-full p-1 text-text-faint hover:text-text"
            >
              <X size={13} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
