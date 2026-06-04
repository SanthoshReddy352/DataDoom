import {
  Boxes,
  ChevronRight,
  LayoutGrid,
  PanelLeftClose,
  PanelLeftOpen,
  Plug,
  Settings as SettingsIcon,
} from "lucide-react";
import type { ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { clsx } from "@/lib/clsx";
import { useUi } from "@/store/ui";
import { useChrome, type Crumb } from "@/store/chrome";
import { Toaster } from "./Toaster";
import { ConfirmHost } from "./ConfirmHost";
import { ErrorBoundary } from "./ErrorBoundary";

const NAV = [
  { to: "/datasets", label: "Datasets", icon: LayoutGrid, section: "Workspace" },
  { to: "/templates", label: "Templates", icon: Boxes, section: "Library" },
  { to: "/plugins", label: "Plugins", icon: Plug, section: "Library" },
];

const NAV_SECTIONS = ["Workspace", "Library"] as const;

export function Layout({ children }: { children: ReactNode }) {
  const collapsed = useUi((s) => s.sidebarCollapsed);
  const toggle = useUi((s) => s.toggleSidebar);
  const crumbs = useChrome((s) => s.crumbs);
  const location = useLocation();

  return (
    <div className="flex h-full bg-bg">
      {/* Keyboard users can jump straight to the page content. */}
      <a
        href="#main-content"
        className="ring-focus sr-only z-[100] focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:rounded-control focus:border focus:border-border focus:bg-surface-1 focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-text focus:shadow-pop"
      >
        Skip to content
      </a>
      {/* Sidebar */}
      <aside
        aria-label="Sidebar"
        className={clsx(
          "hidden shrink-0 flex-col border-r border-border bg-surface-1 transition-[width] duration-300 ease-out md:flex",
          collapsed ? "w-[68px]" : "w-[244px]",
        )}
      >
        {/* Brand / wordmark */}
        <div className={clsx("flex h-16 items-center", collapsed ? "justify-center px-2" : "px-5")}>
          <Link to="/datasets" className="ring-focus flex items-center rounded-control" title="DataDoom">
            {collapsed ? (
              <span className="wordmark text-xl text-text">
                DD<span className="wordmark-dot">.</span>
              </span>
            ) : (
              <span className="leading-none">
                <span className="wordmark text-[22px] text-text">
                  DataDoom<span className="wordmark-dot">.</span>
                </span>
                <span className="kicker mt-1 block">synthetic data lab</span>
              </span>
            )}
          </Link>
        </div>

        {/* Nav */}
        <nav aria-label="Primary" className="mt-2 flex flex-1 flex-col gap-5 px-3">
          {NAV_SECTIONS.map((section) => (
            <div key={section}>
              {!collapsed && <div className="kicker mb-1.5 px-2.5">{section}</div>}
              <div className="flex flex-col gap-0.5">
                {NAV.filter((n) => n.section === section).map(({ to, label, icon: Icon }) => (
                  <NavLink
                    key={to}
                    to={to}
                    title={collapsed ? label : undefined}
                    className={({ isActive }) =>
                      clsx(
                        "ring-focus group relative flex items-center gap-3 rounded-control py-2 text-sm font-medium transition-colors",
                        collapsed ? "justify-center px-0" : "px-2.5",
                        isActive
                          ? "bg-primary-tint text-primary"
                          : "text-text-muted hover:bg-surface-2 hover:text-text",
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        {isActive && (
                          <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-primary" />
                        )}
                        <Icon size={18} strokeWidth={2} />
                        {!collapsed && label}
                      </>
                    )}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        {/* Footer: settings + offline + collapse */}
        <div className="flex flex-col gap-1 border-t border-border px-3 py-3">
          <NavLink
            to="/settings"
            title={collapsed ? "Settings" : undefined}
            className={({ isActive }) =>
              clsx(
                "ring-focus flex items-center gap-3 rounded-control py-2 text-sm font-medium transition-colors",
                collapsed ? "justify-center px-0" : "px-2.5",
                isActive ? "bg-primary-tint text-primary" : "text-text-muted hover:bg-surface-2 hover:text-text",
              )
            }
          >
            <SettingsIcon size={18} />
            {!collapsed && "Settings"}
          </NavLink>

          {!collapsed && (
            <div className="flex items-center gap-2 px-2.5 pt-1 text-xs text-text-faint">
              <span className="h-1.5 w-1.5 rounded-full bg-success" />
              local · offline
              <span className="ml-auto rounded-pill bg-surface-2 px-1.5 py-0.5 font-mono text-[10px]">
                v0.1
              </span>
            </div>
          )}

          <button
            onClick={toggle}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-expanded={!collapsed}
            className={clsx(
              "ring-focus mt-1 flex items-center gap-2 rounded-control py-2 text-xs text-text-faint transition-colors hover:bg-surface-2 hover:text-text",
              collapsed ? "justify-center px-0" : "px-2.5",
            )}
          >
            {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={16} />}
            {!collapsed && "Collapse"}
          </button>
        </div>
      </aside>

      {/* Main column */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 shrink-0 items-center gap-3 border-b border-border bg-surface-1/80 px-6 backdrop-blur">
          {/* Mobile brand */}
          <Link to="/datasets" className="wordmark text-lg text-text md:hidden">
            DataDoom<span className="wordmark-dot">.</span>
          </Link>

          {/* Breadcrumbs */}
          <Breadcrumbs crumbs={crumbs} />

          <div className="ml-auto flex items-center gap-3">
            <span
              title="All data stays on this machine"
              className="hidden items-center gap-2 rounded-pill border border-border bg-surface-2 px-3 py-1.5 text-xs text-text-muted sm:inline-flex"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-success" /> local
            </span>
          </div>
        </header>
        <main id="main-content" tabIndex={-1} className="min-h-0 flex-1 overflow-hidden outline-none">
          <ErrorBoundary resetKey={location.pathname}>{children}</ErrorBoundary>
        </main>
      </div>
      <Toaster />
      <ConfirmHost />
    </div>
  );
}

function Breadcrumbs({ crumbs }: { crumbs: Crumb[] }) {
  if (crumbs.length === 0) return <div className="hidden md:block" />;
  return (
    <nav aria-label="Breadcrumb" className="hidden min-w-0 items-center gap-1.5 text-sm md:flex">
      {crumbs.map((c, i) => {
        const last = i === crumbs.length - 1;
        return (
          <span key={i} className="flex min-w-0 items-center gap-1.5">
            {i > 0 && <ChevronRight size={14} className="shrink-0 text-text-faint" />}
            {c.to && !last ? (
              <Link
                to={c.to}
                className="ring-focus truncate rounded text-text-muted transition-colors hover:text-text"
              >
                {c.label}
              </Link>
            ) : (
              <span className={clsx("truncate", last ? "font-medium text-text" : "text-text-muted")}>
                {c.label}
              </span>
            )}
          </span>
        );
      })}
    </nav>
  );
}
