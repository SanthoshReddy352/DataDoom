import { create } from "zustand";

export interface Crumb {
  label: string;
  to?: string;
}

interface ChromeState {
  crumbs: Crumb[];
  setCrumbs: (crumbs: Crumb[]) => void;
}

// Lightweight breadcrumb channel: pages publish their trail; the Layout top bar
// renders it. This is what gives the app a structured, legible user flow.
export const useChrome = create<ChromeState>((set) => ({
  crumbs: [],
  setCrumbs: (crumbs) => set({ crumbs }),
}));
