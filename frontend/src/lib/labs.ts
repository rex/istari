/* Pure helpers for the verified-lab loop: where the owner is, and what the cluster chip says.
   Kept out of the component files so fast refresh stays whole and the logic is unit-testable. */

import type { VerifierStateView } from "@/lib/types-labs";

/** Where the owner is in the loop, read from the newest attempt and one local fact. */
export type LabPhase = "setup" | "work" | "check" | "passed" | "failed";

export function phaseOf(state: VerifierStateView, openedTerminal: boolean): LabPhase {
  const latest = state.attempts[0];
  if (!latest) return "setup";
  if (latest.checked_at === null) return openedTerminal ? "check" : "work";
  return latest.passed ? "passed" : "failed";
}

/** How a lab's grader is named, and what each step says, by its verifier backend. */
export interface GraderCopy {
  /** In a sentence: "the lab cluster", "the AWS emulator". */
  name: string;
  /** Opening a sentence: "The lab cluster", "The AWS emulator". */
  subject: string;
  /** At the start of a label: "Lab cluster", "AWS emulator". */
  label: string;
  /** What the lab needs when the backend is not configured: "a lab cluster". */
  needs: string;
  unconfigured: string;
  notFound: string;
  setupHint: string;
  /** The work happens in the learner's own shell (true) or in the backend's terminal. */
  ownShell: boolean;
  workTitle: string;
  checkHint: string;
  setupBusy: string;
  checkBusy: string;
  /** The backend's mode as the ready chip shows it. */
  mode: (mode: string) => string;
}

const CLUSTER_COPY: GraderCopy = {
  name: "the lab cluster",
  subject: "The lab cluster",
  label: "Lab cluster",
  needs: "a lab cluster",
  unconfigured: "No lab cluster configured",
  notFound: "Task not found on the instance",
  setupHint:
    "The backend runs the task's setup script and puts the cluster into the starting state. Takes a few seconds; up to 90.",
  ownShell: false,
  workTitle: "Work in the terminal",
  checkHint:
    "The backend runs the task's validate script against the live cluster and returns pass or fail with its reason. Up to 45 seconds.",
  setupBusy: "Running the setup script on the cluster…",
  checkBusy: "Running the validate script on the cluster…",
  mode: (mode) => ` · ${mode} mode`,
};

const EMULATOR_COPY: GraderCopy = {
  name: "the AWS emulator",
  subject: "The AWS emulator",
  label: "AWS emulator",
  needs: "the AWS emulator",
  unconfigured: "No AWS emulator configured",
  notFound: "Task not found in this Istari build",
  setupHint:
    "Istari creates the task's starting resources in the emulator and clears any earlier attempt. A few seconds.",
  ownShell: true,
  workTitle: "Work in your own shell",
  checkHint:
    "Istari reads the resources back from the emulator and grades each part of the task, with the reason for any miss. A few seconds.",
  setupBusy: "Creating the starting resources in the emulator…",
  checkBusy: "Reading the resources back from the emulator…",
  mode: (mode) => ` · ${mode}`,
};

export function graderCopy(backend: string): GraderCopy {
  return backend === "localemu" ? EMULATOR_COPY : CLUSTER_COPY;
}

export type ChipTone = "neutral" | "success" | "danger" | "warning";

export interface ClusterChip {
  tone: ChipTone;
  label: string;
  detail: string | null;
}

/** One line of truth about the lab's grader, in order of what blocks the owner first. */
export function clusterChip(state: VerifierStateView): ClusterChip {
  const copy = graderCopy(state.spec.backend);
  if (!state.configured) {
    return {
      tone: "neutral",
      label: copy.unconfigured,
      detail: state.message,
    };
  }
  if (!state.reachable) {
    return { tone: "danger", label: `${copy.label} unreachable`, detail: state.message };
  }
  if (state.unavailable_reason) {
    return {
      tone: "warning",
      label: "Task not available in this mode",
      detail: state.unavailable_reason,
    };
  }
  if (!state.profile_available || !state.task) {
    return { tone: "warning", label: copy.notFound, detail: state.message };
  }
  const mode = state.mode ? copy.mode(state.mode) : "";
  const session =
    state.session_profile && state.session_profile !== state.spec.profile
      ? `Setting up switches the cluster's session from ${state.session_profile} to ${state.spec.profile}.`
      : null;
  return { tone: "success", label: `${copy.label} ready${mode}`, detail: session };
}
