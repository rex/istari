/* Small, pure formatting helpers. Dates render in the user's configured timezone. */

export function formatPercent(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatDateTime(iso: string, timeZone: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat(undefined, {
    timeZone,
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function formatDate(iso: string, timeZone: string): string {
  const date = new Date(iso.length === 10 ? `${iso}T12:00:00Z` : iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat(undefined, { timeZone, dateStyle: "medium" }).format(date);
}

/** "in 3 days", "today", "2 hours ago" — coarse, friendly, never guilt-tripping. */
export function formatRelative(iso: string, now: Date = new Date()): string {
  const target = new Date(iso);
  const diffMs = target.getTime() - now.getTime();
  const abs = Math.abs(diffMs);
  const minute = 60_000;
  const hour = 60 * minute;
  const day = 24 * hour;
  const future = diffMs > 0;
  if (abs < minute) return "now";
  if (abs < hour) {
    const n = Math.round(abs / minute);
    return future ? `in ${n} min` : `${n} min ago`;
  }
  if (abs < day) {
    const n = Math.round(abs / hour);
    return future ? `in ${n} h` : `${n} h ago`;
  }
  const n = Math.round(abs / day);
  if (n === 1) return future ? "tomorrow" : "yesterday";
  return future ? `in ${n} days` : `${n} days ago`;
}

export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

export function clampText(text: string, max = 120): string {
  return text.length <= max ? text : `${text.slice(0, max - 1).trimEnd()}…`;
}
