import type { ReactNode } from "react";

import { Button } from "@/components/ui/Button";
import { formatRelative, pluralize } from "@/lib/format";
import { graderCopy, type LabPhase } from "@/lib/labs";
import type { LabAttemptView, VerifierStateView } from "@/lib/types-labs";

export type Busy = "setup" | "check" | null;

interface LabStepsProps {
  state: VerifierStateView;
  phase: LabPhase;
  busy: Busy;
  disabled: boolean;
  onSetup: () => void;
  onCheck: () => void;
  onOpenTerminal: () => void;
}

function Step({
  number,
  title,
  status,
  children,
}: {
  number: number;
  title: string;
  status: "todo" | "current" | "done";
  children?: ReactNode;
}) {
  return (
    <li
      className={`labsteps__step is-${status}`}
      aria-current={status === "current" ? "step" : undefined}
    >
      <span className="labsteps__num" aria-hidden="true">
        {status === "done" ? "✓" : number}
      </span>
      <div className="labsteps__body">
        <div className="labsteps__title">{title}</div>
        {children}
      </div>
    </li>
  );
}

function statusFor(step: 1 | 2 | 3, phase: LabPhase): "todo" | "current" | "done" {
  const current: Record<LabPhase, 1 | 2 | 3> = {
    setup: 1,
    work: 2,
    check: 3,
    passed: 3,
    failed: 3,
  };
  const at = current[phase];
  if (step < at) return "done";
  if (step === at) return "current";
  return "todo";
}

/** Three steps, one obvious primary action at each: set up, work in the terminal, check. */
export function LabSteps({
  state,
  phase,
  busy,
  disabled,
  onSetup,
  onCheck,
  onOpenTerminal,
}: LabStepsProps) {
  const latest = state.attempts[0];
  const settled = phase === "passed" || phase === "failed";
  const setupLabel = latest ? "Set up again" : "Set up environment";
  const terminal = state.terminal_url;
  const copy = graderCopy(state.spec.backend);
  return (
    <ol className="labsteps list-reset" aria-label="Lab steps">
      <Step number={1} title="Set up the environment" status={statusFor(1, phase)}>
        <p className="labsteps__hint">{copy.setupHint}</p>
        {phase === "setup" || settled ? (
          <div className="labsteps__action">
            <Button
              variant={phase === "setup" ? "primary" : "secondary"}
              onClick={onSetup}
              busy={busy === "setup"}
              disabled={disabled || busy !== null}
            >
              {busy === "setup" ? "Setting up…" : setupLabel}
            </Button>
          </div>
        ) : latest?.setup_at ? (
          <p className="labsteps__note">
            Environment ready {formatRelative(latest.setup_at)}.
            {latest.output ? (
              <details className="labsteps__output">
                <summary>Setup output</summary>
                <pre className="labresult__reason">{latest.output}</pre>
              </details>
            ) : null}
          </p>
        ) : null}
      </Step>
      <Step number={2} title={copy.workTitle} status={statusFor(2, phase)}>
        {copy.ownShell ? (
          <>
            <p className="labsteps__hint">
              Paste the emulator's lines into your shell so the AWS CLI talks to it, then do the
              task with <code>aws</code>. Nothing here touches a real AWS account.
            </p>
            {state.cli_env.length > 0 ? (
              <pre className="labresult__reason" aria-label="Shell environment for the AWS CLI">
                {state.cli_env.map((line) => `export ${line}`).join("\n")}
              </pre>
            ) : null}
          </>
        ) : (
          <p className="labsteps__hint">
            A root shell on the control plane, in a new tab. Workers answer to{" "}
            <code>ssh node01</code> and <code>ssh node02</code>.
          </p>
        )}
        {terminal ? (
          <div className="labsteps__action">
            <a
              className={`btn ${phase === "work" ? "btn--primary" : "btn--secondary"}`}
              href={terminal}
              target="_blank"
              rel="noopener noreferrer"
              onClick={onOpenTerminal}
              aria-disabled={disabled || undefined}
            >
              Open terminal ↗
            </a>
            {state.map_url ? (
              <a
                className="btn btn--ghost"
                href={state.map_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                Cluster map ↗
              </a>
            ) : null}
          </div>
        ) : null}
      </Step>
      <Step number={3} title="Check the answer" status={statusFor(3, phase)}>
        <p className="labsteps__hint">{copy.checkHint}</p>
        <div className="labsteps__action">
          <Button
            variant={phase === "check" || phase === "failed" ? "primary" : "secondary"}
            onClick={onCheck}
            busy={busy === "check"}
            disabled={disabled || busy !== null || phase === "setup"}
          >
            {busy === "check" ? "Checking…" : settled ? "Check again" : "Check answer"}
          </Button>
        </div>
      </Step>
    </ol>
  );
}

/** The verdict, verbatim from the grader. Never a percentage, never a guess. */
export function LabResult({ attempt }: { attempt: LabAttemptView }) {
  if (attempt.checked_at === null || attempt.passed === null) return null;
  const passed = attempt.passed;
  const when = formatRelative(attempt.checked_at);
  const took =
    attempt.duration_seconds !== null
      ? ` · ${pluralize(attempt.duration_seconds, "second")} after setup`
      : "";
  return (
    <section
      className={`labresult ${passed ? "labresult--pass" : "labresult--fail"}`}
      role="status"
      aria-live="polite"
    >
      <p className="labresult__verdict">{passed ? "Passed" : "Not yet"}</p>
      {attempt.reason_line ? <pre className="labresult__reason">{attempt.reason_line}</pre> : null}
      <p className="labresult__meta">
        Checked {when}
        {took}.
      </p>
      {attempt.output.trim() && attempt.output.trim() !== attempt.reason_line ? (
        <details className="labsteps__output">
          <summary>Full grader output</summary>
          <pre className="labresult__reason">{attempt.output}</pre>
        </details>
      ) : null}
    </section>
  );
}
