import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "@tanstack/react-router";

import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { StateBlock } from "@/components/ui/StateBlock";
import type { CourseView, LectureView } from "@/lib/types-watch";
import { formatClock } from "@/lib/vtt";
import { courseQueryOptions } from "@/queries/courses";

function lastWatched(course: CourseView): LectureView | null {
  let best: LectureView | null = null;
  for (const section of course.sections) {
    for (const lecture of section.lectures) {
      const at = lecture.progress?.last_watched_at;
      if (at && (!best?.progress?.last_watched_at || at > best.progress.last_watched_at)) {
        best = lecture;
      }
    }
  }
  return best;
}

function progressBadge(lecture: LectureView) {
  const p = lecture.progress;
  if (!p) return <Badge>unwatched</Badge>;
  if (p.completed_at) return <Badge tone="success">watched</Badge>;
  if (p.duration_seconds)
    return (
      <Badge tone="info">{Math.round((p.position_seconds / p.duration_seconds) * 100)}%</Badge>
    );
  return <Badge tone="info">at {formatClock(p.position_seconds)}</Badge>;
}

export default function CoursePage() {
  const { course: slug = "" } = useParams({ strict: false });
  const course = useQuery(courseQueryOptions(slug));
  if (course.isPending) return <Spinner label="Opening course" />;
  if (course.isError)
    return (
      <StateBlock tone="error" title="Could not open this course" body={course.error.message} />
    );
  const data = course.data;
  const resume = lastWatched(data);

  return (
    <div className="stack">
      <div className="page-head">
        <p className="card__eyebrow">
          <Link to="/watch">Watch</Link> · {data.topic}
        </p>
        <h1>{data.title}</h1>
        <p className="cluster">
          {data.exam_code ? <Badge tone="gold">{data.exam_code}</Badge> : null}
          {data.year ? <Badge>{data.year}</Badge> : null}
          <Badge tone="info">
            {data.completed_count}/{data.lecture_count} watched
          </Badge>
          {resume ? (
            <Link
              to="/watch/$course/play"
              params={{ course: data.slug }}
              search={{ lecture: resume.path }}
              className="btn btn--primary btn--sm"
            >
              Continue: {resume.title}
            </Link>
          ) : null}
        </p>
      </div>
      {data.sections.map((section) => (
        <section key={section.title}>
          <div className="domain-head">
            <h2>{section.title}</h2>
            <span className="muted small">{section.lectures.length} lectures</span>
          </div>
          <div className="lesson-list">
            {section.lectures.map((lecture) => (
              <Link
                key={lecture.path}
                to="/watch/$course/play"
                params={{ course: data.slug }}
                search={{ lecture: lecture.path }}
                className="card card--quiet lesson-row"
              >
                <span>
                  <span className="lesson-row__title">{lecture.title}</span>
                  <span className="lesson-row__meta">
                    {lecture.has_captions ? "captions" : "no captions"} ·{" "}
                    {(lecture.size_bytes / 1_048_576).toFixed(0)} MB
                  </span>
                </span>
                <span className="cluster">{progressBadge(lecture)}</span>
              </Link>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
