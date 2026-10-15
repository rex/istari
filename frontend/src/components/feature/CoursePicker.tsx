import { useRef } from "react";

import { Badge } from "@/components/ui/Badge";
import { formatRelative } from "@/lib/format";
import type { TrackSummary } from "@/lib/types";

interface CoursePickerProps {
  tracks: TrackSummary[];
  /** the track the app is on today: gets "Current track" and the one primary button */
  currentId: number | null;
  /** the picked card (the radio value); in Settings the same as currentId */
  value: number | null;
  onSelect: (examVersionId: number) => void;
}

function countsLine(track: TrackSummary): string[] {
  const c = track.counts;
  if (!c) return [];
  const unit = (n: number, one: string) => `${n} ${n === 1 ? one : `${one}s`}`;
  return [
    unit(c.lessons, "lesson"),
    unit(c.questions, "question"),
    unit(c.cards, "card"),
    unit(c.labs, "lab"),
  ];
}

/** One card per track; a radiogroup, so arrow keys move and Enter or Space picks. */
export function CoursePicker({ tracks, currentId, value, onSelect }: CoursePickerProps) {
  const cards = useRef(new Map<number, HTMLDivElement>());
  const selectedId = value ?? tracks[0]?.exam_version_id ?? null;

  const move = (from: number, step: number) => {
    const index = tracks.findIndex((t) => t.exam_version_id === from);
    const next = tracks[(index + step + tracks.length) % tracks.length];
    if (!next) return;
    onSelect(next.exam_version_id);
    cards.current.get(next.exam_version_id)?.focus();
  };

  return (
    <div className="track-grid" role="radiogroup" aria-label="Track">
      {tracks.map((track) => {
        const selected = track.exam_version_id === selectedId;
        const current = track.exam_version_id === currentId;
        const unverified = track.verification_status === "unverified";
        return (
          <div
            key={track.exam_version_id}
            ref={(el) => {
              if (el) cards.current.set(track.exam_version_id, el);
              else cards.current.delete(track.exam_version_id);
            }}
            className={`track-card ${selected ? "is-selected" : ""}`}
            role="radio"
            aria-checked={selected}
            tabIndex={selected ? 0 : -1}
            onClick={() => onSelect(track.exam_version_id)}
            onKeyDown={(event) => {
              if (event.key === "ArrowRight" || event.key === "ArrowDown") {
                event.preventDefault();
                move(track.exam_version_id, 1);
              } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
                event.preventDefault();
                move(track.exam_version_id, -1);
              } else if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSelect(track.exam_version_id);
              }
            }}
          >
            <p className="track-card__provider">
              <span>{track.provider}</span>
              <span className="track-card__mark" aria-hidden="true">
                {selected ? "✓" : ""}
              </span>
            </p>
            <h2 className="track-card__name">{track.certification}</h2>
            <p className="track-card__meta">
              {track.code}
              {unverified ? (
                <>
                  {" "}
                  <Badge tone="warning">exam metadata unverified</Badge>
                </>
              ) : track.checked_on ? (
                ` · exam metadata verified ${track.checked_on}`
              ) : null}
            </p>
            {track.counts ? (
              <p className="track-card__counts">
                {countsLine(track).map((part) => (
                  <span key={part}>{part}</span>
                ))}
              </p>
            ) : null}
            <div className="track-card__progress">
              <div className="meter" aria-hidden="true">
                <div
                  className="meter__fill"
                  style={{ width: `${Math.round((track.progress?.fraction ?? 0) * 100)}%` }}
                />
              </div>
              <p className="track-card__meta">{track.progress?.sentence ?? "Not started"}</p>
            </div>
            <div className="track-card__foot">
              {current ? (
                <span className="track-card__current">Current track</span>
              ) : (
                <span className="track-card__meta">
                  {track.last_studied_at
                    ? `Last studied ${formatRelative(track.last_studied_at)}`
                    : "Not started"}
                </span>
              )}
              <span className={`btn btn--sm ${current ? "btn--primary" : "btn--secondary"}`}>
                {current ? "Continue" : track.progress ? "Switch" : "Start"}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

interface TrackSwitchProps {
  code: string;
  certification: string;
  open: boolean;
  onToggle: () => void;
}

/** The compact chip in a page head: the current code and name; opens the picker. */
export function TrackSwitch({ code, certification, open, onToggle }: TrackSwitchProps) {
  return (
    <button type="button" className="track-switch" aria-expanded={open} onClick={onToggle}>
      <span className="track-switch__code">{code}</span>
      <span>{certification}</span>
      <span className="track-switch__caret" aria-hidden="true">
        ▾
      </span>
    </button>
  );
}
