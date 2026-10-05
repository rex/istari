import { describe, expect, it } from "vitest";

import { clampText, formatDate, formatPercent, formatRelative, pluralize } from "@/lib/format";

describe("format", () => {
  it("formats percentages and handles missing evidence", () => {
    expect(formatPercent(0.3333)).toBe("33%");
    expect(formatPercent(0.5, 1)).toBe("50.0%");
    expect(formatPercent(null)).toBe("—");
  });

  it("renders dates in the configured timezone", () => {
    // 2026-10-06T04:30Z is still Oct 5 in Chicago.
    expect(formatDate("2026-10-06T04:30:00Z", "America/Chicago")).toContain("5");
    expect(formatDate("2026-10-06T04:30:00Z", "UTC")).toContain("6");
  });

  it("describes relative time without guilt", () => {
    const now = new Date("2026-10-05T20:00:00Z");
    expect(formatRelative("2026-10-05T20:00:30Z", now)).toBe("now");
    expect(formatRelative("2026-10-05T18:00:00Z", now)).toBe("2 h ago");
    expect(formatRelative("2026-10-08T20:00:00Z", now)).toBe("in 3 days");
    expect(formatRelative("2026-10-04T20:00:00Z", now)).toBe("yesterday");
  });

  it("pluralizes and clamps", () => {
    expect(pluralize(1, "card")).toBe("1 card");
    expect(pluralize(3, "card")).toBe("3 cards");
    expect(clampText("abcdef", 4)).toBe("abc…");
  });
});
