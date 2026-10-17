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

Figures (rex/istari#78) are drawings of the thing a lesson teaches: SVG with the provider's
own icons, rendered offline from a script beside the pack and checked at import to be inert
(no scripts, handlers, embedded documents or external references). `/api/figures/{key}.svg`
serves the current revision. A figure is its own item, mapped to objectives and nothing
else: a lesson lists the figures it shows and places them in its body with
`![alt](figure:slug)`, the viewer renders them as captioned figures, and a lecture borrows
the figures of the objectives it is mapped to (`/api/figures/lecture/{course}?path=`,
pinned and ruled mappings first, excluded ones bringing nothing; the player's "See it"
rail). Nothing in a figure knows which course or lecture shows it, so a per-course
variant later is another mapping, not another drawing.

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

### Lecture index

Which lectures teach which objectives. `services/lecture_index.py` picks the candidate
courses for the active track (same exam family, or filed under the track's subject), reads
their captions off the share in a worker thread, and stores each lecture as term counts in
`indexed_lectures` (never the transcript). `domain/lecture_index.py` is the pure part: a
tokenizer that keeps service names whole, a BM25 index over the lectures, a weighted query
per objective from its title, knowledge and skills statements and the lessons and questions
mapped to it, an objective-specificity weight that zeroes the words every objective shares,
and title rules (an objective code named in a file name outranks the ranking, but only in
a course of the track's own exam family, since another exam's "(OBJ 4.3)" names that exam's
objective; a domain's distinctive word in a section title lifts its objectives). Two measured
adjustments (rex/istari#67): a term in more than 40% of the lectures is left out of the
scoring, and each objective's score is divided by its query's mass, so the objectives with
the most lessons and questions do not win on count alone; a welcome, a tour of the course or
a support lecture maps to nothing. `make lectures-eval` ranks a hand-labelled sample (kept
with the corpus, never committed) under any parameter set and prints the rates and every
miss; `services/lecture_eval.py` is that harness, and the levers it exposes but does not ship
(an absolute floor, a section prior, lighter lesson bodies) were measured and gained
nothing on the first sample. Results land in
`lecture_objectives` with a source: `rule`, `lexical`, or the owner's `pinned` and
`excluded`, which every rebuild keeps. `services/lecture_queue.py` serves the review queue:
one unreviewed lecture at a time with its candidates and an excerpt, the courses for the
track's own exam first (by `course_currency`), with the lecture's place among the pending
courses and how much of its course and section is left; a decision can take one lecture,
or a whole section or course at once (one `lecture_reviews` row per lecture either way).
`services/lecture_mapping.py` records the per-lecture decisions and answers the two lookups:
a lecture's objectives and an objective's lectures. One build runs at a time, in the background, with its own session, and rescans
the catalog before it reads a caption, so a rebuild is how new courses get in; its status
is a row in `lecture_index_runs`.

### Courses compared

`services/course_comparison.py` answers which courses are worth the time for a track: every
candidate course of the index with its lectures and captions from the catalog, the minutes of
captioned lecture time mapped to each domain and the objectives touched from
`lecture_objectives` (excluded rows left out), its exam against the track's (`currency`: the
same version, an older or newer one, the same certification with no version named, another
exam, or none named in its folder; `domain/naming.py` reads the certification's name out of
a title, since most downloaded courses carry the name and no code, and reads the same
family at another level, Professional against Associate, as another exam; a year in such a
title is read against the pack's `current_since`, the date this exam version replaced the
previous one, so a 2018 Solutions Architect Associate course is an older version and a 2024
one is this version, while the same year or no year says nothing) and the lectures
the owner has completed. Figures only; the page at `/watch/compare` sorts them and
says in words that coverage and currency are not quality. Minutes come from captions, so a
course without them cannot be measured and the page says so.

### Learning paths

`domain/learning_path.py` composes one path per objective from the lectures mapped to it:
the course with the deepest coverage of the objective (minutes of mapped captions weighted
by match strength) supplies a run of its lectures, its most relevant sections first and in
course order within a section; a course made for this exam leads when it has half the
deepest depth or two hours of mapped lectures of its own; the other courses' strongest
lectures fill in behind it (skipping titles the run already covers), a course for an older
version of the exam steps aside when a current one has at least half its minutes, and the
whole thing is capped at two hours. `services/learning_path.py` keeps the result in `objective_path_entries`:
`proposed` rows are rewritten by every index run and every decision, `pinned` rows (the
owner's order) and `excluded` rows stay. `/api/paths` serves the summaries, one objective's
path with the reason per entry and where to resume, and the owner's decisions; the player
follows a path when the `path` search parameter names one, and the planner takes the next
unwatched lecture of the weakest objective's path into a 30-minute plan. Never a merged
video: every entry is one lecture of one course, attributed to it.

### Watch outcomes

`services/watch_outcomes.py` says what watching did, with the samples in plain sight. Per
objective: the mapped lectures watched to the end and the first-attempt answers on that
objective split at the first of those watches (`watch` on the objective's Progress row,
labelled correlation, never mastery). Per course: the first attempts on an objective after
a lecture of that course mapped to it was watched, the comparison's "After watching"
column, which reads as a rate only from three attempts on.

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

### Styles

The identity is the Istari design system, a Design System artifact on claude.ai/design that
Pierce built on 2026-10-15 from this repository's marks and component inventory (its link is
in rex/istari#55). `frontend/src/styles/tokens.css` is the system's generated token file
(colour, type, space, radii, shadows, layout widths, timings, and the `@font-face` rules) and
`frontend/src/styles/bundle.css` its component stylesheet, written to this app's own class
names; both are the system's files, Prettier-formatted by the lint gate but otherwise
unchanged. The four typefaces (Cormorant Garamond for display, Hanken Grotesk for the
interface, Newsreader for reading, JetBrains Mono for code) ship as OFL latin subsets under
`styles/fonts/` with their licence texts; Vite hashes them into `assets/`. Under 720px the
stylesheet turns the primary nav into a bottom tab bar and the More sheet carries the rest.

The split of authority: the system is the source for tokens and rules (edit there, copy the
two files here, `make fix`, run the gates); the code is the source for markup (change a
component here, then its preview there). The system's 45 previews are static renditions of
the stylesheet, so a class the code stops emitting or starts emitting is a change to make in
both places; `rex/istari#60` records the differences found when the system was adopted.

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
