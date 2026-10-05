import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "@tanstack/react-router";
import { useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { StateBlock } from "@/components/ui/StateBlock";
import { isApiError } from "@/lib/api";
import type { ContentItemDetail } from "@/lib/types";
import { contentItemQueryOptions, useContentMutations } from "@/queries/content";

function initialText(d: ContentItemDetail): string {
  return JSON.stringify(
    {
      ...d.content,
      objectives: d.objectives,
      sources: d.sources,
      provenance: d.provenance,
      review_status: d.review_status,
    },
    null,
    2,
  );
}

/** JSON editor for one item in pack-schema shape. Keyed by revision so a save resets it. */
function ItemEditor({ detail }: { detail: ContentItemDetail }) {
  const { updateItem } = useContentMutations();
  const [text, setText] = useState(() => initialText(detail));
  const [parseError, setParseError] = useState<string | null>(null);
  return (
    <form
      className="card stack"
      onSubmit={(e) => {
        e.preventDefault();
        setParseError(null);
        let parsed: Record<string, unknown>;
        try {
          parsed = JSON.parse(text) as Record<string, unknown>;
        } catch (error) {
          setParseError(error instanceof Error ? error.message : "Invalid JSON");
          return;
        }
        updateItem.mutate({ key: detail.key, item: parsed });
      }}
    >
      <label className="field">
        <span className="field__label">
          Item (pack schema JSON — answers included, so this page is behind login)
        </span>
        <textarea
          className="textarea textarea--mono"
          value={text}
          onChange={(e) => setText(e.target.value)}
          spellCheck={false}
        />
      </label>
      <div className="cluster">
        <Button type="submit" variant="primary" busy={updateItem.isPending}>
          Save as new revision
        </Button>
        {updateItem.isSuccess ? (
          <span className="save-status save-status--saved">Saved</span>
        ) : null}
      </div>
      {parseError ? (
        <p className="save-status save-status--error" role="alert">
          {parseError}
        </p>
      ) : null}
      {updateItem.isError ? (
        <pre className="import-report" role="alert">
          {updateItem.error.message}
          {"\n"}
          {isApiError(updateItem.error) ? JSON.stringify(updateItem.error.details, null, 2) : ""}
        </pre>
      ) : null}
    </form>
  );
}

export default function ContentItemPage() {
  const { key = "" } = useParams({ strict: false });
  const item = useQuery(contentItemQueryOptions(key));
  const { setFlags } = useContentMutations();

  if (item.isPending) return <Spinner label="Loading item" />;
  if (item.isError)
    return <StateBlock tone="error" title="Item not found" body={item.error.message} />;
  const d = item.data;

  return (
    <div className="stack">
      <div className="page-head">
        <p className="card__eyebrow">
          <Link to="/content">Content</Link> · {d.pack_slug}
        </p>
        <h1>{d.key}</h1>
        <p className="cluster">
          <Badge>{d.kind}</Badge>
          <Badge>
            revision {d.revision} of {d.revisions.length}
          </Badge>
          <Badge
            tone={
              d.status === "active" ? "success" : d.status === "invalidated" ? "danger" : "neutral"
            }
          >
            {d.status}
          </Badge>
          <Badge>{d.review_status.replace("_", " ")}</Badge>
          {d.user_approved ? <Badge tone="gold">user approved</Badge> : null}
        </p>
      </div>
      <section className="card stack">
        <div className="cluster">
          <Button
            size="sm"
            onClick={() => setFlags.mutate({ key, user_approved: !d.user_approved })}
          >
            {d.user_approved ? "Withdraw approval" : "Approve for assessments"}
          </Button>
          <Button
            size="sm"
            variant={d.status === "invalidated" ? "secondary" : "danger"}
            onClick={() =>
              setFlags.mutate({
                key,
                status: d.status === "invalidated" ? "active" : "invalidated",
              })
            }
          >
            {d.status === "invalidated" ? "Reinstate" : "Invalidate (flags analytics)"}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() =>
              setFlags.mutate({ key, status: d.status === "retired" ? "active" : "retired" })
            }
          >
            {d.status === "retired" ? "Un-retire" : "Retire"}
          </Button>
        </div>
        <p className="muted small">
          Approval lets an unverified draft count toward sessions and progress. Invalidating keeps
          history but excludes this item's answers from every figure.
        </p>
      </section>
      <ItemEditor key={d.revision} detail={d} />
    </div>
  );
}
