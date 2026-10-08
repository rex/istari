# Changelog

All notable changes to this project are documented here. This project
follows [Semantic Versioning](https://semver.org/) and
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Format:

```markdown
## [X.Y.Z] — YYYY-MM-DD — Agent: <name>
### Added | Changed | Fixed | Removed | Deprecated | Security
- <what changed, in imperative voice>
```

**Every commit requires a version bump and a matching entry here.** The
`scripts/check_version_bumped.py` gate enforces this; `auto-commit.sh`
calls `scripts/bump_version.py <level>` before commit.

**Bump level guidance** (agent decides per slice):
- `patch` — bug fix, documentation change, refactor with no behavior change
- `minor` — new feature, new public API, any backward-compatible addition
- `major` — breaking change, removal, incompatible behavior change

**Agent attribution is required.** Every entry names the agent (or human)
that authored the change. This is how we keep `git blame` honest when
multiple agents and humans work on the same slice.

Append new entries at the top. One entry per commit (same cadence as
version bumps).

---

## [0.6.0] — 2026-10-08 — Agent: Claude Fable 5.1
### Added
- `scripts/entrypoint.sh` is the container command: `alembic upgrade head`, the pack
  import (`seed`, skipped with `ISTARI_SEED_ON_START=false`), the owner account from
  `ISTARI_OWNER_USERNAME` and `ISTARI_OWNER_PASSWORD` when the database has none yet,
  then uvicorn. A failing step stops the container.
- `bootstrap-owner --if-missing` keeps an existing owner and exits 0, so a restart or a
  rotated secret never replaces the account; `--username` falls back to
  `ISTARI_OWNER_USERNAME`. The shared logic lives in `app/cli/owner.py` with tests.
- `.gitea/workflows/ci.yml`: on a Gitea instance, every push runs `make validate` and
  `make test` against a throwaway Postgres service container (trust authentication, so the
  workflow holds no credential); a push to `main` builds the image and pushes it to that
  instance's registry, derived from the server URL, tagged `latest` and with the commit
  sha, with three push attempts. The file names no hosts.
- `docs/deployment.md`: entrypoint behaviour, the owner variables, the CI flow and a
  hostname-free Kubernetes note (probes on `/api/health`, read-only `LEARNING_ROOT`).

## [0.5.1] — 2026-10-08 — Agent: Claude Fable 5.1
### Changed
- Handoff notes: corpus ingest totals, roadmap issues #29-#39

## [0.5.0] — 2026-10-07 — Agent: Claude Fable 5.1
### Added
- Watch: the video courses on the learning share, inside Istari. `LEARNING_ROOT` and
  `LEARNING_TOPICS` name the mounted share and its course folders; a background scan
  lists every directory with videos as a course, its subdirectories as sections, with
  lectures in natural order and their caption tracks matched by stem. The share is read
  in place and never written.
- `/watch` lists courses grouped by topic with exam code, year, caption coverage and a
  "continue" lecture; `/watch/<course>` lists sections and lectures with progress;
  `/watch/<course>/play` streams the lecture (Range requests, so seeking works) with
  the subtitle track as WebVTT (SRT converted on the fly), resumes where you left off,
  saves position every five seconds and on pause, marks a lecture watched at 95 percent
  or on "Mark watched", and moves on to the next lecture when one ends.
- Transcript panel beside the video: the captions as searchable, click-to-seek text
  with the current cue highlighted and followed.
- Keyboard: Space/k play or pause, j/l ±10 s, arrows ±5 s, f fullscreen, n/p next or
  previous lecture; listed in the shortcuts help.
- `course_progress` table (migration `0002_course_progress`), `/api/courses` endpoints,
  and tests: naming and caption rules, catalog scan of a temporary tree, byte-range
  streaming, caption conversion, progress round trip, path safety (only catalogued paths
  resolve), VTT parsing and the transcript panel.
### Changed
- Exam-code inference, slugs and natural sorting moved to `domain/naming.py`, shared by
  the corpus tooling and the catalog.

## [0.4.0] — 2026-10-07 — Agent: Claude Fable 5.1
### Added
- Private corpus tooling (`backend/app/corpus/`): subtitle tracks (SRT, WebVTT) become
  readable transcript text; HTML, EPUB, DOCX go through pandoc and PDFs through
  pdftotext; `corpus-ingest` walks one course directory into a gitignored
  `corpus/<course>/` with a manifest (exam code and year inferred from the name,
  every file written or skipped with a reason); `--all` treats a topic folder as a set
  of courses. The source directory is never written.
- `corpus-udemy`: Udemy section-quiz HTML exports and practice-test results PDFs parse
  into a private pack (`content/private/`, gitignored) in Istari's own schema: items
  are `draft`, authored by the vendor, not source-checked, grouped into domains by quiz
  or test, under an `<EXAM>-DRILL` exam version so they never mix with a verified
  pack. Invalid questions are reported and left out. `make corpus-ingest` and
  `make corpus-udemy` wrap both.
- `docs/corpus.md`: what the corpus is for (coverage maps, drafting input, drill), what
  it is not (a fact source), the commands, and the currency table for the AWS library.
- Unit tests for captions, ingestion, both Udemy parsers and the private-pack builder,
  all on synthetic samples shaped like the exports.

## [0.3.0] — 2026-10-07 — Agent: Claude Fable 5.1
### Added
- Every page, the login page included, shows a build badge: version, git commit short
  hash, image build time and the process start time ("up since"). The API is the source
  of truth (`/api/health` now reports `version`, `commit`, `built_at`, `started_at`);
  the SPA embeds its own commit and says so when it differs from the API's.
- `backend/app/buildinfo.py` resolves the stamp once at startup: `GIT_COMMIT` and
  `BUILD_DATE` from the environment, else `git rev-parse --short HEAD` in a checkout,
  else `unknown`. The startup log line names version, commit and build time.
- `make docker-build` / `make docker-up` pass `APP_VERSION`, `GIT_COMMIT` and
  `BUILD_DATE` as build args; the image carries them as environment variables and OCI
  labels (`org.opencontainers.image.{version,revision,created,source}`).
- Tests: build-info resolution (unit), health body (integration), `BuildBadge`
  (component, including the stale-bundle warning), badge on login and Today (e2e).
### Changed
- Skeleton synced to agentic-skeleton 0.50.0: `scripts/check_skills.py` and
  `scripts/stamp_skill.py` added, provenance stamped in `VIBE.yaml`. The Makefile
  keeps its repo-specific recipes (advisory drift, reconciled by hand).
### Fixed
- The very first `GET /api/me` on a fresh database created the settings row without
  protection, so two overlapping first requests (the SPA's post-login refetch plus any
  second tab or probe) made one of them fail with a 500. The insert now runs in a
  savepoint and the loser reads the winner's row. Regression test added.
- Playwright: the keyboard-shortcut test decided "abandon or start" before the
  active-session request had answered; it now waits for that response. The login helper
  fails loudly when its `/api/me` probe is not 200 instead of silently skipping
  onboarding.

## [0.2.0] — 2026-10-05 — Agent: Claude Fable 5.1
### Added
- `content/packs/aws-saa-c03-starter/pack.json`: 8 lessons, 40 scenario questions
  (2 multiple-response), 24 flashcards and 2 lab briefs covering all 14 SAA-C03 task
  statements; exam metadata verified against the official exam guide and certification
  page on 2026-10-05; every item AI-authored, `source_checked` against AWS documentation.
- `tests/integration/test_real_pack.py` pins the pack's counts, objective coverage,
  provenance and a clean idempotent import (backend suite: 75 tests).
- `docs/architecture.md`, `docs/content-schema.md` (scoring policy and import semantics),
  `docs/deployment.md` (no assumed hostnames); AGENTS.md, README.md and TASK_STATE.md
  filled in; `.claude/session-context.md`.
### Changed
- Pack items identify themselves with `slug` instead of `key`: gitleaks reads
  `"key": "<value>"` as a generic API key, and a public repo cannot carry that false
  positive in every pack. The API and database keep `item_key`.
- Option ids in the pack schema may be up to 32 characters (descriptive slugs).
- `make e2e` exports `E2E_DATABASE_URL` for the whole recipe; the Playwright global setup
  resolves paths with `import.meta.url` (the frontend is an ES module package).
- Playwright spec: onboarding is completed deterministically by asking `/api/me`, and
  the five-question session starts from the Practice page, because a fresh pack rightly
  puts due flashcards first in the Today plan.
- `make lint` and `make fix` recipes no longer chain two `cd` commands.
### Fixed
- Progress summary and domain headers counted a lesson once per objective it teaches
  (the shipped pack showed 0/14 lessons for 8 lessons). Distinct lessons are counted
  now; per-objective rows are unchanged. Covered by `test_progress_counts_each_lesson_once`.
- First full Playwright run: 9 passed on desktop, mobile and ultrawide.

## [0.1.0] — 2026-10-05 — Agent: Claude Fable 5.1
### Added
- Project scaffold from `agentic-skeleton` (AGENTS.md, VIBE.yaml, Makefile
  gates, `.claude/` hooks, pre-commit with detect-secrets + gitleaks).
- Backend (FastAPI + SQLAlchemy async + Alembic): single-owner auth with
  argon2id, server sessions, CSRF and login throttling; subject →
  certification → exam version → domain → objective model; practice
  sessions with server-side grading, exact-set multi-answer, confidence
  and idempotent answers; py-fsrs review scheduling behind an interface
  with a daily limit and backlog recovery; Today planner; Progress
  evidence views; lessons, notes, labs with evidence; content pack
  import/export with strict validation, revisions and retirement;
  operator CLI (`bootstrap-owner`, `seed`, `import-pack`, `export-pack`,
  `validate-pack`); `/api/health`; structured logs with request ids.
- Frontend (React 19 + Vite 8 + TanStack Router/Query): Today, Learn,
  Practice, Review, Progress, Labs, Settings and Content pages with
  keyboard shortcuts, focus mode, sanitized Markdown and brand assets.
- Postgres compose stack, hardened Dockerfile, backup/restore scripts
  with a tested restore into an isolated database, secret-scan CI
  workflow.
- Backend tests (73) and frontend unit/component tests (16).
- `make db-revision REV_ID=<slug>` to give Alembic revisions descriptive ids; the
  initial migration is revision `0001`.
### Changed
- `DATABASE_URL` is required (no default DSN with a password); `TEST_DATABASE_URL` derives
  from it. `.env.example` and compose interpolate `POSTGRES_PASSWORD`; compose refuses to
  start without it. Playwright takes its DSN from `E2E_DATABASE_URL` only.
- Modules over the eight-public-definition cap are split by resource:
  `contracts/session_requests.py`, `domain/planning_types.py`,
  `services/progress_activity.py`, `queries/{lessons,review,labs,progress,track}.ts`.
### Security
- Test owner passwords are generated per run; no literal credentials are in the tree
  (detect-secrets and gitleaks pass on every file).
