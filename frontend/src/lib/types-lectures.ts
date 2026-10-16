/* The lecture-to-objective index. Mirrors backend/app/contracts/lectures.py and
   lecture_review.py. */

import type { Currency } from "@/lib/types-comparison";

export type MappingSource = "rule" | "lexical" | "pinned" | "excluded";

export interface LectureMappingView {
  objective_code: string;
  objective_title: string;
  domain_code: string;
  score: number;
  normalized: number;
  source: MappingSource;
  matched_terms: string[];
}
export interface LectureRef {
  course_slug: string;
  course_title: string;
  exam_code: string | null;
  year: number | null;
  lecture_path: string;
  lecture_title: string;
  section_title: string;
  duration_seconds: number | null;
  word_count: number;
}
export interface ReviewLectureView extends LectureRef {
  excerpt: string;
  candidates: LectureMappingView[];
  reviewed: boolean;
}
export interface ReviewQueueView {
  lecture: ReviewLectureView | null;
  remaining: number;
  reviewed: number;
  indexed: number;
  /** the lecture's course among the courses still pending; own-exam courses come first */
  course_index: number | null;
  courses_pending: number;
  course_currency: Currency | null;
  course_pending: number;
  section_pending: number;
}
export interface ReviewDecision {
  course_slug: string;
  lecture_path: string;
  /** objective codes to pin; empty with exclude=false accepts the lecture as ranked */
  pin?: string[];
  exclude?: boolean;
}
/** Accept as ranked, or exclude, every unreviewed lecture of a course or one section. */
export interface CourseDecision {
  course_slug: string;
  section_title?: string;
  exclude?: boolean;
}
export interface IndexStatusView {
  exam_version_id: number;
  candidate_courses: number;
  lectures_total: number;
  lectures_with_captions: number;
  lectures_indexed: number;
  mappings: number;
  reviewed: number;
  running: boolean;
  last_run_at: string | null;
  last_error: string | null;
}
export interface ObjectiveLectureView extends LectureRef {
  score: number;
  normalized: number;
  source: MappingSource;
  matched_terms: string[];
}
export interface ObjectiveLecturesView {
  objective_code: string;
  objective_title: string;
  lectures: ObjectiveLectureView[];
}
