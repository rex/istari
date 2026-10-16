import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams, useSearch } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";

import { LectureObjectives } from "@/components/feature/LectureObjectives";
import { TranscriptPanel } from "@/components/feature/TranscriptPanel";
import { Button } from "@/components/ui/Button";
import { Kbd } from "@/components/ui/Kbd";
import { Spinner } from "@/components/ui/Spinner";
import { StateBlock } from "@/components/ui/StateBlock";
import { locateInPath } from "@/lib/paths";
import { type ShortcutBinding, useShortcuts } from "@/lib/shortcuts";
import type { PathEntryView } from "@/lib/types-paths";
import type { CourseView, LectureView } from "@/lib/types-watch";
import { type Cue, parseVtt } from "@/lib/vtt";
import {
  captionsUrl,
  courseQueryOptions,
  mediaUrl,
  useSaveLectureProgress,
} from "@/queries/courses";
import { objectivePathQueryOptions } from "@/queries/paths";
import { useUIStore } from "@/stores/ui";

const SAVE_EVERY_SECONDS = 5;
const RESUME_MARGIN_SECONDS = 10;

async function fetchCaptions(url: string): Promise<Cue[]> {
  const response = await fetch(url, { credentials: "same-origin" });
  if (!response.ok) return [];
  return parseVtt(await response.text());
}

/** Where "previous" and "next" go: the course's own order, or the learning path's. */
interface Target {
  course: string;
  path: string;
  title: string;
}

interface LecturePlayerProps {
  course: CourseView;
  lecture: LectureView;
  position: string;
  prev: Target | null;
  next: Target | null;
  pathCode: string | null;
}

/** One lecture: the video, its transcript, shortcuts, and quiet position saves. */
function LecturePlayer({ course, lecture, position, prev, next, pathCode }: LecturePlayerProps) {
  const navigate = useNavigate();
  const { mutate: save } = useSaveLectureProgress(course.slug);
  const videoRef = useRef<HTMLVideoElement>(null);
  const latest = useRef({ time: 0, duration: 0 });
  const lastSavedAt = useRef(0);
  const [currentTime, setCurrentTime] = useState(0);
  const captions = useQuery({
    queryKey: ["captions", course.slug, lecture.path],
    queryFn: () => fetchCaptions(captionsUrl(course.slug, lecture.path)),
    enabled: lecture.has_captions,
    staleTime: Infinity,
  });
  const cues = captions.data ?? [];

  const persist = (completed = false) => {
    const { time, duration } = latest.current;
    save({
      lecture_path: lecture.path,
      position_seconds: time,
      duration_seconds: duration > 0 ? duration : undefined,
      completed,
    });
  };

  const goTo = (target: Target | null) => {
    if (!target) return;
    void navigate({
      to: "/watch/$course/play",
      params: { course: target.course },
      search: pathCode ? { lecture: target.path, path: pathCode } : { lecture: target.path },
    });
  };

  // Leaving the page (or switching lectures) saves the last known position.
  useEffect(() => {
    const path = lecture.path;
    return () => {
      const { time, duration } = latest.current;
      if (time > 0) {
        save({
          lecture_path: path,
          position_seconds: time,
          duration_seconds: duration > 0 ? duration : undefined,
        });
      }
    };
  }, [lecture.path, save]);

  // Runs at key time, never during render; the native controls handle keys while the
  // video element itself is focused.
  const withVideo = (fn: (video: HTMLVideoElement) => void) => {
    const video = videoRef.current;
    if (video && document.activeElement !== video) fn(video);
  };
  const toggle = () =>
    withVideo((v) => {
      if (v.paused) void v.play();
      else v.pause();
    });
  const skip = (seconds: number) =>
    withVideo((v) => {
      v.currentTime = Math.max(0, Math.min(v.duration || Infinity, v.currentTime + seconds));
    });
  const bindings = useMemo<ShortcutBinding[]>(
    () => [
      { key: " ", description: "Play or pause", handler: toggle, allowOnControls: false },
      { key: "k", description: "Play or pause", handler: toggle },
      { key: "j", description: "Back 10 seconds", handler: () => skip(-10) },
      { key: "l", description: "Forward 10 seconds", handler: () => skip(10) },
      { key: "ArrowLeft", description: "Back 5 seconds", handler: () => skip(-5) },
      { key: "ArrowRight", description: "Forward 5 seconds", handler: () => skip(5) },
      {
        key: "f",
        description: "Fullscreen",
        handler: () => withVideo((v) => void v.requestFullscreen()),
      },
      { key: "n", description: "Next lecture", handler: () => goTo(next) },
      { key: "p", description: "Previous lecture", handler: () => goTo(prev) },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps -- the handlers read fresh state at key time
    [next, prev],
  );
  useShortcuts(bindings);

  return (
    <div className="player">
      <div className="stack">
        <p className="card__eyebrow">
          <Link to="/watch">Watch</Link> ·{" "}
          <Link to="/watch/$course" params={{ course: course.slug }}>
            {course.title}
          </Link>
        </p>
        <h1 className="player__title">{lecture.title}</h1>
        <LectureObjectives course={course.slug} path={lecture.path} />
        <video
          ref={videoRef}
          className="player__video"
          controls
          playsInline
          preload="metadata"
          src={mediaUrl(course.slug, lecture.path)}
          onLoadedMetadata={(e) => {
            const video = e.currentTarget;
            const at = lecture.progress?.position_seconds ?? 0;
            if (
              at > RESUME_MARGIN_SECONDS &&
              !lecture.progress?.completed_at &&
              at < video.duration - RESUME_MARGIN_SECONDS
            ) {
              video.currentTime = at;
            }
          }}
          onTimeUpdate={(e) => {
            const video = e.currentTarget;
            latest.current = { time: video.currentTime, duration: video.duration || 0 };
            setCurrentTime(video.currentTime);
            const since = video.currentTime - lastSavedAt.current;
            if (since >= SAVE_EVERY_SECONDS || since < 0) {
              lastSavedAt.current = video.currentTime;
              persist();
            }
          }}
          onPause={() => persist()}
          onEnded={() => {
            persist(true);
            goTo(next);
          }}
        >
          {lecture.has_captions ? (
            <track
              kind="subtitles"
              src={captionsUrl(course.slug, lecture.path)}
              srcLang="en"
              label="English"
              default
            />
          ) : null}
        </video>
        <div className="player__bar">
          <span className="cluster">
            <Button size="sm" variant="ghost" disabled={!prev} onClick={() => goTo(prev)}>
              ← {prev ? prev.title : "Start"}
            </Button>
            <Button size="sm" variant="secondary" disabled={!next} onClick={() => goTo(next)}>
              {next ? next.title : "Last lecture"} →
            </Button>
          </span>
          <span className="cluster small muted">
            {position}
            {pathCode ? (
              <Link to="/learn/path/$code" params={{ code: pathCode }}>
                path {pathCode}
              </Link>
            ) : null}
            <Button size="sm" variant="ghost" onClick={() => persist(true)}>
              Mark watched
            </Button>
            <span>
              <Kbd>?</Kbd> shortcuts
            </span>
          </span>
        </div>
      </div>
      <aside className="card card--quiet stack">
        <h3>Transcript</h3>
        {lecture.has_captions && captions.isPending ? (
          <Spinner label="Loading captions" />
        ) : (
          <TranscriptPanel
            cues={cues}
            currentTime={currentTime}
            onSeek={(seconds) => {
              const video = videoRef.current;
              if (!video) return;
              video.currentTime = seconds;
              void video.play();
            }}
          />
        )}
      </aside>
    </div>
  );
}

export default function PlayerPage() {
  const { course: slug = "" } = useParams({ strict: false });
  const search = useSearch({ strict: false });
  const lecturePath = typeof search.lecture === "string" ? search.lecture : "";
  const pathCode = typeof search.path === "string" && search.path ? search.path : null;
  const course = useQuery(courseQueryOptions(slug));
  const pathQuery = useQuery({
    ...objectivePathQueryOptions(pathCode ?? ""),
    enabled: pathCode !== null,
  });
  const setFocusMode = useUIStore((s) => s.setFocusMode);

  useEffect(() => {
    setFocusMode(true);
    return () => setFocusMode(false);
  }, [setFocusMode]);

  if (course.isPending) return <Spinner label="Opening lecture" />;
  if (course.isError)
    return (
      <StateBlock tone="error" title="Could not open this course" body={course.error.message} />
    );
  const lectures = course.data.sections.flatMap((section) => section.lectures);
  const index = lectures.findIndex((lecture) => lecture.path === lecturePath);
  const lecture = lectures[index];
  if (!lecture) {
    return (
      <StateBlock
        tone="error"
        title="Lecture not found"
        body="It may have moved on the share. Pick it again from the course page."
        action={
          <Link to="/watch/$course" params={{ course: slug }} className="btn btn--primary">
            Back to the course
          </Link>
        }
      />
    );
  }

  // Along a learning path the neighbours are the path's, whatever course they sit in.
  const inPath =
    pathCode && pathQuery.data ? locateInPath(pathQuery.data.entries, slug, lecturePath) : null;
  const fromCourse = (item: LectureView | undefined): Target | null =>
    item ? { course: slug, path: item.path, title: item.title } : null;
  const fromPath = (entry: PathEntryView | null): Target | null =>
    entry
      ? { course: entry.course_slug, path: entry.lecture_path, title: entry.lecture_title }
      : null;
  return (
    <LecturePlayer
      key={`${slug}/${lecture.path}`}
      course={course.data}
      lecture={lecture}
      position={
        inPath
          ? `${inPath.index + 1} of ${inPath.total} in path ${pathCode}`
          : `${index + 1} of ${lectures.length}`
      }
      prev={inPath ? fromPath(inPath.prev) : fromCourse(lectures[index - 1])}
      next={inPath ? fromPath(inPath.next) : fromCourse(lectures[index + 1])}
      pathCode={inPath ? pathCode : null}
    />
  );
}
