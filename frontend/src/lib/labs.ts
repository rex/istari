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

export type ChipTone = "neutral" | "success" | "danger" | "warning";

export interface ClusterChip {
  tone: ChipTone;
  label: string;
  detail: string | null;
}

/** One line of truth about the lab cluster, in order of what blocks the owner first. */
export function clusterChip(state: VerifierStateView): ClusterChip {
  if (!state.configured) {
    return { tone: "neutral", label: "No lab cluster configured", detail: state.message };
  }
  if (!state.reachable) {
    return { tone: "danger", label: "Lab cluster unreachable", detail: state.message };
  }
  if (state.unavailable_reason) {
    return {
      tone: "warning",
      label: "Task not available in this mode",
      detail: state.unavailable_reason,
    };
  }
  if (!state.profile_available || !state.task) {
    return { tone: "warning", label: "Task not found on the instance", detail: state.message };
  }
  const mode = state.mode ? ` · ${state.mode} mode` : "";
  const session =
    state.session_profile && state.session_profile !== state.spec.profile
      ? `Setting up switches the cluster's session from ${state.session_profile} to ${state.spec.profile}.`
      : null;
  return { tone: "success", label: `Lab cluster ready${mode}`, detail: session };
}
