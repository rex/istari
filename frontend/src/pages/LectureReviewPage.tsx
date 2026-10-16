import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Kbd } from "@/components/ui/Kbd";
import { Spinner } from "@/components/ui/Spinner";
import { StateBlock } from "@/components/ui/StateBlock";
import { formatRelative } from "@/lib/format";
import { SOURCE_TONE } from "@/lib/lectures";
import { type ShortcutBinding, useShortcuts } from "@/lib/shortcuts";
import type { LectureMappingView, ReviewLectureView } from "@/lib/types-lectures";
import {
  type QueueCursor,
  indexStatusQueryOptions,
  lectureKeys,
  reviewQueueQueryOptions,
  useLectureIndexMutations,
} from "@/queries/lectures";
import { trackQueryOptions } from "@/queries/track";

function minutes(seconds: number | null): string {
  return seconds ? `~${Math.max(1, Math.round(seconds / 60))} min` : "length unknown";
}

function IndexStatus() {
  const status = useQuery(indexStatusQueryOptions());
  const { rebuild } = useLectureIndexMutations();
  const s = status.data;
  if (!s) return null;
  return (
    <section className="card card--quiet stack" aria-label="Index status">
      <div className="spread">
        <p className="cluster small muted" style={{ margin: 0 }}>
          <span>
            <strong>{s.candidate_courses}</strong> candidate courses
          </span>
          <span>
            <strong>{s.lectures_indexed}</strong> of {s.lectures_total} lectures indexed (
            {s.lectures_with_captions} with captions)
          </span>
          <span>
            <strong>{s.mappings}</strong> mappings
          </span>
          <span>
            <strong>{s.reviewed}</strong> reviewed
          </span>
          <span>{s.last_run_at ? `last run ${formatRelative(s.last_run_at)}` : "never run"}</span>
        </p>
        <Button
          size="sm"
          variant="secondary"
          busy={s.running || rebuild.isPending}
          onClick={() => rebuild.mutate()}
        >
          {s.running ? "Indexing…" : "Rebuild index"}
        </Button>
      </div>
      {s.last_error ? (
        <p className="save-status save-status--error" role="alert">
          {s.last_error}
        </p>
      ) : null}
    </section>
  );
}

function Candidate({
  mapping,
  index,
  selected,
  onToggle,
}: {
  mapping: LectureMappingView;
  index: number;
  selected: boolean;
  onToggle: () => void;
}) {
  const percent = Math.round(mapping.normalized * 100);
  return (
    <li className="card card--quiet stack">
      <div className="spread">
        <button
          type="button"
          className={`btn btn--sm ${selected ? "btn--secondary" : "btn--ghost"}`}
          aria-pressed={selected}
          onClick={onToggle}
        >
          <Kbd>{String(index + 1)}</Kbd> {mapping.objective_code} · {mapping.objective_title}
        </button>
        <Badge tone={SOURCE_TONE[mapping.source]}>{mapping.source}</Badge>
      </div>
      <div className="meter" aria-label={`match ${percent}%`}>
        <div className="meter__fill" style={{ width: `${percent}%` }} />
      </div>
      {mapping.matched_terms.length > 0 ? (
        <p className="small muted mono" style={{ margin: 0 }}>
          {mapping.matched_terms.join(" · ")}
        </p>
      ) : null}
    </li>
  );
}

/** One lecture to decide on. Keyed by lecture in the parent so its state starts fresh. */
function ReviewCard({ lecture, onSkip }: { lecture: ReviewLectureView; onSkip: () => void }) {
  const { decide } = useLectureIndexMutations();
  const track = useQuery(trackQueryOptions());
  const candidates = lecture.candidates.filter((c) => c.source !== "excluded");
  const [selected, setSelected] = useState<Set<string>>(
    () => new Set(candidates.slice(0, 1).map((c) => c.objective_code)),
  );
  const key = { course_slug: lecture.course_slug, lecture_path: lecture.lecture_path };
  const toggle = (code: string) =>
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  const bindings = useMemo<ShortcutBinding[]>(
    () => [
      { key: "a", description: "Accept as ranked", handler: () => decide.mutate(key) },
      {
        key: "p",
        description: "Pin the selected objectives",
        handler: () => {
          if (selected.size > 0) decide.mutate({ ...key, pin: [...selected] });
        },
      },
      {
        key: "x",
        description: "Exclude this lecture",
        handler: () => decide.mutate({ ...key, exclude: true }),
      },
      { key: "n", description: "Skip for now", handler: onSkip },
      ...candidates.slice(0, 9).map((c, i) => ({
        key: String(i + 1),
        description: `Toggle ${c.objective_code}`,
        handler: () => toggle(c.objective_code),
      })),
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps -- handlers read fresh state at key time
    [selected, lecture.course_slug, lecture.lecture_path],
  );
  useShortcuts(bindings, !decide.isPending);
  const objectives = track.data?.domains.flatMap((d) => d.objectives) ?? [];

  return (
    <section className="card stack" aria-label="Lecture to review">
      <p className="card__eyebrow">
        {lecture.course_title}
        {lecture.exam_code ? ` · ${lecture.exam_code}` : ""}
        {lecture.year ? ` · ${lecture.year}` : ""} · {lecture.section_title}
      </p>
      <h2 style={{ margin: 0 }}>{lecture.lecture_title}</h2>
      <p className="small muted" style={{ margin: 0 }}>
        {minutes(lecture.duration_seconds)} · {lecture.word_count} words in the captions
      </p>
      <p className="read dim" style={{ margin: 0 }}>
        {lecture.excerpt}…
      </p>
      {candidates.length > 0 ? (
        <ol className="list-reset stack" aria-label="Candidate objectives">
          {candidates.map((c, i) => (
            <Candidate
              key={c.objective_code}
              mapping={c}
              index={i}
              selected={selected.has(c.objective_code)}
              onToggle={() => toggle(c.objective_code)}
            />
          ))}
        </ol>
      ) : (
        <p className="muted">No objective scored well enough; pick one below or exclude.</p>
      )}
      <label className="field">
        <span className="field__label">Add another objective</span>
        <select
          className="select"
          value=""
          onChange={(e) => {
            if (e.target.value) toggle(e.target.value);
          }}
        >
          <option value="">Choose an objective…</option>
          {objectives
            .filter((o) => !selected.has(o.code))
            .map((o) => (
              <option key={o.code} value={o.code}>
                {o.code} {o.title}
              </option>
            ))}
        </select>
        {[...selected].some((code) => !candidates.some((c) => c.objective_code === code)) ? (
          <span className="field__hint">
            Also pinning:{" "}
            {[...selected]
              .filter((code) => !candidates.some((c) => c.objective_code === code))
              .join(", ")}
          </span>
        ) : null}
      </label>
      <div className="cluster">
        <Button variant="primary" busy={decide.isPending} onClick={() => decide.mutate(key)}>
          Accept as ranked <Kbd>a</Kbd>
        </Button>
        <Button
          variant="secondary"
          disabled={selected.size === 0 || decide.isPending}
          onClick={() => decide.mutate({ ...key, pin: [...selected] })}
        >
          Pin selected <Kbd>p</Kbd>
        </Button>
        <Button
          variant="ghost"
          disabled={decide.isPending}
          onClick={() => decide.mutate({ ...key, exclude: true })}
        >
          Exclude <Kbd>x</Kbd>
        </Button>
        <Button variant="ghost" disabled={decide.isPending} onClick={onSkip}>
          Skip <Kbd>n</Kbd>
        </Button>
        {decide.isError ? (
          <span className="save-status save-status--error">{decide.error.message}</span>
        ) : null}
      </div>
    </section>
  );
}

export default function LectureReviewPage() {
  const queryClient = useQueryClient();
  const [after, setAfter] = useState<QueueCursor>(null);
  const queue = useQuery(reviewQueueQueryOptions(after));
  const status = useQuery(indexStatusQueryOptions());
  const running = status.data?.running ?? false;
  const wasRunning = useRef(false);
  // The status polls while a build runs; when it ends, the queue and lookups are refetched.
  useEffect(() => {
    if (wasRunning.current && !running) {
      void queryClient.invalidateQueries({ queryKey: lectureKeys.all });
    }
    wasRunning.current = running;
  }, [running, queryClient]);
  const current = queue.data?.lecture ?? null;

  return (
    <div className="stack">
      <div className="page-head">
        <h1>Lecture mapping</h1>
        <p>
          Which lectures teach which objectives. Captions are read off the share and ranked against
          this track's objectives; your pins and exclusions outrank the ranking and survive every
          rebuild.
        </p>
      </div>
      <IndexStatus />
      {queue.isPending ? <Spinner label="Loading the queue" /> : null}
      {queue.isError ? (
        <StateBlock tone="error" title="Could not load the queue" body={queue.error.message} />
      ) : null}
      {queue.data ? (
        current ? (
          <>
            <p className="small muted" style={{ margin: 0 }}>
              {queue.data.remaining} left to review · {queue.data.reviewed} reviewed
            </p>
            <ReviewCard
              key={`${current.course_slug}/${current.lecture_path}`}
              lecture={current}
              onSkip={() => setAfter([current.course_slug, current.lecture_path])}
            />
          </>
        ) : queue.data.indexed === 0 && !status.data?.running ? (
          <StateBlock
            title="No lectures indexed yet"
            body="Rebuild the index to read the candidate courses' captions off the share. Courses on this track's exam family or filed under its subject are the candidates."
          />
        ) : (
          <StateBlock
            tone="success"
            title="Nothing left to review"
            body={`${queue.data.reviewed} lectures reviewed. Rebuild the index after new courses or captions land on the share; your decisions stay.`}
          />
        )
      ) : null}
    </div>
  );
}
