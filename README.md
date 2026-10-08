# Istari

<p align="center"><img src="brand/istari-lockup.webp" alt="Istari" width="420"></p>

Istari is a personal certification-training platform for one learner: short lessons,
scenario practice graded on the server, spaced-repetition review cards scheduled with
FSRS, an explainable daily plan, and progress views that show evidence instead of a
readiness percentage. It ships with an AWS Certified Solutions Architect - Associate
(SAA-C03) starter pack: 8 lessons, 40 questions, 24 flashcards and 2 hands-on lab briefs,
every item sourced to AWS documentation checked on 2026-10-05.

## Stack

- **Backend** (`backend/`): Python 3.13, FastAPI, SQLAlchemy 2 async with asyncpg,
  Alembic, py-fsrs, argon2-cffi. Managed with `uv`; linted with ruff, typed with mypy
  strict, layered by import-linter.
- **Frontend** (`frontend/`): React 19, TypeScript 5.9, Vite 8, TanStack Router and
  Query, zustand, react-markdown. Managed with `pnpm`; ESLint, Prettier, Vitest,
  Playwright.
- **Database**: PostgreSQL 18 via `compose.yaml`.

## Prerequisites

- Python 3.13 and [`uv`](https://docs.astral.sh/uv/)
- Node 22+ and `pnpm` 10 (`corepack enable`)
- Docker with Compose (for Postgres; the app itself runs natively in dev)

## Setup

```sh
cp .env.example .env     # set POSTGRES_PASSWORD before the first db-up
make setup               # install, start Postgres, migrate, seed content, typecheck
make bootstrap-owner USERNAME=<you>   # prompts for the owner password
make dev                 # API on http://127.0.0.1:8000, Vite on http://127.0.0.1:5173
```

There is no default password and no sign-up: the single owner account is created by
the CLI. Log in, pick the exam version in onboarding, and start a five-question session
from Today.

## Make targets

`make help` shows the full list with grouped descriptions. Quick
reference:

- `make dev` — API + Vite dev servers.
- `make test` — backend (pytest, real Postgres) and frontend (Vitest) tests.
- `make e2e` — build the SPA and run Playwright on desktop, mobile and ultrawide.
- `make lint` / `make typecheck` / `make validate` — ruff, eslint, prettier; mypy, tsc;
  architecture, module-shape and version gates.
- `make build` — production SPA build into `backend/static`.
- `make seed` — import every `content/packs/*/pack.json` (idempotent).
- `make corpus-ingest SRC=<course dir>` / `make corpus-udemy ...` — purchased course
  material to a private, gitignored corpus and drill packs (see `docs/corpus.md`).
- `make bootstrap-owner USERNAME=<you>` — create or reset the owner.
- `make backup` / `make restore FILE=<dump> TARGET_DB=<db>` — pg_dump and a restore
  into an isolated database.
- `make docker-build` / `make docker-up` — the hardened container stack.

## Env vars

See `.env.example` for the complete list. Key vars:

- `POSTGRES_PASSWORD` — the compose database password; `DATABASE_URL` interpolates it.
- `DATABASE_URL` — asyncpg DSN. Required; there is no default.
- `TEST_DATABASE_URL` — optional; defaults to `DATABASE_URL` with `_test` appended.
- `TIMEZONE` — display timezone (storage is UTC); default `America/Chicago`.
- `SESSION_COOKIE_SECURE` — set `true` behind HTTPS.
- `GIT_COMMIT` / `BUILD_DATE` — stamped into the image by `make docker-build`; every
  page's footer shows them with the version and the process start time. Leave unset in
  development (the commit then comes from the checkout).

## API docs

For HTTP services (per `agentic-skeleton`'s `/api/*` contract):

- `/api/health` — liveness probe.
- `/api/docs` — interactive API documentation.
- `/api/openapi.json` — OpenAPI 3.x JSON spec.

## Architecture overview

Routes parse HTTP and call services; services implement use cases over SQLAlchemy
adapters; the domain layer (grading, planner, scheduler interface, pack schema) is pure
Python with no framework imports, enforced by import-linter. The SPA talks to `/api/*`
only. Details: [`docs/architecture.md`](docs/architecture.md); content packs, scoring and
import semantics: [`docs/content-schema.md`](docs/content-schema.md); running it
somewhere: [`docs/deployment.md`](docs/deployment.md).

## Content and provenance

Every lesson, question, flashcard and lab carries sources with the date they were checked,
an authorship record (the starter pack is AI-authored and labelled as such in the app),
and a review status. Items are `source_checked`, not yet `human_reviewed`; the Content
page lets the owner approve, invalidate or edit them, and edits create new revisions so
past answers keep pointing at the text that was actually seen.

## Dev workflow

1. Work on `main` (single owner) or a short branch; commit at logical boundaries.
2. Every commit bumps `VERSION` and adds a `CHANGELOG.md` entry (`make bump-minor`).
3. `make validate` and `make test`; pre-commit runs detect-secrets, gitleaks and the
   repo gates on every commit.
4. Push. The repository is public; secrets are blocked by pre-commit, CI and GitHub push
   protection.

## Testing

Testing is required (`VIBE.yaml::quality_gates.tests.mode: required`). The backend suite
runs against a real migrated Postgres database (`<DATABASE_URL>_test`), including a
backup-and-restore round trip into an isolated database and an import of the shipped pack.
Playwright drives the built SPA through login, onboarding, a five-question session with a
reload mid-session, review and progress on three viewports.

## Repo policy

Machine-readable in `VIBE.yaml`. Schema:
`agentic-skeleton/references/vibe-yaml-schema.md`.

## See also

- `AGENTS.md` — agent-collaboration container.
- `TASK_STATE.md` — current slice + standing user directives.
- `CHANGELOG.md` — versioned change log (Keep a Changelog format).
- `docs/_templates/module-README.md` — template for per-module READMEs
  inside this project.
- `docs/adr/` — architecture decision records.
