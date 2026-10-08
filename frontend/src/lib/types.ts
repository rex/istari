/* API types, mirroring backend/app/contracts. Keep in step with /api/openapi.json. */

export type SessionMinutes = 5 | 15 | 30;
export type Confidence = "guessing" | "uncertain" | "confident";
export type SessionKind = "practice" | "assessment";

export interface SourceView {
  title: string;
  url: string;
  checked_on: string;
}
export interface ObjectiveRef {
  code: string;
  title: string;
  domain_code: string;
}

export interface UserView {
  username: string;
  csrf_token: string;
}
export interface SettingsView {
  timezone: string;
  preferred_session_minutes: number;
  exam_date: string | null;
  active_exam_version_id: number | null;
  daily_review_limit: number;
  backlog_mode: "normal" | "recovery";
  familiar_objective_codes: string[];
  onboarding_completed_at: string | null;
}
export interface TrackSummary {
  exam_version_id: number;
  code: string;
  name: string;
  certification: string;
  provider: string;
  verification_status: "verified" | "unverified";
  checked_on: string | null;
}
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
export interface MeView {
  user: UserView;
  settings: SettingsView;
  track: TrackSummary | null;
  available_tracks: TrackSummary[];
  onboarding_required: boolean;
}

export interface HealthView {
  status: "ok" | "unhealthy";
  reason: string | null;
  version: string;
  commit: string;
  built_at: string | null;
  started_at: string;
}

export interface PlanBlockView {
  kind: "resume" | "review" | "practice" | "lesson";
  count: number;
  label: string;
  reason: string;
  focus: string | null;
  session_id: number | null;
  item_key: string | null;
}
export interface ActiveSessionView {
  id: number;
  kind: SessionKind;
  answered_count: number;
  total: number;
  planned_minutes: number;
  created_at: string;
}
export interface TodayView {
  minutes: number;
  headline: string;
  blocks: PlanBlockView[];
  explanation: string[];
  active_session: ActiveSessionView | null;
  due_reviews: number;
  reviews_remaining_today: number;
  weakest: {
    code: string;
    title: string;
    first_attempts: number;
    first_correct: number;
    accuracy: number | null;
  }[];
  recent: {
    answers_7d: number;
    reviews_7d: number;
    lessons_completed: number;
    lessons_total: number;
    last_study_date: string | null;
  };
  exam: { code: string; name: string; exam_date: string | null; days_left: number | null } | null;
  quiet_win: string | null;
}

export interface OptionView {
  id: string;
  text_md: string;
}
export interface AnswerView {
  selected_option_ids: string[];
  is_correct: boolean | null;
  confidence: Confidence | null;
  first_attempt: boolean;
  answered_at: string;
}
export interface FeedbackView {
  correct_option_ids: string[];
  explanation_md: string;
  distractor_rationales: Record<string, string>;
  decisive_constraint: string;
  objectives: ObjectiveRef[];
  sources: SourceView[];
  missed_option_ids: string[];
  extra_option_ids: string[];
}
export interface SessionItemView {
  position: number;
  item_key: string;
  family_key: string;
  stem_md: string;
  select_count: number;
  difficulty: string;
  objectives: ObjectiveRef[];
  options: OptionView[];
  state: "pending" | "answered";
  draft_selection: string[] | null;
  draft_confidence: Confidence | null;
  answer: AnswerView | null;
  feedback: FeedbackView | null;
}
export interface SessionView {
  id: number;
  kind: SessionKind;
  focus: string;
  planned_minutes: number;
  status: "in_progress" | "completed" | "abandoned";
  version: number;
  created_at: string;
  completed_at: string | null;
  answered_count: number;
  correct_count: number | null;
  total: number;
  feedback_visible: boolean;
  explanation: Record<string, unknown>;
  items: SessionItemView[];
}
export interface AnswerResponse {
  item: SessionItemView;
  session_version: number;
  already_recorded: boolean;
  answered_count: number;
  total: number;
  status: SessionView["status"];
}

export interface CardView {
  id: number;
  source_kind: string;
  source_item_key: string | null;
  source_note_id: number | null;
  front_md: string;
  back_md: string;
  objectives: ObjectiveRef[];
  state: number;
  due: string;
  due_local: string;
  last_review: string | null;
  suspended: boolean;
  user_edited: boolean;
  retrievability: number | null;
}
export interface DueResponse {
  cards: CardView[];
  due_total: number;
  new_total: number;
  reviewed_today: number;
  daily_limit: number;
  remaining_today: number;
  backlog_mode: string;
  timezone: string;
}
export interface RateResponse {
  card: CardView;
  already_recorded: boolean;
  reviewed_today: number;
  remaining_today: number;
}

export interface ItemProgressView {
  position: number;
  bookmarked: boolean;
  completed_at: string | null;
  last_opened_at: string | null;
}
export interface NoteView {
  id: number;
  item_key: string | null;
  body_md: string;
  created_at: string;
  updated_at: string;
}
export interface LessonSummary {
  item_key: string;
  title: string;
  summary: string;
  estimated_minutes: number;
  objectives: ObjectiveRef[];
  domain_code: string;
  review_status: string;
  authored_by: string;
  progress: ItemProgressView;
  self_declared_familiar: boolean;
}
export interface LessonView extends LessonSummary {
  body_md: string;
  foundations_md: string;
  checks: { prompt_md: string; answer_md: string }[];
  sources: SourceView[];
  notes: NoteView[];
}

export type EvidenceLevel = "insufficient" | "weak" | "developing" | "solid";
export interface ObjectiveProgress {
  code: string;
  title: string;
  domain_code: string;
  lessons_total: number;
  lessons_completed: number;
  questions_total: number;
  families_seen: number;
  first_attempts: number;
  first_correct: number;
  first_accuracy: number | null;
  repeat_attempts: number;
  repeat_correct: number;
  repeat_accuracy: number | null;
  assessment_attempts: number;
  assessment_correct: number;
  evidence: EvidenceLevel;
  self_declared_familiar: boolean;
}
export interface DomainProgress {
  code: string;
  name: string;
  weight_percent: number;
  objectives: ObjectiveProgress[];
  first_attempts: number;
  first_correct: number;
  first_accuracy: number | null;
  lessons_total: number;
  lessons_completed: number;
}
export interface ProgressView {
  totals: {
    first_attempts: number;
    first_correct: number;
    first_accuracy: number | null;
    repeat_attempts: number;
    repeat_correct: number;
    repeat_accuracy: number | null;
    assessment_attempts: number;
    assessment_correct: number;
    assessment_sessions: number;
    lessons_total: number;
    lessons_completed: number;
    cards_total: number;
    cards_due: number;
    questions_total: number;
    families_seen: number;
  };
  domains: DomainProgress[];
  weak_areas: ObjectiveProgress[];
  confident_mistakes: {
    item_key: string;
    stem_md: string;
    objectives: ObjectiveRef[];
    answered_at: string;
    session_id: number;
    has_card: boolean;
  }[];
  recent_activity: { date: string; answers: number; reviews: number; lessons: number }[];
  flags: { invalidated_items: number; excluded_answers: number; note: string };
  next_action: PlanBlockView | null;
  evidence_note: string;
}

export interface LabSummary {
  item_key: string;
  title: string;
  estimated_minutes: number;
  objectives: ObjectiveRef[];
  evidence_count: number;
  review_status: string;
}
export interface EvidenceView {
  id: number;
  body_md: string;
  created_at: string;
  updated_at: string;
}
export interface LabView extends LabSummary {
  goals_md: string;
  prerequisites_md: string;
  cost_warning_md: string;
  steps_md: string;
  expected_observations_md: string;
  cleanup_md: string;
  sources: SourceView[];
  evidence: EvidenceView[];
}

export interface ContentItemSummary {
  key: string;
  kind: string;
  family_key: string;
  status: string;
  user_approved: boolean;
  revision: number;
  review_status: string;
  objectives: string[];
  preview: string;
  updated_at: string;
}
export interface ContentItemDetail extends ContentItemSummary {
  pack_slug: string;
  content: Record<string, unknown>;
  sources: Record<string, unknown>[];
  provenance: Record<string, unknown>;
  revisions: number[];
}
export interface ImportReportView {
  pack_slug: string;
  dry_run: boolean;
  created: string[];
  updated: string[];
  unchanged: string[];
  retired: string[];
  track_changes: string[];
  warnings: Record<string, unknown>[];
  counts: Record<string, number>;
}
