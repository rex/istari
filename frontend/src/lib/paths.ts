/* Pure helpers for learning paths: where a lecture sits in one, and reordering. */

import type { LectureKey, ObjectivePathView, PathEntryView } from "@/lib/types-paths";

export interface PathPosition {
  index: number;
  total: number;
  prev: PathEntryView | null;
  next: PathEntryView | null;
}

/** The lecture's place in the path, or null when it is not on it. */
export function locateInPath(
  entries: PathEntryView[],
  course: string,
  path: string,
): PathPosition | null {
  const index = entries.findIndex((e) => e.course_slug === course && e.lecture_path === path);
  if (index < 0) return null;
  return {
    index,
    total: entries.length,
    prev: entries[index - 1] ?? null,
    next: entries[index + 1] ?? null,
  };
}

/** Where "continue" starts: the first unwatched entry, else the first entry. */
export function resumeEntry(view: ObjectivePathView): PathEntryView | null {
  return view.entries[view.resume_position ?? 0] ?? null;
}

export function entryKeys(entries: PathEntryView[]): LectureKey[] {
  return entries.map((e) => [e.course_slug, e.lecture_path]);
}

/** A new array with the entry at `from` moved to `to`; out-of-range moves change nothing. */
export function moveEntry<T>(items: T[], from: number, to: number): T[] {
  if (from < 0 || to < 0 || from >= items.length || to >= items.length || from === to) {
    return items;
  }
  const next = [...items];
  const [moved] = next.splice(from, 1);
  if (moved !== undefined) next.splice(to, 0, moved);
  return next;
}
