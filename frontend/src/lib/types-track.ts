/* Track (exam version) types, mirroring backend/app/contracts/track.py. Re-exported from
   lib/types.ts; import from there. */

import type { SourceView } from "@/lib/types";

export interface ObjectiveView {
  id: number;
  code: string;
  title: string;
  knowledge: string[];
  skills: string[];
}
export interface DomainView {
  id: number;
  code: string;
  name: string;
  weight_percent: number;
  objectives: ObjectiveView[];
}
export interface TrackCounts {
  lessons: number;
  questions: number;
  cards: number;
  labs: number;
}
/** Coverage in words and as a fraction for the meter; never a readiness score. */
export interface TrackProgress {
  fraction: number;
  sentence: string;
}
export interface TrackSummary {
  exam_version_id: number;
  code: string;
  name: string;
  certification: string;
  provider: string;
  verification_status: "verified" | "unverified";
  checked_on: string | null;
  /** filled on the list endpoints (the course picker); null on a single track's view */
  counts: TrackCounts | null;
  progress: TrackProgress | null;
  last_studied_at: string | null;
}
export interface TrackView extends TrackSummary {
  duration_minutes: number;
  scored_questions: number;
  unscored_questions: number;
  passing_scaled_score: number;
  score_scale: [number, number];
  format_notes: string;
  guide_revision: string | null;
  sources: SourceView[];
  domains: DomainView[];
}
