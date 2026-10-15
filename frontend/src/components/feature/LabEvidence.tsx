import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Markdown } from "@/lib/Markdown";
import { formatDateTime } from "@/lib/format";
import type { EvidenceView } from "@/lib/types";
import { useEvidenceMutations } from "@/queries/labs";

/** The owner's own notes on a lab: what was observed, what surprised, what was cleaned up. */
export function LabEvidence({
  labKey,
  evidence,
  timeZone,
}: {
  labKey: string;
  evidence: EvidenceView[];
  timeZone: string;
}) {
  const { add, update, remove } = useEvidenceMutations(labKey);
  const [draft, setDraft] = useState("");
  const [editing, setEditing] = useState<{ id: number; body: string } | null>(null);
  return (
    <section className="card card--quiet notes" aria-labelledby="evidence-title">
      <h3 id="evidence-title">Evidence</h3>
      <p className="muted small">What you observed, what surprised you, what you cleaned up.</p>
      {evidence.map((e) => (
        <article key={e.id} className="note">
          <div className="note__meta">
            <span>{formatDateTime(e.updated_at, timeZone)}</span>
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
  );
}
