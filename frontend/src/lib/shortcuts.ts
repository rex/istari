/* Scoped keyboard shortcuts.
   - Only bare keys (no Ctrl/Meta/Alt) are ever handled, so browser shortcuts survive.
   - Ignored while typing in inputs, textareas, selects or contenteditable.
   - A binding declares its key and a handler; the hook is mounted by the active
     study surface only, so bindings never leak across screens. */

import { useEffect } from "react";

export interface ShortcutBinding {
  key: string;
  description: string;
  handler: (event: KeyboardEvent) => void;
  /** Allow the shortcut while the focused element is a button/link (default true). */
  allowOnControls?: boolean;
}

export function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  return target.isContentEditable;
}

export function matchesBinding(event: KeyboardEvent, binding: ShortcutBinding): boolean {
  if (event.ctrlKey || event.metaKey || event.altKey) return false;
  if (event.key !== binding.key) return false;
  if (isEditableTarget(event.target)) return false;
  if (binding.allowOnControls === false && event.target instanceof HTMLElement) {
    const tag = event.target.tagName;
    if (tag === "BUTTON" || tag === "A") return false;
  }
  return true;
}

export function dispatchShortcut(
  event: KeyboardEvent,
  bindings: readonly ShortcutBinding[],
): boolean {
  if (event.defaultPrevented || event.repeat) return false;
  for (const binding of bindings) {
    if (matchesBinding(event, binding)) {
      event.preventDefault();
      binding.handler(event);
      return true;
    }
  }
  return false;
}

export function useShortcuts(bindings: readonly ShortcutBinding[], enabled = true): void {
  useEffect(() => {
    if (!enabled) return;
    const listener = (event: KeyboardEvent) => {
      dispatchShortcut(event, bindings);
    };
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, [bindings, enabled]);
}
