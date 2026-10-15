import { Badge } from "@/components/ui/Badge";
import { formatDateTime, pluralize } from "@/lib/format";
import type { LabAttemptView } from "@/lib/types-labs";

/** Every attempt, newest first. Failures stay visible: they are attempts, not blemishes. */
export function LabAttempts({
  attempts,
  timeZone,
}: {
  attempts: LabAttemptView[];
  timeZone: string;
}) {
  if (attempts.length === 0) {
    return <p className="muted small">No attempts yet. The first setup starts the record.</p>;
  }
  return (
    <ol className="labattempts list-reset" aria-label="Attempts">
      {attempts.map((attempt) => {
        const stamp = attempt.checked_at ?? attempt.setup_at;
        return (
          <li key={attempt.id} className="labattempt">
            <span className="labattempt__badge">
              {attempt.checked_at === null ? (
                <Badge>set up</Badge>
              ) : attempt.passed ? (
                <Badge tone="success">passed</Badge>
              ) : (
                <Badge tone="danger">failed</Badge>
              )}
            </span>
            <span className="labattempt__body">
              <span className="labattempt__when">
                {stamp ? formatDateTime(stamp, timeZone) : "—"}
                {attempt.duration_seconds !== null
                  ? ` · ${pluralize(attempt.duration_seconds, "second")}`
                  : ""}
              </span>
              {attempt.reason_line ? (
                <code className="labattempt__reason" title={attempt.reason_line}>
                  {attempt.reason_line}
                </code>
              ) : null}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
