import { Link } from "@tanstack/react-router";
import { useEffect, useRef } from "react";

interface MoreSheetProps {
  open: boolean;
  onClose: () => void;
}

// On phones the primary nav is the tab bar; the destinations that do not earn a tab live
// here: Labs (the terminal wants a desktop), Progress (occasional, table-heavy), Settings.
const MORE = [
  { to: "/labs", label: "Labs" },
  { to: "/progress", label: "Progress" },
  { to: "/settings", label: "Settings" },
] as const;

/** Native dialog, like the shortcuts help: a list of ghost buttons, closed by a pick or Esc. */
export function MoreSheet({ open, onClose }: MoreSheetProps) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog ref={ref} className="dialog" onClose={onClose} aria-labelledby="more-title">
      <div className="spread">
        <h2 id="more-title" style={{ margin: 0 }}>
          More
        </h2>
        <form method="dialog">
          <button type="submit" className="btn btn--ghost btn--sm">
            Close
          </button>
        </form>
      </div>
      <ul className="list-reset" style={{ marginTop: "var(--space-4)" }}>
        {MORE.map((item) => (
          <li key={item.to}>
            <Link to={item.to} className="btn btn--ghost btn--block" onClick={onClose}>
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </dialog>
  );
}
