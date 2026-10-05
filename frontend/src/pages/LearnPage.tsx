import { useQuery, useSuspenseQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";

import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { StateBlock } from "@/components/ui/StateBlock";
import { lessonsQueryOptions } from "@/queries/lessons";
import { trackQueryOptions } from "@/queries/track";

export default function LearnPage() {
  const { data: track } = useSuspenseQuery(trackQueryOptions());
  const lessons = useQuery(lessonsQueryOptions());
  if (lessons.isPending) return <Spinner label="Loading lessons" />;
  if (lessons.isError)
    return <StateBlock tone="error" title="Could not load lessons" body={lessons.error.message} />;
  const done = lessons.data.filter((l) => l.progress.completed_at).length;

  return (
    <div className="stack">
      <div className="page-head">
        <h1>Learn</h1>
        <p>
          {done} of {lessons.data.length} lessons read. Reading is coverage, not proof — practice
          supplies the evidence.
        </p>
      </div>
      {track.domains.map((domain) => {
        const mine = lessons.data.filter((l) => l.domain_code === domain.code);
        if (mine.length === 0) return null;
        return (
          <section key={domain.code}>
            <div className="domain-head">
              <h2>
                {domain.code}. {domain.name}
              </h2>
              <span className="muted small">{domain.weight_percent}% of the exam</span>
            </div>
            <div className="lesson-list">
              {mine.map((lesson) => (
                <Link
                  key={lesson.item_key}
                  to="/learn/$key"
                  params={{ key: lesson.item_key }}
                  className="card card--quiet lesson-row"
                >
                  <span>
                    <span className="lesson-row__title">{lesson.title}</span>
                    <span className="lesson-row__meta">
                      {lesson.summary} · ~{lesson.estimated_minutes} min ·{" "}
                      {lesson.objectives.map((o) => o.code).join(", ")}
                    </span>
                  </span>
                  <span className="cluster">
                    {lesson.progress.bookmarked ? <Badge tone="gold">bookmarked</Badge> : null}
                    {lesson.self_declared_familiar ? <Badge>familiar (self-declared)</Badge> : null}
                    {lesson.progress.completed_at ? (
                      <Badge tone="success">read</Badge>
                    ) : lesson.progress.position > 0 ? (
                      <Badge tone="info">{Math.round(lesson.progress.position * 100)}%</Badge>
                    ) : (
                      <Badge>unread</Badge>
                    )}
                  </span>
                </Link>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
