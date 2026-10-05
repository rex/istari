import { useQuery, useSuspenseQuery } from "@tanstack/react-query";
import { Link, useParams } from "@tanstack/react-router";
import { useEffect, useRef } from "react";

import { NotesPanel } from "@/components/feature/NotesPanel";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { StateBlock } from "@/components/ui/StateBlock";
import { Markdown } from "@/lib/Markdown";
import { meQueryOptions } from "@/queries/auth";
import { lessonQueryOptions, useLessonProgress } from "@/queries/lessons";

export default function LessonPage() {
  const { key = "" } = useParams({ strict: false });
  const { data: me } = useSuspenseQuery(meQueryOptions());
  const lesson = useQuery(lessonQueryOptions(key));
  const progress = useLessonProgress(key);
  const lastSaved = useRef(0);
  const articleRef = useRef<HTMLElement>(null);

  // Save reading position (0–1) as the reader scrolls, at most every few seconds.
  useEffect(() => {
    const onScroll = () => {
      const el = articleRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const total = rect.height - window.innerHeight;
      const ratio = total <= 0 ? 1 : Math.min(1, Math.max(0, -rect.top / total));
      const now = Date.now();
      if (
        now - lastSaved.current > 4000 &&
        Math.abs(ratio - (lesson.data?.progress.position ?? 0)) > 0.05
      ) {
        lastSaved.current = now;
        progress.mutate({ position: Number(ratio.toFixed(2)) });
      }
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [lesson.data?.progress.position, progress]);

  if (lesson.isPending) return <Spinner label="Opening lesson" />;
  if (lesson.isError)
    return (
      <StateBlock tone="error" title="Could not open this lesson" body={lesson.error.message} />
    );
  const data = lesson.data;
  const completed = Boolean(data.progress.completed_at);

  return (
    <div className="with-rail">
      <article ref={articleRef} className="reader">
        <p className="card__eyebrow">
          <Link to="/learn">Learn</Link> ·{" "}
          {data.objectives.map((o) => `${o.code} ${o.title}`).join(" · ")}
        </p>
        <h1>{data.title}</h1>
        <p className="dim">{data.summary}</p>
        <div className="reader-bar">
          <Badge>
            {data.authored_by === "ai" ? "AI-authored" : "Human-authored"} ·{" "}
            {data.review_status.replace("_", " ")}
          </Badge>
          <Badge>~{data.estimated_minutes} min</Badge>
          <Button
            size="sm"
            variant={data.progress.bookmarked ? "primary" : "ghost"}
            onClick={() => progress.mutate({ bookmarked: !data.progress.bookmarked })}
            aria-pressed={data.progress.bookmarked}
          >
            {data.progress.bookmarked ? "Bookmarked" : "Bookmark"}
          </Button>
          <Button
            size="sm"
            variant={completed ? "secondary" : "primary"}
            onClick={() => progress.mutate({ completed: !completed })}
          >
            {completed ? "Mark unread" : "Mark as read"}
          </Button>
        </div>
        {data.foundations_md ? (
          <details className="disclosure">
            <summary>Foundations first (optional)</summary>
            <Markdown>{data.foundations_md}</Markdown>
          </details>
        ) : null}
        <Markdown>{data.body_md}</Markdown>
        {data.checks.length > 0 ? (
          <section>
            <h2>Check yourself</h2>
            {data.checks.map((check, index) => (
              <details key={index} className="disclosure">
                <summary>
                  <Markdown inline>{check.prompt_md}</Markdown>
                </summary>
                <Markdown>{check.answer_md}</Markdown>
              </details>
            ))}
          </section>
        ) : null}
        <section>
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
        </section>
      </article>
      <aside className="with-rail__rail stack">
        <div className="card card--quiet">
          <NotesPanel itemKey={data.item_key} notes={data.notes} timeZone={me.settings.timezone} />
        </div>
        <div className="card card--quiet small">
          <p className="card__eyebrow">Next</p>
          <Link to="/practice">Practice these objectives</Link>
        </div>
      </aside>
    </div>
  );
}
