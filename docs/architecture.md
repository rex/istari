# Architecture

Istari is one FastAPI service, one PostgreSQL database and one React single-page app
served from the same origin. It is built for a single owner and optimised for being
understandable in a year, not for scale.

## Backend layers

```
routes/      HTTP only: parse, call a service, shape the response. No SQL.
services/    Use cases: sessions, answers, reviews, today, progress, content import/export.
adapters/db  SQLAlchemy models, engine, session factory.
domain/      Pure Python: grading, planner, scheduler interface, pack schema, clocks.
contracts/   Pydantic response/request models shared by routes and services.
```

`import-linter` enforces the direction: `domain` imports nothing from the app, `adapters`
may import `domain`, `services` may import both, `routes` sit on top. The module-shape gate
caps every file at eight public top-level definitions, which is why services and query
modules are split by resource.

### Authentication

One owner row (`owner`), created by `bootstrap-owner` with an argon2id hash. Login issues
a random session token stored as a SHA-256 hash in `auth_sessions` and sent as an
`HttpOnly`, `SameSite=Lax` cookie. Unsafe methods must carry the synchronizer token
(`X-CSRF-Token`, issued with the session) and an `Origin` matching the app. A sliding
window over `login_attempts` throttles failures (`LOGIN_*` settings). Security headers and
a strict CSP are added to every response.

### Study sessions and grading

A session (`study_sessions`) is a fixed list of `session_items`, each pointing at the
content revision the learner actually saw and carrying a per-session shuffled option order.
Answers are graded in `domain/grading.py`: exact-set match for multiple response, no
partial credit. The answer key lives only in `FeedbackView`, which is attached after an
item is answered (practice) or after the session completes (assessment).

Idempotency has three layers: a unique constraint on `answers.session_item_id`, a unique
`client_request_id`, and a row lock plus a savepoint fallback that returns the already
recorded answer on an `IntegrityError`. Drafts (`selected_option_ids`, confidence) are saved
with an `expected_version`; a stale tab gets a 409 and reloads.

### Review scheduling

`domain/scheduling/interface.py` defines `Scheduler` and `CardState`; `fsrs_adapter.py`
implements it with py-fsrs. Services never import py-fsrs directly, so the library can be
swapped or pinned without touching them. Card due times are stored in UTC; the owner's
timezone (default `America/Chicago`) is applied only when rendering. A daily limit caps
reviews per local day, and backlog recovery mode serves ten cards per visit, oldest first,
so a missed week never becomes a wall. Review events record state before and after, the
scheduler version and config id, so history survives algorithm changes.

### The daily plan

`domain/recommendation.py` is a pure function from `PlannerInput` to `Plan`. Budgets per
session length (5 / 15 / 30 minutes), block order (resume, reviews, practice, lesson),
weakest-objective selection (at least three first attempts and accuracy under 70 percent,
else a mixed set) and the human-readable explanation all live there; `services/today.py`
only gathers the inputs.

### Progress

Evidence is split into first attempts, repeated attempts and assessment attempts, counted
per objective and per family (variants of one scenario count once). Fewer than three first
attempts shows as "insufficient evidence". There is no readiness percentage and no pass
prediction anywhere. Items marked `invalidated` drop out of every figure while their answers
remain in the database.

### Content

Packs are strict JSON (`docs/content-schema.md`). Import is content-addressed: a changed
item becomes a new `content_revisions` row and the current pointer moves; missing items
are retired; user data is never touched. Dry runs execute inside a savepoint. Export writes
the same schema back out.

### Watch

`services/catalog.py` scans the configured topic folders under `LEARNING_ROOT` in a
worker thread (the share is remote and slow) and keeps the result in memory: every
directory with videos is a course, every directory inside it with videos is a section,
lectures sort naturally ("2 - IAM" before "10 - VPC") and pick up their caption track
by stem (`_en.srt`, ` English.vtt` and similar variants). The scan starts in the
background at startup and on demand. Routes only ever open paths the catalog itself
reported, resolved and checked against the course root, so a request can never reach a
file outside it. Video is a `FileResponse` (Starlette handles Range, so seeking works);
SRT captions become WebVTT on the fly for the browser's `<track>`. `course_progress`
stores position and completion per lecture; a position past 95 percent of the duration
marks the lecture watched. Watching is coverage, never evidence.

### Observability

Structured JSON logs with a request id on every line and in the `X-Request-ID` header;
`GET /api/health` reports version and database reachability. Errors are translated by one
exception handler from the domain exception hierarchy to HTTP problem responses.

## Frontend

`frontend/src/` is a Vite + React 19 SPA. TanStack Router (code-based routes, typed paths)
handles navigation; TanStack Query owns server state with one query module per resource
(`queries/study.ts`, `lessons.ts`, `review.ts`, `labs.ts`, `progress.ts`, `content.ts`,
`track.ts`); a small zustand store holds UI state (focus mode, shortcut help). Markdown is
rendered with `react-markdown` and `remark-gfm`, raw HTML skipped and URLs whitelisted.
Keyboard shortcuts (1–6 select options, Enter submits, Space/Enter reveals a card, 1–4
rate) are registered per page. Per-item state lives in `QuestionRunner`, remounted by key
per item so the React Compiler lint rules hold.

## Data model (tables)

`owner`, `auth_sessions`, `login_attempts`, `user_settings`, `scheduler_configs`;
`subjects` → `certifications` → `exam_versions` → `domains` → `objectives`;
`content_packs`, `content_items`, `content_revisions`, `content_item_objectives`;
`study_sessions`, `session_items`, `answers`; `review_cards`, `review_events`;
`notes`, `lab_evidence`, `item_progress`.

## Testing

- `backend/tests/unit`: grading, planner, pack validation, FSRS adapter, timeframes.
- `backend/tests/integration`: real Postgres, migrated with Alembic once per session and
  truncated per test: auth and throttling, sessions and idempotent answers, import and
  revisions, reviews and the daily limit, Today and Progress, lessons and labs, backup and
  restore into an isolated database, and the shipped pack.
- `frontend/tests`: Vitest unit and component tests; Playwright study-loop spec on
  desktop, mobile and ultrawide viewports against the built SPA served by the API.
