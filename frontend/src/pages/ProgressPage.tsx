import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";

import { EvidenceBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { StateBlock } from "@/components/ui/StateBlock";
import { formatPercent } from "@/lib/format";
import type { ObjectiveProgress } from "@/lib/types";
import { progressQueryOptions } from "@/queries/progress";
import { useCardMutations } from "@/queries/review";
import { useCreateSession } from "@/queries/study";

function Stat({ value, label, note }: { value: string; label: string; note?: string }) {
  return (
    <div className="card card--quiet stat">
      <span className="stat__value">{value}</span>
      <span className="stat__label">{label}</span>
      {note ? <span className="stat__note">{note}</span> : null}
    </div>
  );
}

function ObjectiveRow({ o }: { o: ObjectiveProgress }) {
  return (
    <tr>
      <td>
        <strong>{o.code}</strong> {o.title}
        {o.self_declared_familiar ? (
          <span className="muted small"> · familiar (self-declared)</span>
        ) : null}
      </td>
      <td>
        {o.lessons_completed}/{o.lessons_total}
      </td>
      <td>
        {o.first_correct}/{o.first_attempts}{" "}
        <span className="muted">({formatPercent(o.first_accuracy)})</span>
      </td>
      <td>
        {o.repeat_correct}/{o.repeat_attempts}{" "}
        <span className="muted">({formatPercent(o.repeat_accuracy)})</span>
      </td>
      <td>
        {o.assessment_correct}/{o.assessment_attempts}
      </td>
      <td>
        <EvidenceBadge level={o.evidence} />
      </td>
    </tr>
  );
}

export default function ProgressPage() {
  const navigate = useNavigate();
  const progress = useQuery(progressQueryOptions());
  const createSession = useCreateSession();
  const cards = useCardMutations();
  if (progress.isPending) return <Spinner label="Counting the evidence" />;
  if (progress.isError)
    return (
      <StateBlock tone="error" title="Could not load progress" body={progress.error.message} />
    );
  const p = progress.data;
  const maxDay = Math.max(1, ...p.recent_activity.map((d) => d.answers + d.reviews + d.lessons));
  const next = p.next_action;

  return (
    <div className="stack">
      <div className="page-head">
        <h1>Progress</h1>
        <p>{p.evidence_note}</p>
      </div>
      <div className="grid-3">
        <Stat
          value={formatPercent(p.totals.first_accuracy)}
          label="First-attempt accuracy"
          note={`${p.totals.first_correct}/${p.totals.first_attempts} unique questions`}
        />
        <Stat
          value={formatPercent(p.totals.repeat_accuracy)}
          label="Repeated practice"
          note={`${p.totals.repeat_correct}/${p.totals.repeat_attempts} — not exam evidence`}
        />
        <Stat
          value={`${p.totals.assessment_correct}/${p.totals.assessment_attempts}`}
          label="Assessment answers"
          note={`${p.totals.assessment_sessions} assessment session(s); small samples are noisy`}
        />
        <Stat
          value={`${p.totals.families_seen}/${p.totals.questions_total}`}
          label="Questions seen"
          note="Of the usable bank for this track"
        />
        <Stat
          value={`${p.totals.lessons_completed}/${p.totals.lessons_total}`}
          label="Lessons read"
          note="Coverage, not mastery"
        />
        <Stat
          value={`${p.totals.cards_due}/${p.totals.cards_total}`}
          label="Cards due"
          note="Spaced repetition queue"
        />
      </div>
      {next ? (
        <section className="card card--gold spread">
          <div>
            <p className="card__eyebrow">Next useful action</p>
            <strong>{next.label}</strong> <span className="muted">— {next.reason}</span>
          </div>
          <Button
            variant="primary"
            busy={createSession.isPending}
            onClick={() => {
              if (next.kind === "resume" && next.session_id)
                void navigate({
                  to: "/practice/$sessionId",
                  params: { sessionId: String(next.session_id) },
                });
              else if (next.kind === "review")
                void navigate({ to: "/review", search: { limit: next.count } });
              else if (next.kind === "lesson" && next.item_key)
                void navigate({ to: "/learn/$key", params: { key: next.item_key } });
              else
                createSession.mutate(
                  { kind: "practice", minutes: 15, focus: next.focus ?? "mixed" },
                  {
                    onSuccess: (s) =>
                      void navigate({
                        to: "/practice/$sessionId",
                        params: { sessionId: String(s.id) },
                      }),
                  },
                );
            }}
          >
            Go
          </Button>
        </section>
      ) : null}
      <section className="card card--quiet">
        <p className="card__eyebrow">Last 14 days</p>
        <div className="activity" aria-label="Daily activity">
          {p.recent_activity.map((d) => {
            const total = d.answers + d.reviews + d.lessons;
            return (
              <div
                key={d.date}
                className={`activity__day ${total ? "activity__day--active" : ""}`}
                style={{ height: `${Math.max(4, (total / maxDay) * 56)}px` }}
                title={`${d.date}: ${d.answers} answers, ${d.reviews} reviews, ${d.lessons} lessons`}
              />
            );
          })}
        </div>
        <div className="activity__labels">
          <span>{p.recent_activity[0]?.date}</span>
          <span>today</span>
        </div>
      </section>
      {p.weak_areas.length > 0 ? (
        <section className="card">
          <h2>Weak areas</h2>
          <ul className="list-reset">
            {p.weak_areas.map((o) => (
              <li key={o.code} className="spread">
                <span>
                  <strong>{o.code}</strong> {o.title}{" "}
                  <span className="muted">
                    {o.first_correct}/{o.first_attempts}
                  </span>
                </span>
                <Button
                  size="sm"
                  onClick={() =>
                    createSession.mutate(
                      { kind: "practice", minutes: 15, focus: `objective:${o.code}` },
                      {
                        onSuccess: (s) =>
                          void navigate({
                            to: "/practice/$sessionId",
                            params: { sessionId: String(s.id) },
                          }),
                      },
                    )
                  }
                >
                  Practice
                </Button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {p.confident_mistakes.length > 0 ? (
        <section className="card">
          <h2>Confident mistakes</h2>
          <p className="muted small">Wrong while sure. These are the highest-value follow-ups.</p>
          <ul className="list-reset">
            {p.confident_mistakes.map((m) => (
              <li key={m.item_key} className="spread">
                <span className="small">
                  {m.stem_md.slice(0, 160)}…{" "}
                  <span className="muted">{m.objectives.map((o) => o.code).join(", ")}</span>
                </span>
                {m.has_card ? (
                  <span className="badge badge--gold">card made</span>
                ) : (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() =>
                      cards.create.mutate({
                        source_kind: "mistake",
                        item_key: m.item_key,
                        front_md: m.stem_md,
                        back_md:
                          "Review the explanation in Practice and write the decisive constraint here.",
                      })
                    }
                  >
                    Make a card
                  </Button>
                )}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {p.domains.map((d) => (
        <section key={d.code} className="card card--quiet">
          <div className="domain-head">
            <h2>
              {d.code}. {d.name}
            </h2>
            <span className="muted small">
              {d.weight_percent}% · first attempts {d.first_correct}/{d.first_attempts} (
              {formatPercent(d.first_accuracy)})
            </span>
          </div>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Objective</th>
                  <th>Lessons</th>
                  <th>First attempt</th>
                  <th>Repeated</th>
                  <th>Assessment</th>
                  <th>Evidence</th>
                </tr>
              </thead>
              <tbody>
                {d.objectives.map((o) => (
                  <ObjectiveRow key={o.code} o={o} />
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
      <p className="muted small">
        {p.flags.note} <Link to="/content">Content</Link>
      </p>
    </div>
  );
}
