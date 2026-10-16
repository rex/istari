/* API shapes for the course comparison. Mirrors contracts/comparison.py. */

export type Currency = "current" | "older" | "newer" | "same_exam" | "other" | "unknown";

export interface DomainCoverage {
  domain_code: string;
  lectures: number;
  minutes: number;
  objectives_touched: number;
}

export interface CourseRow {
  course_slug: string;
  course_title: string;
  topic: string;
  exam_code: string | null;
  year: number | null;
  currency: Currency;
  lectures_total: number;
  lectures_captioned: number;
  lectures_mapped: number;
  lectures_completed: number;
  minutes_captioned: number;
  minutes_mapped: number;
  objectives_touched: number;
  domains: DomainCoverage[];
  /** first attempts on an objective after a lecture of this course mapped to it was watched */
  outcome_attempts: number;
  outcome_correct: number;
}

export interface ComparisonDomain {
  code: string;
  name: string;
  objectives: number;
}

export interface CourseComparisonView {
  exam_version_id: number;
  exam_code: string;
  objectives_total: number;
  indexed_at: string | null;
  scanning: boolean;
  domains: ComparisonDomain[];
  courses: CourseRow[];
}
