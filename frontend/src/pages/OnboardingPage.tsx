import { useQuery, useSuspenseQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Segmented } from "@/components/ui/Segmented";
import { api } from "@/lib/api";
import type { SessionMinutes, TrackView } from "@/lib/types";
import { meQueryOptions, useCompleteOnboarding } from "@/queries/auth";

const MINUTES = [
  { value: 5, label: "5 min" },
  { value: 15, label: "15 min" },
  { value: 30, label: "30 min" },
] as const;

/** One short screen: track, optional exam date, session length. Nothing else gates you. */
export default function OnboardingPage() {
  const navigate = useNavigate();
  const { data: me } = useSuspenseQuery(meQueryOptions());
  const complete = useCompleteOnboarding();
  const first = me.available_tracks[0];
  const [trackId, setTrackId] = useState<number | null>(
    me.track?.exam_version_id ?? first?.exam_version_id ?? null,
  );
  const [examDate, setExamDate] = useState(me.settings.exam_date ?? "");
  const [minutes, setMinutes] = useState<SessionMinutes>(
    (me.settings.preferred_session_minutes as SessionMinutes) || 15,
  );
  const [familiar, setFamiliar] = useState<Set<string>>(
    new Set(me.settings.familiar_objective_codes),
  );
  const track = useQuery({
    queryKey: ["tracks", trackId],
    queryFn: () => api<TrackView>(`/api/tracks/${trackId}`),
    enabled: trackId !== null,
  });

  if (me.available_tracks.length === 0) {
    return (
      <section className="card stack" style={{ maxWidth: "40rem" }}>
        <h1>No content yet</h1>
        <p>
          Import a content pack first: <code>make seed</code> loads everything under{" "}
          <code>content/packs/</code>. Then come back here.
        </p>
      </section>
    );
  }

  return (
    <form
      className="card stack"
      style={{ maxWidth: "44rem" }}
      onSubmit={(event) => {
        event.preventDefault();
        if (trackId === null) return;
        complete.mutate(
          {
            exam_version_id: trackId,
            exam_date: examDate || null,
            preferred_session_minutes: minutes,
            familiar_objective_codes: [...familiar],
          },
          { onSuccess: () => void navigate({ to: "/" }) },
        );
      }}
    >
      <div className="page-head">
        <h1>Set up your track</h1>
        <p>Thirty seconds. You can change all of this in Settings.</p>
      </div>
      <fieldset className="field">
        <legend className="field__label">Track</legend>
        {me.available_tracks.map((t) => (
          <label key={t.exam_version_id} className="check">
            <input
              type="radio"
              name="track"
              checked={trackId === t.exam_version_id}
              onChange={() => setTrackId(t.exam_version_id)}
            />
            <span>
              {t.certification} <span className="muted">({t.code})</span>
              {t.verification_status === "unverified" ? (
                <span className="badge badge--warning" style={{ marginLeft: "0.5rem" }}>
                  exam metadata unverified
                </span>
              ) : null}
            </span>
          </label>
        ))}
      </fieldset>
      <label className="field">
        <span className="field__label">Exam date (optional)</span>
        <input
          className="input"
          type="date"
          value={examDate}
          onChange={(e) => setExamDate(e.target.value)}
        />
        <span className="field__hint">Used only for a quiet countdown. No streaks, no guilt.</span>
      </label>
      <div className="field">
        <span className="field__label">Preferred session length</span>
        <Segmented
          name="minutes"
          label="Session length"
          options={MINUTES}
          value={minutes}
          onChange={setMinutes}
        />
      </div>
      <details className="disclosure">
        <summary>Already familiar with some objectives? (optional)</summary>
        <p className="muted small">
          Marked objectives are read last, not skipped. Practice still covers them, because
          self-declared familiarity is not evidence.
        </p>
        {track.data?.domains.map((domain) => (
          <fieldset key={domain.code} className="field">
            <legend className="field__label">
              {domain.code}. {domain.name}
            </legend>
            {domain.objectives.map((o) => (
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
        <Button
          type="submit"
          variant="primary"
          size="lg"
          busy={complete.isPending}
          disabled={trackId === null}
        >
          Start studying
        </Button>
        {complete.isError ? (
          <span className="save-status save-status--error">Could not save. Try again.</span>
        ) : null}
      </div>
    </form>
  );
}
