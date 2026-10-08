import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { TranscriptPanel } from "@/components/feature/TranscriptPanel";
import type { Cue } from "@/lib/vtt";

const cues: Cue[] = [
  { start: 0, end: 4, text: "Welcome to the course." },
  { start: 4, end: 9, text: "Today we cover IAM roles." },
  { start: 9, end: 15, text: "Roles beat long-term keys." },
];

describe("<TranscriptPanel />", () => {
  beforeAll(() => {
    Element.prototype.scrollIntoView = vi.fn();
  });

  it("highlights the cue at the current time and seeks on click", async () => {
    const onSeek = vi.fn();
    render(<TranscriptPanel cues={cues} currentTime={5} onSeek={onSeek} />);
    const active = screen.getByRole("button", { current: true });
    expect(active).toHaveTextContent("Today we cover IAM roles.");
    expect(active).toHaveTextContent("0:04");
    await userEvent.click(screen.getByRole("button", { name: /Roles beat/ }));
    expect(onSeek).toHaveBeenCalledWith(9);
  });

  it("filters cues by search text", async () => {
    render(<TranscriptPanel cues={cues} currentTime={0} onSeek={() => undefined} />);
    await userEvent.type(screen.getByLabelText("Search the transcript"), "roles");
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByText("2 of 3 cues match")).toBeInTheDocument();
  });

  it("says so when there are no captions", () => {
    render(<TranscriptPanel cues={[]} currentTime={0} onSeek={() => undefined} />);
    expect(screen.getByText("No captions for this lecture.")).toBeInTheDocument();
  });
});
