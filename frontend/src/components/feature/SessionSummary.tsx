import { Link } from "@tanstack/react-router";

import { Button } from "@/components/ui/Button";
import { formatPercent } from "@/lib/format";
import type { SessionView } from "@/lib/types";

interface SessionSummaryProps {
  session: SessionView;
  onReview: (position: number) => void;
}

export function SessionSummary({ session, onReview }: SessionSummaryProps) {
  const answered = session.items.filter((i) => i.answer);
  const correct = session.correct_count ?? 0;
  const firstAttempts = answered.filter((i) => i.answer?.first_attempt).length;
  const confidentMisses = answered.filter(
    (i) => i.answer?.is_correct === false && i.answer.confidence === "confident",
  );
  return (
    <section className="card">
      <p className="card__eyebrow">
        {session.kind === "assessment" ? "Assessment" : "Practice"} complete
      </p>
      <p className="summary-score">
        {correct} / {answered.length}
      </p>
      <p className="dim">
        {formatPercent(answered.length ? correct / answered.length : null)} on this set ·{" "}
        {firstAttempts} first attempt{firstAttempts === 1 ? "" : "s"},{" "}
        {answered.length - firstAttempts} repeat{answered.length - firstAttempts === 1 ? "" : "s"}.
        {session.kind === "practice" ? " Repeated practice is not exam evidence." : ""}
      </p>
      {confidentMisses.length > 0 ? (
        <p className="dim small">
          {confidentMisses.length} confident mistake{confidentMisses.length === 1 ? "" : "s"} —
          these surface first next time.
        </p>
      ) : null}
      <ol className="summary-list">
        {session.items.map((item) => (
          <li key={item.position}>
            <span className={item.answer?.is_correct ? "ok" : "miss"} aria-hidden="true">
              {item.answer ? (item.answer.is_correct ? "✓" : "✗") : "–"}
            </span>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => onReview(item.position)}
            >
              <span className="sr-only">
                Question {item.position}: {item.answer?.is_correct ? "correct" : "incorrect"}.{" "}
              </span>
              {item.objectives.map((o) => o.code).join(", ")} · {item.item_key}
            </button>
          </li>
        ))}
      </ol>
      <div className="cluster">
        <Link to="/" className="btn btn--primary">
          Back to Today
        </Link>
        <Link to="/practice" className="btn btn--secondary">
          Another session
        </Link>
        <Button variant="ghost" onClick={() => onReview(1)}>
          Walk through the answers
        </Button>
      </div>
    </section>
  );
}
