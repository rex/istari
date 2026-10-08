import { describe, expect, it } from "vitest";

import { cueIndexAt, formatClock, parseVtt } from "@/lib/vtt";

const VTT = `WEBVTT
Kind: captions

NOTE a comment

00:03.990 --> 00:05.280
Good morning, <i>my dear</i> students.

1
00:01:05.280 --> 00:01:08.490
Welcome to the fourth session.
Two lines.

00:01:08,490 --> 00:01:09,000
`;

describe("parseVtt", () => {
  it("reads cues with and without hours, joins lines, strips tags, drops empty cues", () => {
    const cues = parseVtt(VTT);
    expect(cues).toEqual([
      { start: 3.99, end: 5.28, text: "Good morning, my dear students." },
      { start: 65.28, end: 68.49, text: "Welcome to the fourth session. Two lines." },
    ]);
  });
});

describe("cueIndexAt", () => {
  const cues = parseVtt(VTT);
  it("finds the cue containing a time and -1 between or outside cues", () => {
    expect(cueIndexAt(cues, 4)).toBe(0);
    expect(cueIndexAt(cues, 5.28)).toBe(-1);
    expect(cueIndexAt(cues, 66)).toBe(1);
    expect(cueIndexAt(cues, 1000)).toBe(-1);
    expect(cueIndexAt([], 1)).toBe(-1);
  });
});

describe("formatClock", () => {
  it("formats minutes and hours", () => {
    expect(formatClock(0)).toBe("0:00");
    expect(formatClock(65.9)).toBe("1:05");
    expect(formatClock(3725)).toBe("1:02:05");
  });
});
