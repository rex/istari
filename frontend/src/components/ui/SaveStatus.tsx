export type SaveState = "idle" | "saving" | "saved" | "error" | "stale";

const COPY: Record<SaveState, string> = {
  idle: "",
  saving: "Saving…",
  saved: "Saved",
  error: "Not saved — check your connection",
  stale: "Updated in another tab — reloaded",
};

/** Never shows "saved" unless the server confirmed it. */
export function SaveStatus({
  state,
  onRetry,
}: {
  state: SaveState;
  onRetry?: (() => void) | undefined;
}) {
  if (state === "idle") return null;
  return (
    <span className={`save-status save-status--${state}`} role="status" aria-live="polite">
      {COPY[state]}
      {state === "error" && onRetry ? (
        <button type="button" className="btn btn--ghost btn--sm" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </span>
  );
}
