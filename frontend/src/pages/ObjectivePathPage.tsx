import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "@tanstack/react-router";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { StateBlock } from "@/components/ui/StateBlock";
import { formatMinutes } from "@/lib/comparison";
import { formatRelative } from "@/lib/format";
import { entryKeys, moveEntry, resumeEntry } from "@/lib/paths";
import type { ObjectivePathView, PathEntryView } from "@/lib/types-paths";
import { objectivePathQueryOptions, usePathMutations } from "@/queries/paths";

function PathRow({
  entry,
  code,
  first,
  last,
  busy,
  onMove,
  onExclude,
}: {
  entry: PathEntryView;
  code: string;
  first: boolean;
  last: boolean;
  busy: boolean;
  onMove: (step: -1 | 1) => void;
  onExclude: () => void;
}) {
  return (
    <li className="card card--quiet stack">
      <p className="card__eyebrow">
        {entry.position + 1} · {entry.course_title} · {entry.section_title}
      </p>
      <div className="spread">
        <Link
          to="/watch/$course/play"
          params={{ course: entry.course_slug }}
          search={{ lecture: entry.lecture_path, path: code }}
          className="lesson-row__title"
        >
          {entry.lecture_title}
        </Link>
        <span className="cluster">
          {entry.source === "pinned" ? <Badge tone="gold">pinned</Badge> : null}
          {entry.completed ? <Badge tone="success">watched</Badge> : null}
          <span className="small muted">
            {entry.minutes ? formatMinutes(entry.minutes) : "length unknown"}
          </span>
        </span>
      </div>
      <p className="small muted" style={{ margin: 0 }}>
        {entry.reason}
      </p>
      <div className="cluster">
        <Button size="sm" variant="ghost" disabled={first || busy} onClick={() => onMove(-1)}>
          Move up
        </Button>
        <Button size="sm" variant="ghost" disabled={last || busy} onClick={() => onMove(1)}>
          Move down
        </Button>
        <Button size="sm" variant="ghost" disabled={busy} onClick={onExclude}>
          Exclude
        </Button>
      </div>
    </li>
  );
}

function Head({ view, code }: { view: ObjectivePathView; code: string }) {
  const navigate = useNavigate();
  const resume = resumeEntry(view);
  const watched = view.entries.filter((e) => e.completed).length;
  return (
    <div className="page-head">
      <p className="card__eyebrow">
        <Link to="/learn">Learn</Link> · learning path · domain {view.domain_code}
      </p>
      <h1>
        {view.objective_code} {view.objective_title}
      </h1>
      <p>
        {view.entries.length} lectures, {formatMinutes(view.total_minutes)}, from{" "}
        {view.courses.join(", ") || "no course yet"}. Composed across courses, continuity first;
        your pins lead and your exclusions never return. Every entry is one lecture of one course.
      </p>
      <p className="cluster small muted">
        <span>
          {view.composed_at ? `Composed ${formatRelative(view.composed_at)}` : "Not composed"}
        </span>
        <span>
          {watched} of {view.entries.length} watched
        </span>
        <Link to="/progress">Progress</Link>
      </p>
      {resume ? (
        <Button
          variant="primary"
          onClick={() =>
            void navigate({
              to: "/watch/$course/play",
              params: { course: resume.course_slug },
              search: { lecture: resume.lecture_path, path: code },
            })
          }
        >
          {watched > 0 ? "Continue" : "Start"}: {resume.lecture_title}
        </Button>
      ) : null}
    </div>
  );
}

export default function ObjectivePathPage() {
  const { code = "" } = useParams({ strict: false });
  const path = useQuery(objectivePathQueryOptions(code));
  const { decide, rebuild } = usePathMutations();
  if (path.isPending) return <Spinner label="Composing the path" />;
  if (path.isError) {
    return <StateBlock tone="error" title="Could not load the path" body={path.error.message} />;
  }
  const view = path.data;
  const busy = decide.isPending || rebuild.isPending;
  const edited = view.excluded.length > 0 || view.entries.some((e) => e.source === "pinned");
  const reorder = (from: number, to: number) =>
    decide.mutate({ code, order: entryKeys(moveEntry(view.entries, from, to)) });

  return (
    <div className="stack">
      <Head view={view} code={code} />
      {view.entries.length === 0 ? (
        <StateBlock
          title="No lectures on this path yet"
          body="Paths are composed from the lecture index. Rebuild it under Content, Lecture mapping, once the share's captions are indexed."
          action={
            <Link to="/content/lectures" className="btn btn--secondary">
              Lecture mapping
            </Link>
          }
        />
      ) : (
        <ol className="list-reset stack" aria-label="Lectures on the path">
          {view.entries.map((entry, index) => (
            <PathRow
              key={`${entry.course_slug}/${entry.lecture_path}`}
              entry={entry}
              code={code}
              first={index === 0}
              last={index === view.entries.length - 1}
              busy={busy}
              onMove={(step) => reorder(index, index + step)}
              onExclude={() =>
                decide.mutate({ code, exclude: [[entry.course_slug, entry.lecture_path]] })
              }
            />
          ))}
        </ol>
      )}
      {view.stale_courses.length > 0 ? (
        <p className="small muted" style={{ margin: 0 }}>
          Stepped aside, older exam covered by a current course: {view.stale_courses.join(", ")}.
        </p>
      ) : null}
      {view.excluded.length > 0 ? (
        <section className="card card--quiet stack" aria-label="Excluded lectures">
          <h2>Excluded</h2>
          {view.excluded.map((e) => (
            <div key={`${e.course_slug}/${e.lecture_path}`} className="spread">
              <span className="small">
                {e.lecture_title} <span className="muted">· {e.course_title}</span>
              </span>
              <Button
                size="sm"
                variant="ghost"
                disabled={busy}
                onClick={() => decide.mutate({ code, restore: [[e.course_slug, e.lecture_path]] })}
              >
                Restore
              </Button>
            </div>
          ))}
        </section>
      ) : null}
      <div className="cluster">
        {edited ? (
          <Button
            variant="ghost"
            disabled={busy}
            onClick={() => decide.mutate({ code, reset: true })}
          >
            Back to the proposal
          </Button>
        ) : null}
        <Button variant="ghost" busy={rebuild.isPending} onClick={() => rebuild.mutate()}>
          Recompose all paths
        </Button>
        {decide.isError ? (
          <span className="save-status save-status--error">{decide.error.message}</span>
        ) : null}
      </div>
    </div>
  );
}
