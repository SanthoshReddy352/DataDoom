import { create } from "zustand";

// In-app replacement for the browser's `window.confirm`. A single dialog is
// shown at a time (mounted once via <ConfirmHost />); `confirmDialog(...)`
// resolves to true/false so call sites read like the native API:
//
//   if (await confirmDialog({ title: "Delete?", tone: "danger" })) del.mutate();

export interface ConfirmOptions {
  title: string;
  message?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: "default" | "danger";
}

interface PendingConfirm extends ConfirmOptions {
  id: number;
  resolve: (ok: boolean) => void;
}

interface ConfirmState {
  current: PendingConfirm | null;
  open: (opts: ConfirmOptions) => Promise<boolean>;
  respond: (ok: boolean) => void;
}

let seq = 0;

export const useConfirm = create<ConfirmState>((set, get) => ({
  current: null,
  open: (opts) =>
    new Promise<boolean>((resolve) => {
      // If a dialog is already open, resolve it as cancelled before replacing.
      const existing = get().current;
      if (existing) existing.resolve(false);
      set({ current: { ...opts, id: ++seq, resolve } });
    }),
  respond: (ok) => {
    const cur = get().current;
    if (cur) cur.resolve(ok);
    set({ current: null });
  },
}));

// Imperative helper for non-component call sites (mirrors `toast`).
export const confirmDialog = (opts: ConfirmOptions): Promise<boolean> =>
  useConfirm.getState().open(opts);
