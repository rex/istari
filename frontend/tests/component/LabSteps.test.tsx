import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { LabResult, LabSteps } from "@/components/feature/LabSteps";
import { phaseOf } from "@/lib/labs";
import type { LabAttemptView, VerifierStateView } from "@/lib/types-labs";

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
  cli_env: [],
  task: {
    title: "A pod keeps crashing",
    context: "",
    description: "Make it run.",
    hint: "",
    weight: 4,
    requires: "",
  },
  unavailable_reason: null,
  message: null,
  attribution: "Task text from K16S, fetched live.",
  attempts: [],
  last_attempt: null,
};

function attempt(over: Partial<LabAttemptView> = {}): LabAttemptView {
  return {
    id: 1,
    setup_at: "2026-10-15T05:00:00+00:00",
    checked_at: null,
    passed: null,
    output: "",
    reason_line: "",
    duration_seconds: null,
    ...over,
  };
}

const noop = () => {};
const handlers = { onSetup: noop, onCheck: noop, onOpenTerminal: noop };

describe("phaseOf", () => {
  it("walks setup → work → check from the newest attempt and the terminal click", () => {
    expect(phaseOf(ready, false)).toBe("setup");
    const setUp = { ...ready, attempts: [attempt()] };
    expect(phaseOf(setUp, false)).toBe("work");
    expect(phaseOf(setUp, true)).toBe("check");
  });
  it("reports the verdict once the newest attempt is graded", () => {
    const failed = attempt({ checked_at: "2026-10-15T05:02:00+00:00", passed: false });
    const passed = attempt({ checked_at: "2026-10-15T05:02:00+00:00", passed: true });
    expect(phaseOf({ ...ready, attempts: [failed] }, true)).toBe("failed");
    expect(phaseOf({ ...ready, attempts: [passed] }, false)).toBe("passed");
  });
});

describe("<LabSteps />", () => {
  it("makes set-up the one primary action before anything ran, and keeps check disabled", () => {
    render(<LabSteps state={ready} phase="setup" busy={null} disabled={false} {...handlers} />);
    const setup = screen.getByRole("button", { name: "Set up environment" });
    expect(setup.className).toContain("btn--primary");
    expect(screen.getByRole("button", { name: "Check answer" })).toBeDisabled();
    expect(screen.getByRole("link", { name: /Open terminal/ }).className).toContain(
      "btn--secondary",
    );
  });

  it("hands the primary role to the terminal after setup, then to check once it was opened", () => {
    const state = { ...ready, attempts: [attempt({ output: "ready\n" })] };
    const { rerender } = render(
      <LabSteps state={state} phase="work" busy={null} disabled={false} {...handlers} />,
    );
    expect(screen.getByRole("link", { name: /Open terminal/ }).className).toContain("btn--primary");
    expect(screen.getByText(/Environment ready/)).toBeInTheDocument();
    rerender(<LabSteps state={state} phase="check" busy={null} disabled={false} {...handlers} />);
    expect(screen.getByRole("button", { name: "Check answer" }).className).toContain(
      "btn--primary",
    );
  });

  it("after a failed check offers check again as primary and set up again as secondary", () => {
    const onCheck = vi.fn();
    const failed = attempt({ checked_at: "2026-10-15T05:02:00+00:00", passed: false });
    render(
      <LabSteps
        state={{ ...ready, attempts: [failed] }}
        phase="failed"
        busy={null}
        disabled={false}
        {...handlers}
        onCheck={onCheck}
      />,
    );
    const again = screen.getByRole("button", { name: "Check again" });
    expect(again.className).toContain("btn--primary");
    expect(screen.getByRole("button", { name: "Set up again" }).className).toContain(
      "btn--secondary",
    );
    again.click();
    expect(onCheck).toHaveBeenCalledTimes(1);
  });

  it("disables every action while the cluster is blocked or a call is in flight", () => {
    render(<LabSteps state={ready} phase="setup" busy="setup" disabled={false} {...handlers} />);
    expect(screen.getByRole("button", { name: "Setting up…" })).toBeDisabled();
    render(
      <LabSteps
        state={{ ...ready, reachable: false }}
        phase="setup"
        busy={null}
        disabled={true}
        {...handlers}
      />,
    );
    expect(screen.getByRole("button", { name: "Set up environment" })).toBeDisabled();
  });

  it("for an AWS lab, works in the learner's own shell with the emulator's lines", () => {
    const aws: VerifierStateView = {
      ...ready,
      spec: { ...ready.spec, backend: "localemu", profile: "saa", question: "s3-lifecycle" },
      terminal_url: null,
      exam_url: null,
      cli_env: ["AWS_ENDPOINT_URL=http://localemu.test:4566", "AWS_DEFAULT_REGION=us-east-1"],
      attempts: [attempt()],
    };
    render(<LabSteps state={aws} phase="work" busy={null} disabled={false} {...handlers} />);
    expect(screen.getByText("Work in your own shell")).toBeInTheDocument();
    expect(screen.getByLabelText("Shell environment for the AWS CLI").textContent).toBe(
      "export AWS_ENDPOINT_URL=http://localemu.test:4566\nexport AWS_DEFAULT_REGION=us-east-1",
    );
    expect(screen.queryByRole("link", { name: /Open terminal/ })).toBeNull();
    expect(screen.getByText(/reads the resources back from the emulator/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Check answer" })).toBeEnabled();
  });

  it("never shows an AWS lab the cluster's terminal hint, even before the emulator is set", () => {
    const unset: VerifierStateView = {
      ...ready,
      spec: { ...ready.spec, backend: "localemu", profile: "saa" },
      configured: false,
      terminal_url: null,
      cli_env: [],
    };
    render(<LabSteps state={unset} phase="setup" busy={null} disabled={true} {...handlers} />);
    expect(screen.getByText("Work in your own shell")).toBeInTheDocument();
    expect(screen.queryByText(/control plane/)).toBeNull();
    expect(screen.queryByLabelText("Shell environment for the AWS CLI")).toBeNull();
  });
});

describe("<LabResult />", () => {
  it("shows the grader's verdict and reason line verbatim", () => {
    render(
      <LabResult
        attempt={attempt({
          checked_at: "2026-10-15T05:02:00+00:00",
          passed: false,
          output: "checking\nFAIL: pod web-0 is still CrashLoopBackOff\n",
          reason_line: "FAIL: pod web-0 is still CrashLoopBackOff",
          duration_seconds: 90,
        })}
      />,
    );
    expect(screen.getByText("Not yet")).toBeInTheDocument();
    expect(screen.getByText("FAIL: pod web-0 is still CrashLoopBackOff")).toBeInTheDocument();
    expect(screen.getByText(/90 seconds after setup/)).toBeInTheDocument();
  });
  it("renders nothing for an attempt that was never checked", () => {
    const { container } = render(<LabResult attempt={attempt()} />);
    expect(container).toBeEmptyDOMElement();
  });
});
