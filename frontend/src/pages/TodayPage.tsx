import { useQuery, useSuspenseQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";

import { PlanBlocks } from "@/components/feature/PlanCard";
import { Button } from "@/components/ui/Button";
import { Segmented } from "@/components/ui/Segmented";
import { Spinner } from "@/components/ui/Spinner";
import { StateBlock } from "@/components/ui/StateBlock";
import { formatPercent } from "@/lib/format";
import type { PlanBlockView, SessionMinutes } from "@/lib/types";
import { meQueryOptions } from "@/queries/auth";
import { todayQueryOptions, useCreateSession } from "@/queries/study";

const MINUTES = [
  { value: 5, label: "5 min" },
  { value: 15, label: "15 min" },
  { value: 30, label: "30 min" },
] as const;

export default function TodayPage() {
  const navigate = useNavigate();
  const { data: me } = useSuspenseQuery(meQueryOptions());
  const [minutes, setMinutes] = useState<SessionMinutes>(
    (me.settings.preferred_session_minutes as SessionMinutes) || 15,
  );
  const today = useQuery(todayQueryOptions(minutes));
  const createSession = useCreateSession();

  const start = (block: PlanBlockView | undefined, withMinutes: SessionMinutes) => {
    if (!block) return;
    if (block.kind === "resume" && block.session_id) {
      void navigate({
        to: "/practice/$sessionId",
        params: { sessionId: String(block.session_id) },
      });
    } else if (block.kind === "review") {
      void navigate({ to: "/review", search: { limit: block.count } });
    } else if (block.kind === "lesson" && block.item_key) {
      void navigate({ to: "/learn/$key", params: { key: block.item_key } });
    } else {
      createSession.mutate(
        {
          kind: "practice",
          minutes: withMinutes,
          focus: block.focus ?? "mixed",
          replace_active: false,
        },
        {
          onSuccess: (session) =>
            void navigate({
              to: "/practice/$sessionId",
              params: { sessionId: String(session.id) },
            }),
        },
      );
    }
  };

  if (today.isPending) return <Spinner label="Working out what is next" />;
  if (today.isError) {
    return (
      <StateBlock
        tone="error"
        title="Could not load today's plan"
        body={today.error.message}
        action={<Button onClick={() => void today.refetch()}>Try again</Button>}
      />
    );
  }
  const plan = today.data;
  const primary = plan.blocks[0];
  const primaryLabel = primary
    ? primary.kind === "resume"
      ? "Resume"
      : primary.kind === "review"
        ? `Review ${primary.count} card${primary.count === 1 ? "" : "s"}`
        : primary.kind === "lesson"
          ? "Read the lesson"
          : "Start"
    : null;

  return (
    <div className="with-rail">
      <section className="hero">
        <div>
          <p className="card__eyebrow">Today</p>
          <h1 className="hero__headline">{plan.headline}</h1>
          {plan.quiet_win ? <p className="quiet-win">{plan.quiet_win}</p> : null}
        </div>
        <div className="hero__actions">
          {primary ? (
            <Button
              variant="primary"
              size="lg"
              onClick={() => start(primary, minutes)}
              busy={createSession.isPending}
            >
              {primaryLabel}
            </Button>
          ) : null}
          <Segmented
            name="today-minutes"
            label="Session length"
            options={MINUTES}
            value={minutes}
            onChange={setMinutes}
          />
          {primary && primary.kind !== "resume" ? (
            <Button
              variant="ghost"
              onClick={() => start(plan.blocks.find((b) => b.kind !== "lesson") ?? primary, 5)}
            >
              I have five minutes
            </Button>
          ) : null}
        </div>
        {createSession.isError ? (
          <p className="save-status save-status--error" role="alert">
            Could not start: {createSession.error.message}
          </p>
        ) : null}
        <PlanBlocks blocks={plan.blocks} />
        {plan.blocks.length === 0 ? (
          <StateBlock
            title="Nothing to do for this track yet"
            body="Import a content pack (make seed) or check Settings → Content."
          />
        ) : null}
        <ul className="hero__explain">
          {plan.explanation.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </section>
      <aside className="with-rail__rail stack">
        {plan.exam ? (
          <div className="card card--quiet stat">
            <span className="stat__label">{plan.exam.code}</span>
            <span className="stat__value">
              {plan.exam.days_left === null ? "—" : plan.exam.days_left}
            </span>
            <span className="stat__note">
              {plan.exam.exam_date ? `days until ${plan.exam.exam_date}` : "no exam date set"}
            </span>
          </div>
        ) : null}
        <div className="card card--quiet stack">
          <div className="stat">
            <span className="stat__label">Due reviews</span>
            <span className="stat__value">{plan.due_reviews}</span>
            <span className="stat__note">
              {plan.reviews_remaining_today} left under today's limit
            </span>
          </div>
          <div className="stat">
            <span className="stat__label">Last 7 days</span>
            <span className="stat__value">{plan.recent.answers_7d}</span>
            <span className="stat__note">
              questions · {plan.recent.reviews_7d} reviews · {plan.recent.lessons_completed}/
              {plan.recent.lessons_total} lessons read
            </span>
          </div>
        </div>
        {plan.weakest.length > 0 ? (
          <div className="card card--quiet">
            <p className="card__eyebrow">Weakest objectives</p>
            <ul className="list-reset small">
              {plan.weakest.map((w) => (
                <li key={w.code}>
                  <strong>{w.code}</strong> {w.title}{" "}
                  <span className="muted">
                    {w.first_correct}/{w.first_attempts} ({formatPercent(w.accuracy)})
                  </span>
                </li>
              ))}
            </ul>
            <Link to="/progress" className="small">
              See progress
            </Link>
          </div>
        ) : null}
      </aside>
    </div>
  );
}
