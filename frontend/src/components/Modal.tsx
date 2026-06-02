import { X } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect } from "react";
import { Kicker } from "./ui";

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
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 animate-fade-in bg-black/30 backdrop-blur-[3px]"
        onClick={onClose}
        aria-hidden
      />
      <div className="relative z-10 w-full max-w-lg animate-scale-in rounded-modal border border-border bg-surface-1 p-6 shadow-pop">
        <button
          onClick={onClose}
          className="ring-focus absolute right-4 top-4 rounded-control p-1 text-text-faint hover:bg-surface-2 hover:text-text"
          aria-label="Close"
        >
          <X size={18} />
        </button>
        <Kicker>{kicker}</Kicker>
        <h2 className="mt-2 font-display text-2xl font-semibold tracking-tight">{title}</h2>
        <div className="mt-5">{children}</div>
        {footer && <div className="mt-6 flex justify-end gap-3">{footer}</div>}
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
