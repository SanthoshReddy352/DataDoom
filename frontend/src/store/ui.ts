import { create } from "zustand";

const KEY = "datadoom-sidebar";

function initialCollapsed(): boolean {
  try {
    return localStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
}

interface UiState {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  setSidebar: (collapsed: boolean) => void;
}

export const useUi = create<UiState>((set, get) => ({
  sidebarCollapsed: initialCollapsed(),
  toggleSidebar: () => get().setSidebar(!get().sidebarCollapsed),
  setSidebar: (collapsed) => {
    try {
      localStorage.setItem(KEY, collapsed ? "1" : "0");
    } catch {
      /* ignore */
    }
    set({ sidebarCollapsed: collapsed });
  },
}));
