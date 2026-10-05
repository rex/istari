import { useEffect, useRef } from "react";

import { Kbd } from "@/components/ui/Kbd";
import { useUIStore } from "@/stores/ui";

const GROUPS = [
  {
    title: "Practice",
    rows: [
      ["1 – 6", "Select an option by position"],
      ["Enter", "Submit the answer, or go to the next question"],
      ["f", "Toggle focus mode"],
    ],
  },
  {
    title: "Review",
    rows: [
      ["Space", "Reveal the answer"],
      ["1 / 2 / 3 / 4", "Again / Hard / Good / Easy"],
    ],
  },
  {
    title: "Anywhere",
    rows: [
      ["?", "This help"],
      ["Esc", "Close help, leave focus mode"],
    ],
  },
] as const;

/** Native <dialog>; shortcuts never use modifier keys, so browser shortcuts are untouched. */
export function ShortcutsHelp() {
  const open = useUIStore((s) => s.shortcutsOpen);
  const setOpen = useUIStore((s) => s.setShortcutsOpen);
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      className="dialog"
      onClose={() => setOpen(false)}
      aria-labelledby="shortcuts-title"
    >
      <h2 id="shortcuts-title">Keyboard shortcuts</h2>
      <p className="muted small">
        Only active on the matching screen, and never while you are typing.
      </p>
      {GROUPS.map((group) => (
        <section key={group.title}>
          <h3>{group.title}</h3>
          <dl className="shortcut-list">
            {group.rows.map(([keys, what]) => (
              <div key={keys} className="shortcut-list__row">
                <dt>
                  <Kbd>{keys}</Kbd>
                </dt>
                <dd>{what}</dd>
              </div>
            ))}
          </dl>
        </section>
      ))}
      <form method="dialog">
        <button type="submit" className="btn btn--secondary">
          Close
        </button>
      </form>
    </dialog>
  );
}
