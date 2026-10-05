import { useQuery, useSuspenseQuery } from "@tanstack/react-query";
import { Link, useSearch } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { StateBlock } from "@/components/ui/StateBlock";
import { Markdown } from "@/lib/Markdown";
import { newRequestId } from "@/lib/api";
import { useShortcuts, type ShortcutBinding } from "@/lib/shortcuts";
import type { CardView } from "@/lib/types";
import { meQueryOptions } from "@/queries/auth";
import { dueQueryOptions, useRateCard } from "@/queries/review";
import { useUIStore } from "@/stores/ui";

const RATINGS = [
  { value: 1, label: "Again", key: "1" },
  { value: 2, label: "Hard", key: "2" },
  { value: 3, label: "Good", key: "3" },
  { value: 4, label: "Easy", key: "4" },
] as const;

const elapsedSince = (startedAt: number): number => Date.now() - startedAt;
const now = (): number => Date.now();

export default function ReviewPage() {
  const search = useSearch({ strict: false });
  const { data: me } = useSuspenseQuery(meQueryOptions());
  const due = useQuery(dueQueryOptions(search.limit));
  const rate = useRateCard();
  const setFocusMode = useUIStore((s) => s.setFocusMode);
  // The queue is derived: the fetched list minus the cards rated this visit.
  const [done, setDone] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [requestId, setRequestId] = useState<string | null>(null);
  const shownAt = useRef<number>(0);

  useEffect(() => {
    setFocusMode(true);
    return () => setFocusMode(false);
  }, [setFocusMode]);

  const queue: CardView[] | null = due.data ? due.data.cards.slice(done) : null;
  const current = queue?.[0];
  const currentId = current?.id;
  useEffect(() => {
    shownAt.current = now();
  }, [currentId]);

  const doRate = (rating: 1 | 2 | 3 | 4) => {
    if (!current || !revealed || rate.isPending) return;
    const rid = requestId ?? newRequestId();
    setRequestId(rid);
    rate.mutate(
      {
        cardId: current.id,
        rating,
        duration_ms: elapsedSince(shownAt.current),
        request_id: rid,
      },
      {
        onSuccess: () => {
          setRequestId(null);
          setRevealed(false);
          setDone((n) => n + 1);
        },
      },
    );
  };

  const bindings = useMemo<ShortcutBinding[]>(
    () => [
      { key: " ", description: "Reveal", handler: () => setRevealed(true) },
      {
        key: "Enter",
        description: "Reveal",
        allowOnControls: false,
        handler: () => setRevealed(true),
      },
      ...RATINGS.map((r) => ({ key: r.key, description: r.label, handler: () => doRate(r.value) })),
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps -- doRate reads fresh state via closure each render
    [current, revealed, rate.isPending],
  );
  useShortcuts(bindings, Boolean(current));

  if (due.isPending || queue === null) return <Spinner label="Fetching due cards" />;
  if (due.isError)
    return <StateBlock tone="error" title="Could not load reviews" body={due.error.message} />;
  const info = due.data;

  if (!current) {
    return (
      <StateBlock
        tone="success"
        title={done > 0 ? `${done} card${done === 1 ? "" : "s"} reviewed` : "Nothing due right now"}
        body={
          <>
            <p>
              {info.due_total - done > 0
                ? `${info.due_total - done} more are due, but today's limit (${info.daily_limit}) or the session cap holds them back. That is fine.`
                : "Come back when the scheduler says so. Reviews are due, never overdue."}
            </p>
            {info.backlog_mode === "recovery" ? (
              <p className="small muted">Backlog recovery mode: ten at a time, oldest first.</p>
            ) : null}
          </>
        }
        action={
          <span className="cluster">
            <Link to="/" className="btn btn--primary">
              Back to Today
            </Link>
            <Link to="/review/cards" className="btn btn--ghost">
              Manage cards
            </Link>
          </span>
        }
      />
    );
  }

  return (
    <div className="flashcard">
      <div className="flashcard__counter">
        <span>
          Card {done + 1} of {queue.length + done} · {info.reviewed_today + done} reviewed today
        </span>
        <span>
          {current.objectives.map((o) => o.code).join(" · ")} · due{" "}
          {current.due_local.replace("T", " ")}
          {current.source_kind !== "flashcard" ? ` · from a ${current.source_kind}` : ""}
        </span>
      </div>
      <div className="flashcard__face" aria-live="polite">
        <Markdown>{current.front_md}</Markdown>
      </div>
      {revealed ? (
        <div className="flashcard__face flashcard__face--back">
          <Markdown>{current.back_md}</Markdown>
        </div>
      ) : (
        <div className="study-actions" style={{ marginTop: "1rem" }}>
          <Button variant="primary" size="lg" onClick={() => setRevealed(true)}>
            Reveal
          </Button>
          <span className="muted small">Space or Enter</span>
        </div>
      )}
      {revealed ? (
        <div className="rating" role="group" aria-label="Rate your recall">
          {RATINGS.map((r) => (
            <Button
              key={r.value}
              variant={r.value === 3 ? "primary" : "secondary"}
              onClick={() => doRate(r.value)}
              busy={rate.isPending}
            >
              {r.label}
              <span className="rating__key">{r.key}</span>
            </Button>
          ))}
        </div>
      ) : null}
      {rate.isError ? (
        <p className="save-status save-status--error" role="alert">
          Rating not saved — {rate.error.message}. Press the rating again to retry.
        </p>
      ) : null}
      <p className="muted small" style={{ marginTop: "1rem" }}>
        Times shown in {me.settings.timezone}. Scheduling by py-fsrs; ratings are about recall, not
        quiz confidence.
      </p>
    </div>
  );
}
