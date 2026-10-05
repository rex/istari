import { describe, expect, it, vi } from "vitest";

import {
  dispatchShortcut,
  isEditableTarget,
  matchesBinding,
  type ShortcutBinding,
} from "@/lib/shortcuts";

function keyEvent(
  key: string,
  init: Partial<KeyboardEventInit> & { target?: EventTarget } = {},
): KeyboardEvent {
  const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true, ...init });
  if (init.target) Object.defineProperty(event, "target", { value: init.target });
  return event;
}

describe("shortcuts", () => {
  const binding: ShortcutBinding = { key: "1", description: "Option 1", handler: vi.fn() };

  it("matches a bare key", () => {
    expect(matchesBinding(keyEvent("1"), binding)).toBe(true);
  });

  it("never swallows browser combos with modifiers", () => {
    expect(matchesBinding(keyEvent("1", { ctrlKey: true }), binding)).toBe(false);
    expect(matchesBinding(keyEvent("1", { metaKey: true }), binding)).toBe(false);
    expect(matchesBinding(keyEvent("1", { altKey: true }), binding)).toBe(false);
  });

  it("is ignored while typing in editable fields", () => {
    const input = document.createElement("input");
    const textarea = document.createElement("textarea");
    const editable = document.createElement("div");
    editable.contentEditable = "true";
    Object.defineProperty(editable, "isContentEditable", { value: true });
    expect(isEditableTarget(input)).toBe(true);
    expect(isEditableTarget(textarea)).toBe(true);
    expect(isEditableTarget(editable)).toBe(true);
    expect(matchesBinding(keyEvent("1", { target: input }), binding)).toBe(false);
  });

  it("can refuse to fire while a control is focused (no accidental submit from Enter on a link)", () => {
    const link = document.createElement("a");
    const enter: ShortcutBinding = {
      key: "Enter",
      description: "Submit",
      handler: vi.fn(),
      allowOnControls: false,
    };
    expect(matchesBinding(keyEvent("Enter", { target: link }), enter)).toBe(false);
    expect(matchesBinding(keyEvent("Enter", { target: document.body }), enter)).toBe(true);
  });

  it("dispatches the first matching binding and prevents default", () => {
    const handler = vi.fn();
    const event = keyEvent("f");
    const handled = dispatchShortcut(event, [{ key: "f", description: "focus", handler }]);
    expect(handled).toBe(true);
    expect(handler).toHaveBeenCalledTimes(1);
    expect(event.defaultPrevented).toBe(true);
    expect(dispatchShortcut(keyEvent("z"), [{ key: "f", description: "focus", handler }])).toBe(
      false,
    );
  });

  it("ignores key repeat", () => {
    const handler = vi.fn();
    dispatchShortcut(keyEvent("1", { repeat: true }), [{ key: "1", description: "x", handler }]);
    expect(handler).not.toHaveBeenCalled();
  });
});
