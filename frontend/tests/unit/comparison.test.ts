import { describe, expect, it } from "vitest";

import { defaultDirection, formatMinutes, sortRows } from "@/lib/comparison";
import type { CourseRow } from "@/lib/types-comparison";

const row = (over: Partial<CourseRow>): CourseRow => ({
  course_slug: "a",
  course_title: "A",
  topic: "Cloud/Testing",
  exam_code: null,
  year: null,
  currency: "unknown",
  lectures_total: 10,
  lectures_captioned: 10,
  lectures_mapped: 5,
  lectures_completed: 0,
  minutes_captioned: 100,
  minutes_mapped: 50,
  objectives_touched: 3,
  domains: [],
  ...over,
});

const slugs = (rows: CourseRow[]) => rows.map((r) => r.course_slug);

describe("formatMinutes", () => {
  it("reads as minutes under an hour, hours past it, a dash for nothing", () => {
    expect(formatMinutes(0)).toBe(String.fromCharCode(0x2014));
    expect(formatMinutes(42.4)).toBe("42 min");
    expect(formatMinutes(65)).toBe("1 h 05 min");
  });
});

describe("sortRows", () => {
  it("shows the best figure first by default and titles in reading order", () => {
    const rows = [
      row({ course_slug: "b", course_title: "Beta", objectives_touched: 1 }),
      row({ course_slug: "a", course_title: "Alpha", objectives_touched: 4 }),
    ];
    expect(slugs(sortRows(rows, "objectives", defaultDirection("objectives")))).toEqual(["a", "b"]);
    expect(slugs(sortRows(rows, "objectives", "asc"))).toEqual(["b", "a"]);
    expect(slugs(sortRows(rows, "title", defaultDirection("title")))).toEqual(["a", "b"]);
  });

  it("ranks the current exam first and breaks ties by title", () => {
    const rows = [
      row({ course_slug: "o", course_title: "Older", currency: "older" }),
      row({ course_slug: "c", course_title: "Current", currency: "current" }),
      row({ course_slug: "u", course_title: "Another current", currency: "current" }),
    ];
    expect(slugs(sortRows(rows, "currency", "desc"))).toEqual(["u", "c", "o"]);
  });

  it("sorts a domain column by objectives touched, then minutes", () => {
    const cell = (objectives_touched: number, minutes: number) => [
      { domain_code: "2", lectures: 1, minutes, objectives_touched },
    ];
    const rows = [
      row({ course_slug: "x", course_title: "X", domains: cell(1, 90) }),
      row({ course_slug: "y", course_title: "Y", domains: cell(2, 10) }),
      row({ course_slug: "z", course_title: "Z", domains: [] }),
    ];
    expect(slugs(sortRows(rows, "domain:2", "desc"))).toEqual(["y", "x", "z"]);
  });
});
