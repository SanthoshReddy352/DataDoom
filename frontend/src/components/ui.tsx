import { clsx } from "@/lib/clsx";
import {
  useEffect,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";

// --- Button -------------------------------------------------------------------
type Variant = "primary" | "secondary" | "ghost" | "destructive";
const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-primary text-white shadow-soft hover:bg-primary-hover focus-visible:ring-primary active:translate-y-px",
  secondary:
    "bg-surface-1 text-text border border-border hover:border-border-strong hover:bg-surface-2 focus-visible:ring-primary",
  ghost: "text-text-muted hover:text-text hover:bg-surface-2 focus-visible:ring-primary",
  destructive: "bg-hazard text-white hover:opacity-90 focus-visible:ring-hazard active:translate-y-px",
};
export function Button({
  variant = "secondary",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-control px-3.5 py-2 text-sm font-medium",
        "transition-all duration-150 outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-bg",
        "disabled:opacity-50 disabled:pointer-events-none",
        VARIANTS[variant],
        className,
      )}
      {...props}
    />
  );
}

// --- IconButton ---------------------------------------------------------------
export function IconButton({
  className,
  active,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { active?: boolean }) {
  return (
    <button
      className={clsx(
        "ring-focus inline-flex h-8 w-8 items-center justify-center rounded-control text-text-muted transition-colors",
        "hover:bg-surface-2 hover:text-text disabled:opacity-40 disabled:pointer-events-none",
        active && "bg-primary-tint text-primary",
        className,
      )}
      {...props}
    />
  );
}

// --- Segmented control --------------------------------------------------------
export function Segmented<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: ReactNode }[];
}) {
  return (
    <div className="inline-flex items-center rounded-control border border-border bg-surface-2 p-0.5">
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={clsx(
            "ring-focus inline-flex items-center gap-1.5 rounded-[7px] px-3 py-1.5 text-xs font-medium transition-colors",
            value === o.value
              ? "bg-surface-1 text-primary shadow-soft"
              : "text-text-faint hover:text-text",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

// --- Menu (click-to-open popover) --------------------------------------------
export function Menu({
  trigger,
  children,
  align = "right",
}: {
  trigger: (props: { open: boolean; toggle: () => void }) => ReactNode;
  children: (close: () => void) => ReactNode;
  align?: "left" | "right";
}) {
  const [open, setOpen] = useState(false);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const triggerRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const toggle = () => {
    if (open) {
      setOpen(false);
      return;
    }
    if (triggerRef.current) setRect(triggerRef.current.getBoundingClientRect());
    setOpen(true);
  };

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      const t = e.target as Node;
      if (menuRef.current?.contains(t) || triggerRef.current?.contains(t)) return;
      setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    const onReflow = () => setOpen(false); // fixed menu would detach on scroll/resize
    window.addEventListener("mousedown", onDown);
    window.addEventListener("keydown", onKey);
    window.addEventListener("resize", onReflow);
    window.addEventListener("scroll", onReflow, true);
    return () => {
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", onReflow);
      window.removeEventListener("scroll", onReflow, true);
    };
  }, [open]);

  return (
    <div ref={triggerRef} className="relative inline-flex">
      {trigger({ open, toggle })}
      {open &&
        rect &&
        (() => {
          const below = window.innerHeight - rect.bottom;
          const above = rect.top;
          // Flip up when there isn't comfortable room below and there's more above.
          const openUp = below < 220 && above > below;
          const maxHeight = Math.max(120, (openUp ? above : below) - 12);
          return createPortal(
            <div
              ref={menuRef}
              style={{
                position: "fixed",
                top: openUp ? undefined : rect.bottom + 4,
                bottom: openUp ? window.innerHeight - rect.top + 4 : undefined,
                left: align === "left" ? rect.left : undefined,
                right: align === "right" ? Math.max(8, window.innerWidth - rect.right) : undefined,
                maxHeight,
              }}
              className={clsx(
                "z-[60] min-w-[180px] animate-scale-in overflow-auto rounded-control border border-border bg-surface-1 p-1 shadow-pop",
                openUp
                  ? align === "right"
                    ? "origin-bottom-right"
                    : "origin-bottom-left"
                  : align === "right"
                    ? "origin-top-right"
                    : "origin-top-left",
              )}
            >
              {children(() => setOpen(false))}
            </div>,
            document.body,
          );
        })()}
    </div>
  );
}

export function MenuItem({
  children,
  onClick,
  danger,
  icon,
}: {
  children: ReactNode;
  onClick: () => void;
  danger?: boolean;
  icon?: ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        "ring-focus flex w-full items-center gap-2.5 rounded-[7px] px-2.5 py-2 text-left text-sm transition-colors",
        danger
          ? "text-hazard hover:bg-hazard-tint"
          : "text-text-muted hover:bg-surface-2 hover:text-text",
      )}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      {children}
    </button>
  );
}

// --- Card ---------------------------------------------------------------------
export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={clsx("rounded-card border border-border bg-surface-1 shadow-card", className)}
      {...props}
    />
  );
}

// --- Kicker / eyebrow ---------------------------------------------------------
export function Kicker({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={clsx("kicker", className)}>{children}</div>;
}

// --- PullStat (oversized display numeral) ------------------------------------
export function PullStat({
  value,
  label,
  tone = "text",
}: {
  value: ReactNode;
  label: string;
  tone?: "text" | "success" | "warning" | "hazard" | "primary";
}) {
  const toneClass = {
    text: "text-text",
    success: "text-success",
    warning: "text-warning",
    hazard: "text-hazard",
    primary: "text-primary",
  }[tone];
  return (
    <div>
      <div className={clsx("font-display text-[40px] font-semibold leading-none tnum", toneClass)}>
        {value}
      </div>
      <div className="kicker mt-2">{label}</div>
    </div>
  );
}

// --- Status badge -------------------------------------------------------------
const STATUS: Record<string, { dot: string; label: string; cls: string }> = {
  draft: { dot: "bg-text-faint", label: "Draft", cls: "text-text-muted bg-surface-2" },
  running: { dot: "bg-primary animate-pulse", label: "Running", cls: "text-primary bg-primary-tint" },
  queued: { dot: "bg-primary animate-pulse", label: "Queued", cls: "text-primary bg-primary-tint" },
  completed: { dot: "bg-success", label: "Completed", cls: "text-success bg-success-tint" },
  failed: { dot: "bg-hazard", label: "Failed", cls: "text-hazard bg-hazard-tint" },
  cancelled: { dot: "bg-text-faint", label: "Cancelled", cls: "text-text-muted bg-surface-2" },
};
export function StatusBadge({ status }: { status: string }) {
  const s = STATUS[status] ?? STATUS.draft;
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-pill px-2.5 py-1 text-xs font-medium",
        s.cls,
      )}
    >
      <span className={clsx("h-1.5 w-1.5 rounded-full", s.dot)} />
      {s.label}
    </span>
  );
}

// --- Type chip ----------------------------------------------------------------
export const TYPE_COLOR: Record<string, string> = {
  numeric: "var(--primary)",
  categorical: "var(--info)",
  boolean: "var(--warning)",
  datetime: "var(--success)",
  text: "var(--hazard)",
};
export function TypeChip({ type }: { type: string }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-pill px-2 py-0.5 text-[11px] font-semibold"
      style={{
        color: TYPE_COLOR[type] ?? "var(--text-muted)",
        background: `color-mix(in srgb, ${TYPE_COLOR[type] ?? "var(--text-muted)"} 12%, transparent)`,
      }}
    >
      <span
        className="h-1.5 w-1.5 rounded-[2px]"
        style={{ background: TYPE_COLOR[type] ?? "var(--text-muted)" }}
      />
      {type}
    </span>
  );
}

// --- Mono hash chip with copy -------------------------------------------------
export function CopyableHash({ label, value }: { label: string; value: string | number }) {
  const text = String(value);
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard?.writeText(text);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1200);
      }}
      title="Click to copy"
      className="ring-focus group inline-flex items-center gap-2 rounded-control border border-border bg-surface-2 px-2.5 py-1.5 text-xs transition-colors hover:border-border-strong"
    >
      <span className="kicker">{label}</span>
      <span className="font-mono text-text-muted group-hover:text-text">
        {copied ? "copied!" : text.length > 18 ? `${text.slice(0, 10)}…${text.slice(-6)}` : text}
      </span>
    </button>
  );
}

// --- Empty state --------------------------------------------------------------
export function EmptyState({
  kicker,
  title,
  children,
}: {
  kicker: string;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="dotgrid flex min-h-[42vh] flex-col items-center justify-center rounded-card border border-dashed border-border p-12 text-center">
      <Kicker>{kicker}</Kicker>
      <h3 className="mt-3 font-display text-2xl font-semibold text-text">{title}</h3>
      <div className="mt-5 flex gap-3">{children}</div>
    </div>
  );
}

export function Spinner({ className }: { className?: string }) {
  return (
    <span
      className={clsx(
        "inline-block h-4 w-4 animate-spin rounded-full border-2 border-border-strong border-t-primary",
        className,
      )}
    />
  );
}
