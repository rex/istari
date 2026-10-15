import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LabTask } from "@/components/feature/LabTask";
import { clusterChip } from "@/lib/labs";
import type { VerifierStateView } from "@/lib/types-labs";

const ready: VerifierStateView = {
  spec: {
    backend: "k16s",
    profile: "cka",
    question: "stub-01",
    weight: 4,
    time_limit_minutes: null,
  },
  configured: true,
  reachable: true,
  mode: "full",
  profile_available: true,
  session_profile: null,
  terminal_url: "http://k16s.lan:8080/terminal/",
  exam_url: "http://k16s.lan:8080/",
  map_url: null,
  task: {
    title: "A pod keeps crashing",
    context: "Namespace apps, pod web-0.",
    description: "Find out why it crashes.\nMake it stay Running.",
    hint: "Look at the last termination reason.",
    weight: 4,
    requires: "",
  },
  unavailable_reason: null,
  message: null,
  attribution: "Task text from K16S, fetched live.",
  attempts: [],
  last_attempt: null,
};

describe("clusterChip", () => {
  it("names the first thing that blocks the owner", () => {
    expect(clusterChip({ ...ready, configured: false, message: "set K16S_BASE_URL" })).toEqual({
      tone: "neutral",
      label: "No lab cluster configured",
      detail: "set K16S_BASE_URL",
    });
    expect(clusterChip({ ...ready, reachable: false, message: "did not answer" }).tone).toBe(
      "danger",
    );
    expect(clusterChip({ ...ready, unavailable_reason: "needs the full install" }).label).toBe(
      "Task not available in this mode",
    );
    expect(clusterChip({ ...ready, task: null, profile_available: false }).tone).toBe("warning");
  });
  it("says when a setup will switch the cluster's session", () => {
    const chip = clusterChip({ ...ready, session_profile: "cka2" });
    expect(chip.tone).toBe("success");
    expect(chip.label).toBe("Lab cluster ready · full mode");
    expect(chip.detail).toContain("from cka2 to cka");
    expect(clusterChip({ ...ready, session_profile: "cka" }).detail).toBeNull();
  });
});

describe("<LabTask />", () => {
  it("shows the live task with its context, hint and attribution", () => {
    render(<LabTask state={ready} />);
    expect(screen.getByRole("heading", { name: "A pod keeps crashing" })).toBeInTheDocument();
    expect(screen.getByText("Namespace apps, pod web-0.")).toBeInTheDocument();
    expect(screen.getByText(/Make it stay Running/)).toBeInTheDocument();
    expect(screen.getByText("Show the hint")).toBeInTheDocument();
    expect(screen.getByText(/Task · cka · weight 4/)).toBeInTheDocument();
    expect(screen.getByText("Task text from K16S, fetched live.")).toBeInTheDocument();
  });
  it("explains instead of inventing text when the cluster has no task to give", () => {
    render(
      <LabTask state={{ ...ready, task: null, message: "The instance does not serve cka." }} />,
    );
    expect(screen.getByRole("heading", { name: "Task text is not available" })).toBeInTheDocument();
    expect(screen.getByText("The instance does not serve cka.")).toBeInTheDocument();
  });
});
