# <project-name>

<One-paragraph description of what this project does.>

## Stack

<Identify the stack: Python/FastAPI · Next.js App Router · React SPA
on Vite · Go · etc. Cross-reference the relevant `lang-*` skill.>

## Prerequisites

- <runtime, e.g. Python 3.12+ via `uv`>
- <package manager, e.g. `pnpm@9` via corepack>
- <system deps, e.g. PostgreSQL, Docker>

## Setup

```sh
make setup
```

Creates `.env` from `.env.example` (per `agentic-skeleton`'s `.env`
standard) and installs dependencies. Edit `.env` after first run and
fill in the required vars listed in `.env.example`.

## Make targets

`make help` shows the full list with grouped descriptions. Quick
reference:

- `make dev` — start the dev server.
- `make test` — run tests.
- `make validate` — lint + typecheck + architecture + version-bump gate.
- `make build` — production build.
- `make help-stack` — see which `lang-*` skill fills in the stub
  recipes for this stack.

## Env vars

See `.env.example` for the complete list. Key vars:

- `DATABASE_URL` — Postgres connection string (per `agentic-skeleton`
  database default).
- <add stack-specific vars during scaffolding>

## API docs

For HTTP services (per `agentic-skeleton`'s `/api/*` contract):

- `/api/health` — liveness probe.
- `/api/docs` — interactive API documentation.
- `/api/openapi` — OpenAPI 3.x JSON spec.

## Architecture overview

<One paragraph naming the layers: routes → services → models →
adapters. For more detail, see `AGENTS.md`.>

## Dev workflow

1. Branch from `main`: `git checkout -b feat/<slice-name>`.
2. Iterate; commit at logical-step boundaries (per `agentic-skeleton`
   git discipline).
3. `make validate` (or rely on `auto-commit.sh` to gate it).
4. Push (auto-pushed via `.git/hooks/post-commit`); open PR.

## Testing

<Whether testing is enabled or explicitly deferred. Echo
`VIBE.yaml::quality_gates.tests.mode`.>

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
