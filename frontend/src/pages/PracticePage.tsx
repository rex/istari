import { useQuery, useSuspenseQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Segmented } from "@/components/ui/Segmented";
import type { SessionKind, SessionMinutes } from "@/lib/types";
import { meQueryOptions } from "@/queries/auth";
import { activeSessionQueryOptions, useCreateSession, useSessionAction } from "@/queries/study";
import { trackQueryOptions } from "@/queries/track";

const MINUTES = [
  { value: 5, label: "5 min · 5 q" },
  { value: 15, label: "15 min · 8 q" },
  { value: 30, label: "30 min · 12 q" },
] as const;
const KINDS = [
  { value: "practice", label: "Practice (feedback each question)" },
  { value: "assessment", label: "Assessment (feedback at the end)" },
] as const;

export default function PracticePage() {
  const navigate = useNavigate();
  const { data: me } = useSuspenseQuery(meQueryOptions());
  const track = useQuery(trackQueryOptions());
  const active = useQuery(activeSessionQueryOptions());
  const createSession = useCreateSession();
  const abandon = useSessionAction("abandon");
  const [kind, setKind] = useState<SessionKind>("practice");
  const [minutes, setMinutes] = useState<SessionMinutes>(
    (me.settings.preferred_session_minutes as SessionMinutes) || 15,
  );
  const [focus, setFocus] = useState("mixed");

  const go = (replace: boolean) =>
    createSession.mutate(
      { kind, minutes, focus, replace_active: replace },
      {
        onSuccess: (s) =>
          void navigate({ to: "/practice/$sessionId", params: { sessionId: String(s.id) } }),
      },
    );

  return (
    <div className="stack" style={{ maxWidth: "44rem" }}>
      <div className="page-head">
        <h1>Practice</h1>
        <p>
          Scenario questions graded on the server. Multiple-answer questions need the exact set.
        </p>
      </div>
      {active.data ? (
        <section className="card card--gold">
          <p className="card__eyebrow">In progress</p>
          <p>
            A {active.data.kind} session is open: {active.data.answered_count} of{" "}
            {active.data.total} answered.
          </p>
          <div className="cluster">
            <Link
              to="/practice/$sessionId"
              params={{ sessionId: String(active.data.id) }}
              className="btn btn--primary"
            >
              Resume
            </Link>
            <Button
              variant="danger"
              size="sm"
              onClick={() => abandon.mutate(active.data!.id)}
              busy={abandon.isPending}
            >
              Abandon it
            </Button>
          </div>
        </section>
      ) : null}
      <section className="card stack">
        <div className="field">
          <span className="field__label">Mode</span>
          <Segmented
            name="kind"
            label="Session mode"
            options={KINDS}
            value={kind}
            onChange={setKind}
          />
        </div>
        <div className="field">
          <span className="field__label">Length</span>
          <Segmented
            name="minutes"
            label="Session length"
            options={MINUTES}
            value={minutes}
            onChange={setMinutes}
          />
        </div>
        <label className="field">
          <span className="field__label">Focus</span>
          <select className="select" value={focus} onChange={(e) => setFocus(e.target.value)}>
            <option value="mixed">Mixed across domains</option>
            <option value="weak">Weakest objective (needs evidence)</option>
            {track.data?.domains.map((d) => (
              <optgroup key={d.code} label={`${d.code}. ${d.name}`}>
                {d.objectives.map((o) => (
                  <option key={o.code} value={`objective:${o.code}`}>
                    {o.code} {o.title}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
          <span className="field__hint">
            Unseen questions first, then earlier mistakes (confident ones first), then repeats.
          </span>
        </label>
        <div className="cluster">
          <Button
            variant="primary"
            size="lg"
            onClick={() => go(false)}
            busy={createSession.isPending}
            disabled={Boolean(active.data)}
          >
            Start {kind}
          </Button>
          {active.data ? (
            <span className="muted small">Finish or abandon the open session first.</span>
          ) : null}
        </div>
        {createSession.isError ? (
          <p className="save-status save-status--error" role="alert">
            {createSession.error.message}
          </p>
        ) : null}
      </section>
    </div>
  );
}
