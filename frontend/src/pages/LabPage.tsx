import { useQuery, useSuspenseQuery } from "@tanstack/react-query";
import { Link, useParams } from "@tanstack/react-router";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { StateBlock } from "@/components/ui/StateBlock";
import { Markdown } from "@/lib/Markdown";
import { formatDateTime } from "@/lib/format";
import { meQueryOptions } from "@/queries/auth";
import { labQueryOptions, useEvidenceMutations } from "@/queries/labs";

export default function LabPage() {
  const { key = "" } = useParams({ strict: false });
  const { data: me } = useSuspenseQuery(meQueryOptions());
  const lab = useQuery(labQueryOptions(key));
  const { add, update, remove } = useEvidenceMutations(key);
  const [draft, setDraft] = useState("");
  const [editing, setEditing] = useState<{ id: number; body: string } | null>(null);
  if (lab.isPending) return <Spinner label="Opening lab" />;
  if (lab.isError)
    return <StateBlock tone="error" title="Could not open this lab" body={lab.error.message} />;
  const data = lab.data;

  return (
    <div className="with-rail">
      <article className="reader">
        <p className="card__eyebrow">
          <Link to="/labs">Labs</Link> · {data.objectives.map((o) => o.code).join(" · ")} · ~
          {data.estimated_minutes} min
        </p>
        <h1>{data.title}</h1>
        <div className="cost-warning">
          <strong>Cost warning.</strong> <Markdown inline>{data.cost_warning_md}</Markdown>
        </div>
        <h2>Goals</h2>
        <Markdown>{data.goals_md}</Markdown>
        <h2>Prerequisites</h2>
        <Markdown>{data.prerequisites_md}</Markdown>
        <h2>Steps (manual)</h2>
        <Markdown>{data.steps_md}</Markdown>
        <h2>Expected observations</h2>
        <Markdown>{data.expected_observations_md}</Markdown>
        <h2>Cleanup</h2>
        <Markdown>{data.cleanup_md}</Markdown>
        <h2>Sources</h2>
        <ul className="sources">
          {data.sources.map((s) => (
            <li key={s.url}>
              <a href={s.url} target="_blank" rel="noopener noreferrer">
                {s.title}
              </a>{" "}
              <span className="muted">(checked {s.checked_on})</span>
            </li>
          ))}
        </ul>
      </article>
      <aside className="with-rail__rail">
        <section className="card card--quiet notes" aria-labelledby="evidence-title">
          <h3 id="evidence-title">Evidence</h3>
          <p className="muted small">What you observed, what surprised you, what you cleaned up.</p>
          {data.evidence.map((e) => (
            <article key={e.id} className="note">
              <div className="note__meta">
                <span>{formatDateTime(e.updated_at, me.settings.timezone)}</span>
                <span className="cluster">
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    onClick={() => setEditing({ id: e.id, body: e.body_md })}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    className="btn btn--danger btn--sm"
                    onClick={() => remove.mutate(e.id)}
                  >
                    Delete
                  </button>
                </span>
              </div>
              {editing?.id === e.id ? (
                <form
                  onSubmit={(ev) => {
                    ev.preventDefault();
                    update.mutate({ id: e.id, body_md: editing.body });
                    setEditing(null);
                  }}
                >
                  <textarea
                    className="textarea"
                    value={editing.body}
                    onChange={(ev) => setEditing({ id: e.id, body: ev.target.value })}
                    aria-label="Edit evidence"
                  />
                  <Button type="submit" size="sm" variant="primary">
                    Save
                  </Button>
                </form>
              ) : (
                <Markdown>{e.body_md}</Markdown>
              )}
            </article>
          ))}
          <form
            onSubmit={(ev) => {
              ev.preventDefault();
              if (draft.trim()) add.mutate(draft.trim(), { onSuccess: () => setDraft("") });
            }}
          >
            <label className="field">
              <span className="field__label">Record evidence</span>
              <textarea
                className="textarea"
                value={draft}
                onChange={(ev) => setDraft(ev.target.value)}
              />
            </label>
            <Button
              type="submit"
              size="sm"
              variant="secondary"
              busy={add.isPending}
              disabled={!draft.trim()}
            >
              Save
            </Button>
          </form>
        </section>
      </aside>
    </div>
  );
}
