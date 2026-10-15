/* Verified labs: a lab's verifier reference, the backend's live state and the graded attempts.
   Mirrors backend/app/contracts/lab_verifier.py. */

export interface LabVerifierSpec {
  backend: string;
  profile: string;
  question: string;
  weight: number;
  time_limit_minutes: number | null;
}

export interface LabAttemptView {
  id: number;
  setup_at: string | null;
  checked_at: string | null;
  /** null until the check has run */
  passed: boolean | null;
  output: string;
  /** the grader's verdict line; empty until checked */
  reason_line: string;
  duration_seconds: number | null;
}

export interface LabAttemptSummary {
  checked_at: string;
  passed: boolean;
  reason_line: string;
}

export interface VerifierTaskView {
  title: string;
  context: string;
  description: string;
  hint: string;
  weight: number;
  requires: string;
}

export interface VerifierStateView {
  spec: LabVerifierSpec;
  configured: boolean;
  reachable: boolean;
  mode: string | null;
  profile_available: boolean;
  session_profile: string | null;
  terminal_url: string | null;
  exam_url: string | null;
  map_url: string | null;
  task: VerifierTaskView | null;
  unavailable_reason: string | null;
  message: string | null;
  attribution: string;
  attempts: LabAttemptView[];
  last_attempt: LabAttemptView | null;
}

export interface SetupResponse {
  ok: boolean;
  output: string;
  unavailable_reason: string | null;
  attempt: LabAttemptView | null;
}

export interface CheckResponse {
  passed: boolean;
  output: string;
  reason_line: string;
  unavailable_reason: string | null;
  attempt: LabAttemptView | null;
}
