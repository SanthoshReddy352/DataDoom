import { X } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useId, useRef } from "react";
import { Kicker } from "./ui";

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea, input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function Modal({
  open,
  onClose,
  kicker,
  title,
  children,
  footer,
}: {
  open: boolean;
  onClose: () => void;
  kicker: string;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();

  // Accessible dialog behavior: trap Tab focus inside the panel, move focus in
  // on open (respecting any autoFocus child), close on Escape, and restore focus
  // to the previously focused element on close.
  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const panel = panelRef.current;
    const visibleFocusables = () =>
      panel
        ? Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
            (el) => el.offsetParent !== null,
          )
        : [];

    // If a child set autoFocus, React already focused it — don't steal it.
    if (panel && !panel.contains(document.activeElement)) {
      (visibleFocusables()[0] ?? panel).focus();
    }

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key !== "Tab") return;
      const items = visibleFocusables();
      if (items.length === 0) {
        e.preventDefault();
        panel?.focus();
        return;
      }
      const first = items[0];
      const last = items[items.length - 1];
      const active = document.activeElement;
      if (e.shiftKey && (active === first || active === panel)) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      previouslyFocused?.focus?.();
    };
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 animate-fade-in bg-black/30 backdrop-blur-[3px]"
        onClick={onClose}
        aria-hidden
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="ring-focus relative z-10 flex max-h-[90vh] w-full max-w-lg flex-col animate-scale-in rounded-modal border border-border bg-surface-1 p-6 shadow-pop"
      >
        <button
          onClick={onClose}
          className="ring-focus absolute right-4 top-4 rounded-control p-1 text-text-faint hover:bg-surface-2 hover:text-text"
          aria-label="Close"
        >
          <X size={18} />
        </button>
        <Kicker>{kicker}</Kicker>
        <h2
          id={titleId}
          className="mt-2 shrink-0 pr-8 font-display text-2xl font-semibold tracking-tight"
        >
          {title}
        </h2>
        {/* Body scrolls when content is tall, so the modal never exceeds the viewport. */}
        <div className="mt-5 min-h-0 flex-1 overflow-y-auto">{children}</div>
        {footer && <div className="mt-6 flex shrink-0 justify-end gap-3">{footer}</div>}
      </div>
    </div>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-text">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-text-faint">{hint}</span>}
    </label>
  );
}

export function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={
        "mt-1.5 w-full rounded-control border border-border bg-surface-2 px-3 py-2 text-sm text-text outline-none focus:border-primary " +
        (props.className ?? "")
      }
    />
  );
}
