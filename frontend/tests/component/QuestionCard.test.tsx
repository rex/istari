import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { QuestionCard } from "@/components/feature/QuestionCard";
import type { SessionItemView } from "@/lib/types";

const item: SessionItemView = {
  position: 2,
  item_key: "q-1",
  family_key: "q-1",
  stem_md: "Which service fits?",
  select_count: 2,
  difficulty: "medium",
  objectives: [{ code: "1.1", title: "Secure access", domain_code: "1" }],
  options: [
    { id: "o3", text_md: "Third" },
    { id: "o1", text_md: "First" },
    { id: "o2", text_md: "Second" },
  ],
  state: "pending",
  draft_selection: null,
  draft_confidence: null,
  answer: null,
  feedback: null,
};

describe("<QuestionCard />", () => {
  it("shows options in the server order with positional keys, never letters as ids", async () => {
    const onToggle = vi.fn();
    render(
      <QuestionCard
        item={item}
        total={5}
        selected={[]}
        onToggle={onToggle}
        confidence={null}
        onConfidence={() => {}}
        locked={false}
      />,
    );
    const boxes = screen.getAllByRole("checkbox");
    expect(boxes.map((b) => b.textContent)).toEqual(["1Third", "2First", "3Second"]);
    expect(screen.getByText(/Choose 2/)).toBeInTheDocument();
    await userEvent.click(boxes[1]!);
    expect(onToggle).toHaveBeenCalledWith("o1");
  });

  it("marks correct and wrong options once feedback exists and locks input", () => {
    const answered: SessionItemView = {
      ...item,
      state: "answered",
      answer: {
        selected_option_ids: ["o1", "o2"],
        is_correct: false,
        confidence: "confident",
        first_attempt: true,
        answered_at: "2026-10-05T20:00:00Z",
      },
      feedback: {
        correct_option_ids: ["o1", "o3"],
        explanation_md: "because",
        distractor_rationales: { o2: "nope" },
        decisive_constraint: "the constraint",
        objectives: [],
        sources: [],
        missed_option_ids: ["o3"],
        extra_option_ids: ["o2"],
      },
    };
    render(
      <QuestionCard
        item={answered}
        total={5}
        selected={[]}
        onToggle={() => {}}
        confidence={null}
        onConfidence={() => {}}
        locked
      />,
    );
    const boxes = screen.getAllByRole("checkbox");
    expect(boxes[0]).toHaveClass("is-correct");
    expect(boxes[1]).toHaveClass("is-correct");
    expect(boxes[2]).toHaveClass("is-wrong");
    expect(boxes.every((b) => (b as HTMLButtonElement).disabled)).toBe(true);
    expect(screen.queryByText(/How sure/)).toBeNull();
  });
});
