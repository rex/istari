import { useMemo } from "react";

import { useShortcuts, type ShortcutBinding } from "@/lib/shortcuts";
import { useUIStore } from "@/stores/ui";

/** `?` opens help, `Esc` closes it / leaves focus mode. Mounted once in the shell. */
export function GlobalShortcuts() {
  const setShortcutsOpen = useUIStore((s) => s.setShortcutsOpen);
  const setFocusMode = useUIStore((s) => s.setFocusMode);
  const bindings = useMemo<ShortcutBinding[]>(
    () => [
      { key: "?", description: "Show shortcuts", handler: () => setShortcutsOpen(true) },
      {
        key: "Escape",
        description: "Close / leave focus mode",
        handler: () => {
          setShortcutsOpen(false);
          setFocusMode(false);
        },
      },
    ],
    [setShortcutsOpen, setFocusMode],
  );
  useShortcuts(bindings);
  return null;
}
