import { useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Kbd } from "@/components/ui/Kbd";
import { CURRENCY_LABEL, CURRENCY_TONE } from "@/lib/comparison";
import type { CourseDecision, ReviewQueueView } from "@/lib/types-lectures";

type Scope = "section" | "course";

/** Where the lecture sits in the queue, and the decisions that take a whole section or
 *  course at once. Excluding asks twice; accepting does not. */
export function ReviewWhole({
  queue,
  busy,
  onDecide,
}: {
  queue: ReviewQueueView;
  busy: boolean;
  onDecide: (decision: CourseDecision) => void;
}) {
  const [confirming, setConfirming] = useState<Scope | null>(null);
  const lecture = queue.lecture;
  if (!lecture) return null;
  const decision = (scope: Scope, exclude: boolean): CourseDecision => ({
    course_slug: lecture.course_slug,
    ...(scope === "section" ? { section_title: lecture.section_title } : {}),
    exclude,
  });
  const exclude = (scope: Scope) => {
    if (confirming === scope) {
      setConfirming(null);
      onDecide(decision(scope, true));
    } else {
      setConfirming(scope);
    }
  };
  const count = (scope: Scope) =>
    scope === "section" ? queue.section_pending : queue.course_pending;

  return (
    <div className="stack" aria-label="Whole section or course">
      <p className="cluster small muted" style={{ margin: 0 }}>
        <span>
          Course {queue.course_index ?? "?"} of {queue.courses_pending}
        </span>
        {queue.course_currency ? (
          <Badge tone={CURRENCY_TONE[queue.course_currency]}>
            {CURRENCY_LABEL[queue.course_currency]}
          </Badge>
        ) : null}
        <span>{queue.course_pending} left in this course</span>
        <span>{queue.section_pending} in this section</span>
      </p>
      <div className="cluster">
        <Button
          size="sm"
          variant="secondary"
          disabled={busy}
          onClick={() => onDecide(decision("section", false))}
        >
          Accept the rest of this section <Kbd>s</Kbd>
        </Button>
        <Button
          size="sm"
          variant="secondary"
          disabled={busy}
          onClick={() => onDecide(decision("course", false))}
        >
          Accept the rest of this course <Kbd>c</Kbd>
        </Button>
        {(["section", "course"] as const).map((scope) => (
          <Button
            key={scope}
            size="sm"
            variant={confirming === scope ? "primary" : "ghost"}
            disabled={busy}
            onClick={() => exclude(scope)}
          >
            {confirming === scope
              ? `Yes, exclude ${count(scope)} lectures`
              : `Exclude this ${scope}`}
          </Button>
        ))}
        {confirming ? (
          <Button size="sm" variant="ghost" onClick={() => setConfirming(null)}>
            Cancel
          </Button>
        ) : null}
      </div>
    </div>
  );
}
