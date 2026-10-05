import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import type { ImportReportView } from "@/lib/types";
import {
  contentItemsQueryOptions,
  packsQueryOptions,
  useContentMutations,
} from "@/queries/content";

const KINDS = ["", "lesson", "question", "flashcard", "lab"] as const;

export default function ContentPage() {
  const [kind, setKind] = useState<string>("");
  const items = useQuery(contentItemsQueryOptions(kind || undefined));
  const packs = useQuery(packsQueryOptions());
  const { importPack } = useContentMutations();
  const [json, setJson] = useState("");
  const [report, setReport] = useState<ImportReportView | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);

  const run = (dryRun: boolean) => {
    setParseError(null);
    let pack: unknown;
    try {
      pack = JSON.parse(json);
    } catch (error) {
      setParseError(error instanceof Error ? error.message : "Invalid JSON");
      return;
    }
    importPack.mutate({ pack, dry_run: dryRun }, { onSuccess: setReport });
  };

  return (
    <div className="stack">
      <div className="page-head">
        <h1>Content</h1>
        <p>Packs, items and revisions. Imports never touch notes, answers or review history.</p>
      </div>
      <section className="card stack">
        <h2>Packs</h2>
        {packs.data?.map((p) => (
          <div key={String(p["slug"])} className="spread">
            <span>
              <strong>{String(p["name"])}</strong>{" "}
              <span className="muted">
                {String(p["slug"])} v{String(p["version"])} · {String(p["authored_by"])}
              </span>
            </span>
            <a
              className="btn btn--ghost btn--sm"
              href={`/api/content/export/${String(p["slug"])}`}
              download={`${String(p["slug"])}.json`}
            >
              Export JSON
            </a>
          </div>
        ))}
      </section>
      <section className="card stack">
        <h2>Import a pack</h2>
        <label className="field">
          <span className="field__label">Pack JSON</span>
          <textarea
            className="textarea textarea--mono"
            value={json}
            onChange={(e) => setJson(e.target.value)}
            placeholder='{"schema_version": 1, "pack": {...}, ...}'
          />
          <input
            type="file"
            accept="application/json"
            aria-label="Choose a pack file"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void file.text().then(setJson);
            }}
          />
        </label>
        <div className="cluster">
          <Button onClick={() => run(true)} busy={importPack.isPending} disabled={!json.trim()}>
            Preview (dry run)
          </Button>
          <Button
            variant="primary"
            onClick={() => run(false)}
            busy={importPack.isPending}
            disabled={!json.trim() || !report?.dry_run}
          >
            Import
          </Button>
          <span className="muted small">
            Preview first; Import is enabled after a preview of the same text.
          </span>
        </div>
        {parseError ? (
          <p className="save-status save-status--error" role="alert">
            {parseError}
          </p>
        ) : null}
        {importPack.isError ? (
          <pre className="import-report" role="alert">
            {importPack.error.message}
            {"\n"}
            {JSON.stringify(
              importPack.error instanceof Error && "details" in importPack.error
                ? (importPack.error as { details: unknown }).details
                : null,
              null,
              2,
            )}
          </pre>
        ) : null}
        {report ? (
          <pre className="import-report">
            {report.dry_run ? "DRY RUN — nothing written" : "IMPORTED"} ·{" "}
            {JSON.stringify(report.counts)}
            {"\n"}created: {report.created.join(", ") || "—"}
            {"\n"}updated: {report.updated.join(", ") || "—"}
            {"\n"}retired: {report.retired.join(", ") || "—"}
            {"\n"}track changes: {report.track_changes.join("; ") || "—"}
            {"\n"}warnings: {report.warnings.map((w) => JSON.stringify(w)).join("; ") || "—"}
          </pre>
        ) : null}
      </section>
      <section className="card stack">
        <div className="spread">
          <h2>Items</h2>
          <select
            className="select"
            style={{ width: "auto" }}
            value={kind}
            onChange={(e) => setKind(e.target.value)}
            aria-label="Filter by kind"
          >
            {KINDS.map((k) => (
              <option key={k} value={k}>
                {k || "all kinds"}
              </option>
            ))}
          </select>
        </div>
        {items.isPending ? <Spinner /> : null}
        {items.data ? (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Key</th>
                  <th>Kind</th>
                  <th>Preview</th>
                  <th>Objectives</th>
                  <th>Rev</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {items.data.items.map((it) => (
                  <tr key={it.key}>
                    <td>
                      <Link to="/content/$key" params={{ key: it.key }}>
                        {it.key}
                      </Link>
                    </td>
                    <td>{it.kind}</td>
                    <td className="small">{it.preview}</td>
                    <td>{it.objectives.join(", ")}</td>
                    <td>{it.revision}</td>
                    <td className="cluster">
                      <Badge
                        tone={
                          it.status === "active"
                            ? "success"
                            : it.status === "invalidated"
                              ? "danger"
                              : "neutral"
                        }
                      >
                        {it.status}
                      </Badge>
                      <Badge>{it.review_status.replace("_", " ")}</Badge>
                      {it.user_approved ? <Badge tone="gold">approved</Badge> : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </div>
  );
}
