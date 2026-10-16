/* Presentation helpers for the course comparison (kept out of the page file for fast refresh). */

import type { CourseRow, Currency } from "@/lib/types-comparison";

export type SortKey =
  "title" | "objectives" | "currency" | "captions" | "minutes" | "watched" | `domain:${string}`;
export type SortDirection = "asc" | "desc";

export const CURRENCY_LABEL: Record<Currency, string> = {
  current: "current exam",
  older: "older version",
  newer: "newer version",
  same_exam: "same exam, no version named",
  other: "other exam",
  unknown: "no exam named",
};

export const CURRENCY_TONE: Record<Currency, "success" | "warning" | "info" | "neutral"> = {
  current: "success",
  older: "warning",
  newer: "info",
  same_exam: "info",
  other: "neutral",
  unknown: "neutral",
};

const CURRENCY_RANK: Record<Currency, number> = {
  current: 0,
  same_exam: 1,
  newer: 2,
  older: 3,
  other: 4,
  unknown: 5,
};

const DASH = String.fromCharCode(0x2014);

/** "42 min" under an hour, "1 h 05 min" past it, a dash when nothing is measured. */
export function formatMinutes(minutes: number): string {
  const whole = Math.round(minutes);
  if (whole <= 0) return DASH;
  if (whole < 60) return `${whole} min`;
  return `${Math.floor(whole / 60)} h ${String(whole % 60).padStart(2, "0")} min`;
}

function metric(row: CourseRow, key: SortKey): number | string {
  switch (key) {
    case "title":
      return row.course_title.toLowerCase();
    case "objectives":
      return row.objectives_touched;
    case "currency":
      return -CURRENCY_RANK[row.currency];
    case "captions":
      return row.lectures_total ? row.lectures_captioned / row.lectures_total : 0;
    case "minutes":
      return row.minutes_mapped;
    case "watched":
      return row.lectures_total ? row.lectures_completed / row.lectures_total : 0;
    default: {
      const code = key.slice("domain:".length);
      const cell = row.domains.find((d) => d.domain_code === code);
      return cell ? cell.objectives_touched * 10_000 + cell.minutes : 0;
    }
  }
}

/** A new array sorted by one column; ties fall back to the title so the order is stable. */
export function sortRows(rows: CourseRow[], key: SortKey, direction: SortDirection): CourseRow[] {
  const sign = direction === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const x = metric(a, key);
    const y = metric(b, key);
    const order =
      typeof x === "string" && typeof y === "string" ? x.localeCompare(y) : Number(x) - Number(y);
    return order !== 0 ? sign * order : a.course_title.localeCompare(b.course_title);
  });
}

/** Words read upward, figures read downward: the first click shows the best at the top. */
export function defaultDirection(key: SortKey): SortDirection {
  return key === "title" ? "asc" : "desc";
}
