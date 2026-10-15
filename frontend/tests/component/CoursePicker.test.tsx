import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CoursePicker, TrackSwitch } from "@/components/feature/CoursePicker";
import type { TrackSummary } from "@/lib/types";

const cka: TrackSummary = {
  exam_version_id: 2,
  code: "CKA-1.35",
  name: "Certified Kubernetes Administrator (Kubernetes v1.35)",
  certification: "Certified Kubernetes Administrator",
  provider: "CNCF / The Linux Foundation",
  verification_status: "verified",
  checked_on: "2026-10-15",
  counts: { lessons: 0, questions: 0, cards: 0, labs: 36 },
  progress: { fraction: 14 / 36, sentence: "14 of 36 labs verified" },
  last_studied_at: new Date().toISOString(),
};
const dva: TrackSummary = {
  exam_version_id: 7,
  code: "DVA-C01-DRILL",
  name: "Developer Associate drills",
  certification: "AWS Certified Developer - Associate",
  provider: "Udemy course",
  verification_status: "unverified",
  checked_on: null,
  counts: { lessons: 0, questions: 130, cards: 0, labs: 0 },
  progress: null,
  last_studied_at: null,
};

describe("CoursePicker", () => {
  it("marks the current track, keeps one primary button and flags unverified metadata", () => {
    render(<CoursePicker tracks={[cka, dva]} currentId={2} value={2} onSelect={() => {}} />);
    const radios = screen.getAllByRole("radio");
    expect(radios).toHaveLength(2);
    expect(radios[0]).toHaveAttribute("aria-checked", "true");
    expect(screen.getByText("Current track")).toBeInTheDocument();
    expect(screen.getByText("Continue")).toHaveClass("btn--primary");
    expect(screen.getByText("Start")).toHaveClass("btn--secondary");
    expect(screen.getByText("14 of 36 labs verified")).toBeInTheDocument();
    expect(screen.getByText("exam metadata unverified")).toBeInTheDocument();
    expect(screen.getAllByText("Not started")).toHaveLength(2);
    expect(screen.getByText("36 labs")).toBeInTheDocument();
    expect(screen.getByText("130 questions")).toBeInTheDocument();
  });

  it("moves with the arrow keys and picks with Enter", () => {
    const onSelect = vi.fn();
    render(<CoursePicker tracks={[cka, dva]} currentId={2} value={2} onSelect={onSelect} />);
    const radios = screen.getAllByRole("radio");
    const first = radios[0] as HTMLElement;
    const second = radios[1] as HTMLElement;
    expect(first).toHaveAttribute("tabindex", "0");
    expect(second).toHaveAttribute("tabindex", "-1");
    fireEvent.keyDown(first, { key: "ArrowRight" });
    expect(onSelect).toHaveBeenLastCalledWith(7);
    fireEvent.keyDown(first, { key: "ArrowLeft" });
    expect(onSelect).toHaveBeenLastCalledWith(7);
    fireEvent.keyDown(second, { key: "Enter" });
    expect(onSelect).toHaveBeenLastCalledWith(7);
    fireEvent.click(first);
    expect(onSelect).toHaveBeenLastCalledWith(2);
  });
});

describe("TrackSwitch", () => {
  it("shows the code and name and reports whether the picker is open", () => {
    const onToggle = vi.fn();
    render(
      <TrackSwitch
        code="CKA-1.35"
        certification="Certified Kubernetes Administrator"
        open={false}
        onToggle={onToggle}
      />,
    );
    const chip = screen.getByRole("button", { name: /CKA-1.35/ });
    expect(chip).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(chip);
    expect(onToggle).toHaveBeenCalledTimes(1);
  });
});
