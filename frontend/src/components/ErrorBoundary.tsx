import { Component, type ReactNode } from "react";
import { RotateCcw } from "lucide-react";

interface State {
  error: Error | null;
}

interface Props {
  children: ReactNode;
  // Changes whenever the route changes (e.g. the pathname). When it changes we
  // clear a caught error, so navigating away (breadcrumbs, sidebar) recovers the
  // view instead of leaving the fallback stuck on screen.
  resetKey?: string;
}

/**
 * Scoped boundary around the routed page area. A render error in one view (e.g.
 * the canvas) shows a recoverable fallback instead of unmounting the whole app
 * to a blank screen — the chrome (sidebar/header) stays intact.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error) {
    // eslint-disable-next-line no-console
    console.error("View error:", error);
  }

  componentDidUpdate(prevProps: Props) {
    // A navigation happened while showing the fallback → recover automatically.
    if (this.state.error && prevProps.resetKey !== this.props.resetKey) {
      this.setState({ error: null });
    }
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex h-full flex-col items-center justify-center gap-4 p-10 text-center">
          <div className="kicker">Something went sideways</div>
          <h2 className="font-display text-2xl font-semibold tracking-tight">This view hit an error</h2>
          <p className="max-w-md text-sm text-text-muted">
            The rest of DataDoom is fine — your data is safe. Reset this view to continue.
          </p>
          <pre className="max-w-lg overflow-auto rounded-control border border-border bg-surface-2 p-3 text-left font-mono text-xs text-text-faint">
            {this.state.error.message}
          </pre>
          <button
            onClick={() => this.setState({ error: null })}
            className="ring-focus inline-flex items-center gap-2 rounded-control bg-primary px-3.5 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            <RotateCcw size={15} /> Reset view
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
