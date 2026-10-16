import { describe, expect, it } from "vitest";

import { entryKeys, locateInPath, moveEntry, resumeEntry } from "@/lib/paths";
import type { ObjectivePathView, PathEntryView } from "@/lib/types-paths";

const entry = (
  course: string,
  path: string,
  position: number,
  completed = false,
): PathEntryView => ({
  position,
  course_slug: course,
  course_title: course.toUpperCase(),
  lecture_path: path,
  lecture_title: path,
  section_title: "01",
  minutes: 10,
  reason: "test",
  source: "proposed",
  completed,
});

const ENTRIES = [entry("a", "1.mp4", 0, true), entry("b", "2.mp4", 1), entry("a", "3.mp4", 2)];

describe("locateInPath", () => {
  it("finds the neighbours across courses and null off the path", () => {
    const middle = locateInPath(ENTRIES, "b", "2.mp4");
    expect(middle?.index).toBe(1);
    expect(middle?.total).toBe(3);
    expect(middle?.prev?.lecture_path).toBe("1.mp4");
    expect(middle?.next?.course_slug).toBe("a");
    expect(locateInPath(ENTRIES, "a", "3.mp4")?.next).toBeNull();
    expect(locateInPath(ENTRIES, "z", "9.mp4")).toBeNull();
  });
});

describe("resumeEntry and moveEntry", () => {
  const view = (resume: number | null): ObjectivePathView => ({
    objective_code: "1.1",
    objective_title: "t",
    domain_code: "1",
    entries: ENTRIES,
    excluded: [],
    stale_courses: [],
    total_minutes: 30,
    courses: ["A", "B"],
    composed_at: null,
    resume_position: resume,
  });

  it("continues at the first unwatched entry, or the first when all are watched", () => {
    expect(resumeEntry(view(1))?.lecture_path).toBe("2.mp4");
    expect(resumeEntry(view(null))?.lecture_path).toBe("1.mp4");
  });

  it("moves an entry and leaves impossible moves alone", () => {
    expect(entryKeys(moveEntry(ENTRIES, 2, 0))).toEqual([
      ["a", "3.mp4"],
      ["a", "1.mp4"],
      ["b", "2.mp4"],
    ]);
    expect(moveEntry(ENTRIES, 0, -1)).toBe(ENTRIES);
    expect(moveEntry(ENTRIES, 2, 3)).toBe(ENTRIES);
  });
});
