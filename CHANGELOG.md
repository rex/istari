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
