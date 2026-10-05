import { useSuspenseQuery } from "@tanstack/react-query";
import { useParams } from "@tanstack/react-router";
import { useEffect, useState } from "react";

import { QuestionRunner } from "@/components/feature/QuestionRunner";
import { SessionSummary } from "@/components/feature/SessionSummary";
import { sessionQueryOptions, useSessionAction } from "@/queries/study";
import { useUIStore } from "@/stores/ui";

export default function SessionPage() {
  const { sessionId = "" } = useParams({ strict: false });
  const id = Number(sessionId);
  const { data: session } = useSuspenseQuery(sessionQueryOptions(id));
  const complete = useSessionAction("complete");
  const setFocusMode = useUIStore((s) => s.setFocusMode);

  const firstPending =
    session.items.find((i) => i.state === "pending")?.position ?? session.items.length;
  const [position, setPosition] = useState(firstPending);
  const [showSummary, setShowSummary] = useState(session.status === "completed");
  // Bumped when another tab changed the draft; remounts the runner with fresh data.
  const [reloadToken, setReloadToken] = useState(0);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    setFocusMode(true);
    return () => setFocusMode(false);
  }, [setFocusMode]);

  const item = session.items.find((i) => i.position === position) ?? session.items[0];
  const allAnswered = session.items.every((i) => i.state === "answered");

  const goTo = (p: number) => {
    setNotice(null);
    setPosition(p);
  };
  const next = () => {
    const pending =
      session.items.find((i) => i.state === "pending" && i.position > position) ??
      session.items.find((i) => i.state === "pending");
    if (pending) goTo(pending.position);
    else if (session.status === "completed") setShowSummary(true);
  };
  const finish = () => complete.mutate(id, { onSuccess: () => setShowSummary(true) });
  const onStale = () => {
    setNotice("Updated in another tab — reloaded the latest draft.");
    setReloadToken((n) => n + 1);
  };

  if (!item) return <p>This session has no items.</p>;
  if (showSummary && session.status === "completed") {
    return (
      <SessionSummary
        session={session}
        onReview={(p) => {
          goTo(p);
          setShowSummary(false);
        }}
      />
    );
  }

  return (
    <div className="stack">
      <div className="spread small muted">
        <span>
          {session.kind === "assessment" ? "Assessment" : "Practice"} · {session.answered_count}/
          {session.total} answered
          {session.status === "completed" ? " · completed" : ""}
        </span>
        <span className="cluster">
          {session.items.map((i) => (
            <button
              key={i.position}
              type="button"
              className={`btn btn--ghost btn--sm ${i.position === position ? "btn--secondary" : ""}`}
              aria-current={i.position === position ? "step" : undefined}
              onClick={() => goTo(i.position)}
            >
              {i.state === "answered" ? "●" : "○"} {i.position}
            </button>
          ))}
        </span>
      </div>
      {notice ? (
        <p className="save-status save-status--stale" role="status">
          {notice}
        </p>
      ) : null}
      <QuestionRunner
        key={`${item.position}:${reloadToken}`}
        session={session}
        item={item}
        allAnswered={allAnswered}
        finishing={complete.isPending}
        onNext={next}
        onFinish={finish}
        onShowSummary={() => setShowSummary(true)}
        onStale={onStale}
      />
    </div>
  );
}
