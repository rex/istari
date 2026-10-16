/* API shapes for learning paths. Mirrors contracts/paths.py. */

export type PathSource = "pinned" | "proposed";
export type LectureKey = [course: string, path: string];

export interface PathEntryView {
  position: number;
  course_slug: string;
  course_title: string;
  lecture_path: string;
  lecture_title: string;
  section_title: string;
  minutes: number | null;
  reason: string;
  source: PathSource;
  completed: boolean;
}

export interface ExcludedEntryView {
  course_slug: string;
  course_title: string;
  lecture_path: string;
  lecture_title: string;
}

export interface ObjectivePathView {
  objective_code: string;
  objective_title: string;
  domain_code: string;
  entries: PathEntryView[];
  excluded: ExcludedEntryView[];
  stale_courses: string[];
  total_minutes: number;
  courses: string[];
  composed_at: string | null;
  resume_position: number | null;
}

export interface PathSummaryView {
  objective_code: string;
  objective_title: string;
  domain_code: string;
  entries: number;
  completed: number;
  total_minutes: number;
}

export interface PathsView {
  exam_version_id: number;
  composed_at: string | null;
  objectives: PathSummaryView[];
}

export interface PathDecision {
  order?: LectureKey[];
  exclude?: LectureKey[];
  restore?: LectureKey[];
  reset?: boolean;
}
