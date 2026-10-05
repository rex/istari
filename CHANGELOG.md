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
