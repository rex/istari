import { useQuery, useSuspenseQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Segmented } from "@/components/ui/Segmented";
import type { SessionMinutes } from "@/lib/types";
import { meQueryOptions, useLogout, useUpdateSettings } from "@/queries/auth";
import { trackQueryOptions } from "@/queries/track";

const MINUTES = [
  { value: 5, label: "5" },
  { value: 15, label: "15" },
  { value: 30, label: "30" },
] as const;

export default function SettingsPage() {
  const navigate = useNavigate();
  const { data: me } = useSuspenseQuery(meQueryOptions());
  const track = useQuery(trackQueryOptions());
  const update = useUpdateSettings();
  const logout = useLogout();
  const s = me.settings;
  const [timezone, setTimezone] = useState(s.timezone);
  const [examDate, setExamDate] = useState(s.exam_date ?? "");
  const [limit, setLimit] = useState(s.daily_review_limit);
  const [familiar, setFamiliar] = useState<Set<string>>(new Set(s.familiar_objective_codes));

  return (
    <div className="stack" style={{ maxWidth: "44rem" }}>
      <div className="page-head">
        <h1>Settings</h1>
        <p>
          Signed in as {me.user.username} · track {me.track?.code ?? "none"} ·{" "}
          <Link to="/content">Content administration</Link>
        </p>
      </div>
      <form
        className="card stack"
        onSubmit={(e) => {
          e.preventDefault();
          update.mutate({
            timezone,
            exam_date: examDate || null,
            clear_exam_date: !examDate,
            daily_review_limit: limit,
            familiar_objective_codes: [...familiar],
          });
        }}
      >
        <label className="field">
          <span className="field__label">Timezone (IANA)</span>
          <input className="input" value={timezone} onChange={(e) => setTimezone(e.target.value)} />
          <span className="field__hint">
            Review due dates are stored in UTC and shown in this zone.
          </span>
        </label>
        <div className="field">
          <span className="field__label">Preferred session length (minutes)</span>
          <Segmented
            name="pref-minutes"
            label="Preferred minutes"
            options={MINUTES}
            value={s.preferred_session_minutes as SessionMinutes}
            onChange={(v) => update.mutate({ preferred_session_minutes: v })}
          />
        </div>
        <label className="field">
          <span className="field__label">Exam date</span>
          <input
            className="input"
            type="date"
            value={examDate}
            onChange={(e) => setExamDate(e.target.value)}
          />
        </label>
        <label className="field">
          <span className="field__label">Daily review limit</span>
          <input
            className="input"
            type="number"
            min={1}
            max={500}
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
          />
        </label>
        <div className="field">
          <span className="field__label">Backlog mode</span>
          <div className="cluster">
            <Button
              size="sm"
              variant={s.backlog_mode === "normal" ? "primary" : "ghost"}
              onClick={() => update.mutate({ backlog_mode: "normal" })}
            >
              Normal
            </Button>
            <Button
              size="sm"
              variant={s.backlog_mode === "recovery" ? "primary" : "ghost"}
              onClick={() => update.mutate({ backlog_mode: "recovery" })}
            >
              Recovery (10 at a time, oldest first)
            </Button>
          </div>
          <span className="field__hint">
            Recovery mode never resets cards or shames you about the count. It just makes the pile
            approachable.
          </span>
        </div>
        <details className="disclosure">
          <summary>Objectives marked familiar</summary>
          {track.data?.domains.map((d) => (
            <fieldset key={d.code} className="field">
              <legend className="field__label">
                {d.code}. {d.name}
              </legend>
              {d.objectives.map((o) => (
                <label key={o.code} className="check">
                  <input
                    type="checkbox"
                    checked={familiar.has(o.code)}
                    onChange={(e) => {
                      const next = new Set(familiar);
                      if (e.target.checked) next.add(o.code);
                      else next.delete(o.code);
                      setFamiliar(next);
                    }}
                  />
                  <span>
                    {o.code} {o.title}
                  </span>
                </label>
              ))}
            </fieldset>
          ))}
        </details>
        <div className="cluster">
          <Button type="submit" variant="primary" busy={update.isPending}>
            Save settings
          </Button>
          {update.isSuccess ? <span className="save-status save-status--saved">Saved</span> : null}
          {update.isError ? (
            <span className="save-status save-status--error">{update.error.message}</span>
          ) : null}
        </div>
      </form>
      <section className="card card--quiet spread">
        <span className="small muted">Server-side session; logging out revokes it.</span>
        <Button
          variant="danger"
          onClick={() =>
            logout.mutate(undefined, { onSettled: () => void navigate({ to: "/login" }) })
          }
          busy={logout.isPending}
        >
          Log out
        </Button>
      </section>
    </div>
  );
}
