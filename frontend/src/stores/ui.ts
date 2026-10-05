/* Client-only UI state: focus mode and the shortcuts overlay. */

import { create } from "zustand";

interface UIState {
  focusMode: boolean;
  shortcutsOpen: boolean;
  setFocusMode: (on: boolean) => void;
  toggleFocusMode: () => void;
  setShortcutsOpen: (open: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  focusMode: false,
  shortcutsOpen: false,
  setFocusMode: (on) => set({ focusMode: on }),
  toggleFocusMode: () => set((state) => ({ focusMode: !state.focusMode })),
  setShortcutsOpen: (open) => set({ shortcutsOpen: open }),
}));
