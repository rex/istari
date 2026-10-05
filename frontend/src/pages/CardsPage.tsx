import { useQuery, useSuspenseQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { StateBlock } from "@/components/ui/StateBlock";
import { formatDateTime } from "@/lib/format";
import { meQueryOptions } from "@/queries/auth";
import { cardsQueryOptions, useCardMutations } from "@/queries/review";

export default function CardsPage() {
  const { data: me } = useSuspenseQuery(meQueryOptions());
  const cards = useQuery(cardsQueryOptions());
  const { create, update, remove } = useCardMutations();
  const [editing, setEditing] = useState<{ id: number; front: string; back: string } | null>(null);
  const [front, setFront] = useState("");
  const [back, setBack] = useState("");

  if (cards.isPending) return <Spinner label="Loading cards" />;
  if (cards.isError)
    return <StateBlock tone="error" title="Could not load cards" body={cards.error.message} />;

  return (
    <div className="stack">
      <div className="page-head">
        <h1>Cards</h1>
        <p>
          {cards.data.total} cards. Pack cards update with imports unless you edit them; your own
          cards are yours. <Link to="/review">Back to review</Link>
        </p>
      </div>
      <form
        className="card stack"
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate(
            { source_kind: "custom", front_md: front, back_md: back },
            {
              onSuccess: () => {
                setFront("");
                setBack("");
              },
            },
          );
        }}
      >
        <h2>New card</h2>
        <label className="field">
          <span className="field__label">Front</span>
          <textarea
            className="textarea"
            value={front}
            onChange={(e) => setFront(e.target.value)}
            required
          />
        </label>
        <label className="field">
          <span className="field__label">Back</span>
          <textarea
            className="textarea"
            value={back}
            onChange={(e) => setBack(e.target.value)}
            required
          />
        </label>
        <div>
          <Button type="submit" variant="primary" busy={create.isPending}>
            Add card
          </Button>
        </div>
      </form>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Front</th>
              <th>Source</th>
              <th>Due</th>
              <th>State</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {cards.data.cards.map((card) => (
              <tr key={card.id}>
                <td>
                  {editing?.id === card.id ? (
                    <form
                      className="stack"
                      onSubmit={(e) => {
                        e.preventDefault();
                        update.mutate({
                          cardId: card.id,
                          front_md: editing.front,
                          back_md: editing.back,
                        });
                        setEditing(null);
                      }}
                    >
                      <textarea
                        className="textarea"
                        aria-label="Front"
                        value={editing.front}
                        onChange={(e) => setEditing({ ...editing, front: e.target.value })}
                      />
                      <textarea
                        className="textarea"
                        aria-label="Back"
                        value={editing.back}
                        onChange={(e) => setEditing({ ...editing, back: e.target.value })}
                      />
                      <span className="cluster">
                        <Button type="submit" size="sm" variant="primary">
                          Save
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => setEditing(null)}>
                          Cancel
                        </Button>
                      </span>
                    </form>
                  ) : (
                    <>
                      {card.front_md.slice(0, 140)}
                      {card.user_edited ? <Badge tone="gold">edited</Badge> : null}
                    </>
                  )}
                </td>
                <td>
                  {card.source_kind}
                  {card.source_item_key ? ` · ${card.source_item_key}` : ""}
                </td>
                <td>{formatDateTime(card.due, me.settings.timezone)}</td>
                <td>
                  {card.suspended ? (
                    <Badge tone="warning">suspended</Badge>
                  ) : card.last_review ? (
                    <Badge tone="success">reviewed</Badge>
                  ) : (
                    <Badge>new</Badge>
                  )}
                </td>
                <td className="cluster">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() =>
                      setEditing({ id: card.id, front: card.front_md, back: card.back_md })
                    }
                  >
                    Edit
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => update.mutate({ cardId: card.id, suspended: !card.suspended })}
                  >
                    {card.suspended ? "Resume" : "Suspend"}
                  </Button>
                  {card.source_kind !== "flashcard" ? (
                    <Button size="sm" variant="danger" onClick={() => remove.mutate(card.id)}>
                      Delete
                    </Button>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
