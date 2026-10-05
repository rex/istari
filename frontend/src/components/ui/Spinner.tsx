export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="spinner" role="status" aria-live="polite">
      <span className="spinner__dot" aria-hidden="true" />
      <span className="spinner__label">{label}…</span>
    </div>
  );
}
