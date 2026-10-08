import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { StateBlock } from "@/components/ui/StateBlock";
import { formatDateTime } from "@/lib/format";
import type { CourseSummary } from "@/lib/types-watch";
import { coursesQueryOptions, useRefreshCatalog } from "@/queries/courses";

const ZONE = Intl.DateTimeFormat().resolvedOptions().timeZone;

function groupByTopic(courses: CourseSummary[]): [string, CourseSummary[]][] {
  const groups = new Map<string, CourseSummary[]>();
  for (const course of courses) {
    const list = groups.get(course.topic) ?? [];
    list.push(course);
    groups.set(course.topic, list);
  }
  return [...groups.entries()];
}

export default function WatchPage() {
  const courses = useQuery(coursesQueryOptions());
  const refresh = useRefreshCatalog();
  if (courses.isPending) return <Spinner label="Loading courses" />;
  if (courses.isError)
    return <StateBlock tone="error" title="Could not load courses" body={courses.error.message} />;
  const { status, courses: list } = courses.data;

  if (!status.configured) {
    return (
      <StateBlock
        title="Watch is not configured"
        body={
          <p>
            Set <code>LEARNING_ROOT</code> to the mounted learning share and{" "}
            <code>LEARNING_TOPICS</code> to the folders that hold video courses, then restart.
            Istari reads the share in place and never writes to it.
          </p>
        }
      />
    );
  }

  return (
    <div className="stack">
      <div className="page-head">
        <h1>Watch</h1>
        <p>
          {list.length} courses from {status.topics.length} folders on the learning share. Watching
          is coverage, not evidence; practice supplies the evidence.
        </p>
        <p className="cluster small muted">
          {status.scanning
            ? "Scanning the share…"
            : status.scanned_at
              ? `Scanned ${formatDateTime(status.scanned_at, ZONE)}`
              : "Not scanned yet"}
          <Button
            size="sm"
            variant="ghost"
            onClick={() => refresh.mutate()}
            busy={refresh.isPending}
          >
            Rescan
          </Button>
        </p>
      </div>
      {list.length === 0 && !status.scanning ? (
        <StateBlock
          title="No courses found"
          body="The configured folders hold no video files, or the share is not mounted."
        />
      ) : null}
      {groupByTopic(list).map(([topic, mine]) => (
        <section key={topic}>
          <div className="domain-head">
            <h2>{topic}</h2>
            <span className="muted small">{mine.length} courses</span>
          </div>
          <div className="lesson-list">
            {mine.map((course) => (
              <Link
                key={course.slug}
                to="/watch/$course"
                params={{ course: course.slug }}
                className="card card--quiet lesson-row"
              >
                <span>
                  <span className="lesson-row__title">{course.title}</span>
                  <span className="lesson-row__meta">
                    {course.lecture_count} lectures · {course.caption_count} with captions
                    {course.resume_title ? ` · continue: ${course.resume_title}` : ""}
                  </span>
                </span>
                <span className="cluster">
                  {course.exam_code ? <Badge tone="gold">{course.exam_code}</Badge> : null}
                  {course.year ? <Badge>{course.year}</Badge> : null}
                  <Badge
                    tone={course.completed_count === course.lecture_count ? "success" : "info"}
                  >
                    {course.completed_count}/{course.lecture_count}
                  </Badge>
                </span>
              </Link>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
