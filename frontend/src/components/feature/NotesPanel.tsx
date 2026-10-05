import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Markdown } from "@/lib/Markdown";
import { formatDateTime } from "@/lib/format";
import type { NoteView } from "@/lib/types";
import { useNoteMutations } from "@/queries/lessons";
import { useCardMutations } from "@/queries/review";

interface NotesPanelProps {
  itemKey: string;
  notes: NoteView[];
  timeZone: string;
}

export function NotesPanel({ itemKey, notes, timeZone }: NotesPanelProps) {
  const { create, update, remove } = useNoteMutations(itemKey);
  const cards = useCardMutations();
  const [draft, setDraft] = useState("");
  const [editing, setEditing] = useState<{ id: number; body: string } | null>(null);

  return (
    <section className="notes" aria-labelledby="notes-title">
      <h3 id="notes-title">Notes</h3>
      {notes.length === 0 ? (
        <p className="muted small">No notes yet. Short and personal works best.</p>
      ) : null}
      {notes.map((note) => (
        <article key={note.id} className="note">
          <div className="note__meta">
            <span>{formatDateTime(note.updated_at, timeZone)}</span>
            <span className="cluster">
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => setEditing({ id: note.id, body: note.body_md })}
              >
                Edit
              </button>
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() =>
                  cards.create.mutate({
                    source_kind: "note",
                    note_id: note.id,
                    front_md: note.body_md.split("\n")[0] ?? "Note",
                    back_md: note.body_md,
                  })
                }
              >
                Make a card
              </button>
              <button
                type="button"
                className="btn btn--danger btn--sm"
                onClick={() => remove.mutate(note.id)}
              >
                Delete
              </button>
            </span>
          </div>
          {editing?.id === note.id ? (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                update.mutate({ id: note.id, body_md: editing.body });
                setEditing(null);
              }}
            >
              <textarea
                className="textarea"
                value={editing.body}
                onChange={(e) => setEditing({ id: note.id, body: e.target.value })}
                aria-label="Edit note"
              />
              <div className="cluster">
                <Button type="submit" variant="primary" size="sm" busy={update.isPending}>
                  Save
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setEditing(null)}>
                  Cancel
                </Button>
              </div>
            </form>
          ) : (
            <Markdown>{note.body_md}</Markdown>
          )}
        </article>
      ))}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (!draft.trim()) return;
          create.mutate(draft.trim(), { onSuccess: () => setDraft("") });
        }}
      >
        <label className="field">
          <span className="field__label">Add a note</span>
          <textarea
            className="textarea"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="What do you want to remember about this?"
          />
        </label>
        <Button
          type="submit"
          variant="secondary"
          size="sm"
          busy={create.isPending}
          disabled={!draft.trim()}
        >
          Save note
        </Button>
        {create.isError ? (
          <span className="save-status save-status--error"> Not saved — try again.</span>
        ) : null}
      </form>
    </section>
  );
}
