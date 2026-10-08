import { useEffect, useRef, useState } from "react";

import { type Cue, cueIndexAt, formatClock } from "@/lib/vtt";

interface TranscriptPanelProps {
  cues: readonly Cue[];
  currentTime: number;
  onSeek: (seconds: number) => void;
}

/** The lecture's captions as a readable, searchable, click-to-seek transcript. */
export function TranscriptPanel({ cues, currentTime, onSeek }: TranscriptPanelProps) {
  const [query, setQuery] = useState("");
  const [follow, setFollow] = useState(true);
  const activeRef = useRef<HTMLButtonElement>(null);
  const activeIndex = cueIndexAt(cues, currentTime);
  const needle = query.trim().toLowerCase();
  const visible = needle
    ? cues
        .map((cue, index) => ({ cue, index }))
        .filter((e) => e.cue.text.toLowerCase().includes(needle))
    : cues.map((cue, index) => ({ cue, index }));

  useEffect(() => {
    if (follow && !needle) activeRef.current?.scrollIntoView({ block: "nearest" });
  }, [activeIndex, follow, needle]);

  if (cues.length === 0) {
    return <p className="muted small">No captions for this lecture.</p>;
  }

  return (
    <div className="transcript">
      <div className="transcript__tools">
        <input
          className="input"
          type="search"
          placeholder="Search this lecture"
          aria-label="Search the transcript"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <label className="check small">
          <input type="checkbox" checked={follow} onChange={(e) => setFollow(e.target.checked)} />
          follow
        </label>
      </div>
      {needle ? (
        <p className="muted small">
          {visible.length} of {cues.length} cues match
        </p>
      ) : null}
      <ol className="transcript__cues list-reset">
        {visible.map(({ cue, index }) => (
          <li key={index}>
            <button
              type="button"
              ref={index === activeIndex ? activeRef : null}
              className={`transcript__cue ${index === activeIndex ? "is-active" : ""}`}
              onClick={() => onSeek(cue.start)}
              aria-current={index === activeIndex ? "true" : undefined}
            >
              <span className="transcript__time">{formatClock(cue.start)}</span>
              <span>{cue.text}</span>
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
