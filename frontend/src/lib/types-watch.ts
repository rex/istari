/* API shapes for the Watch area (courses on the learning share). Mirrors contracts/courses.py. */

export interface CatalogStatus {
  configured: boolean;
  root: string | null;
  topics: string[];
  scanned_at: string | null;
  scanning: boolean;
  course_count: number;
}
export interface LectureProgressView {
  position_seconds: number;
  duration_seconds: number | null;
  completed_at: string | null;
  last_watched_at: string | null;
}
export interface CourseSummary {
  slug: string;
  title: string;
  topic: string;
  exam_code: string | null;
  year: number | null;
  lecture_count: number;
  caption_count: number;
  completed_count: number;
  resume_path: string | null;
  resume_title: string | null;
}
export interface CoursesView {
  status: CatalogStatus;
  courses: CourseSummary[];
}
export interface LectureView {
  path: string;
  title: string;
  has_captions: boolean;
  size_bytes: number;
  progress: LectureProgressView | null;
}
export interface SectionView {
  title: string;
  lectures: LectureView[];
}
export interface CourseView {
  slug: string;
  title: string;
  topic: string;
  exam_code: string | null;
  year: number | null;
  lecture_count: number;
  completed_count: number;
  sections: SectionView[];
}
