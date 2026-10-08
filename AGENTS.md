# AGENTS.md

<!-- Single source of truth for Claude Code, Codex, Gemini CLI, Cursor, Copilot.
     CLAUDE.md and GEMINI.md are symlinks to this file. Keep under 150 lines. -->

## 1. Project snapshot
- **What**: Istari is a single-owner certification-training web app: lessons, scenario practice graded server-side, FSRS-scheduled review cards, an explainable daily plan and honest progress evidence. Ships with an AWS SAA-C03 starter pack (`content/packs/`).
- **Runtime**: Python 3.13 · FastAPI · SQLAlchemy 2 async + asyncpg · Alembic · py-fsrs · argon2-cffi (`backend/`); React 19 · TypeScript 5.9 · Vite 8 · TanStack Router/Query · zustand (`frontend/`); PostgreSQL 18.
- **Infra**: `compose.yaml` (db + app) and a hardened `Dockerfile`. No cloud resources, no AWS credentials. `docs/deployment.md` names no hosts.
- **Owner**: Pierce (@rex). Work is tracked in Rivendell (GitHub issues on rex/istari); nothing else.
- **Non-goals**: multi-user accounts, public deployment, readiness percentages or pass predictions, provisioning anything in AWS, runtime LLM content generation.

## 2. Setup

```bash
cp .env.example .env            # set POSTGRES_PASSWORD before the first db-up
make install                    # uv sync (backend) + pnpm install (frontend)
make db-up db-migrate seed      # Postgres on 127.0.0.1:5433, schema, content packs
make bootstrap-owner USERNAME=<you>   # prompts for the password; no default exists
make dev                        # API :8000 + Vite :5173
```

## 3. Commands the agent MUST run before declaring done

- `make lint`
- `make typecheck`
- `make test`  (required: pytest against `<DATABASE_URL>_test` + vitest)
- `make e2e`  when a page or flow changed (Playwright: desktop, mobile, ultrawide)
- `make validate`  (architecture, module shape, version gate; pre-commit mirrors it)
- `make check-skeleton` — skeleton-owned files (`scripts/`, `.claude/{hooks,commands,agents,rules}`) match the installed agentic-skeleton; if behind, `make sync-skeleton`, then commit + push
- If `infra/**` changed: `terraform fmt -recursive infra/ && terraform validate`
- If `ansible/**` changed: `ansible-lint ansible/ && ansible-playbook --syntax-check`

## 4. Repo layout

```
backend/app/       routes → services → adapters/db + domain (import-linter enforces the layers)
backend/alembic/   Migrations: autogenerate, then review. Pass REV_ID=<slug> (see §9)
backend/tests/     unit/ (pure domain) + integration/ (real Postgres, migrated per session)
frontend/src/      pages/, components/{layout,ui,feature}, queries/ (one module per resource), lib/, styles/
frontend/tests/    unit/ + component/ (Vitest, RTL), e2e/ (Playwright)
content/packs/     pack.json per pack; schema in docs/content-schema.md
content/private/   drill packs from purchased material: gitignored, never committed (docs/corpus.md)
corpus/            converted course text (transcripts, books): gitignored, never committed
docs/              architecture.md, content-schema.md, deployment.md, adr/
scripts/           Gates, bump_version.py, backup.sh / restore.sh
.claude/           Hooks, rules, commands, MCP config
```

## 5. Code style (non-negotiable)

See `CONVENTIONS.md`. Linters enforce formatting and import order — **do not
write style rules here that the linter already checks.**

## 6. Testing policy

See `VIBE.yaml` (`quality_gates.tests`). If testing is `required`, every code
change gets a corresponding test update.

## 7. Security (hard stops)

- No secrets committed. `detect-secrets` + gitleaks enforce.
- Parameterized queries only.
- No wildcard IAM. No `0.0.0.0/0` except 443 on ALBs.
- MCP credentials never touch `.env` — they resolve at connect time through
  `scripts/mcp/op-headers.sh` and degrade to OAuth / anonymous tier.
- See `.claude/rules/security.md` for full checklist.

## 8. Architectural decisions

- Read `docs/adr/README.md` index before proposing layering / DB / auth / deploy changes.
- New decisions: create ADR (`docs/adr/template.md`), merge, THEN implement.

## 9. Things agents get wrong here

<!-- Update whenever an agent makes the same mistake twice. -->

- The PostToolUse auto-lint hook runs `ruff --fix` after every edit and deletes imports that are not used *yet*. Write the usage first, add the import second.
- The same hook rewrites `Literal["ok", "unhealthy"]` inside a function signature into bare names (`Literal[ok, unhealthy]`). Define literal types as module-level aliases (`HealthStatus = Literal[...]`, as `contracts/session.py` does) and annotate with the alias.
- `DATABASE_URL` is required (no default DSN with a password in code). `TEST_DATABASE_URL` defaults to it with `_test` appended. The e2e target derives `E2E_DATABASE_URL` from the backend settings; do not hard-code a DSN in TypeScript.
- `detect-secrets` runs in pre-commit: no literal passwords even in tests (`conftest` generates one per run), and Alembic revision ids must not be hex (`make db-revision MSG=... REV_ID=0002_<slug>`).
- `bash-guard` blocks `DROP DATABASE`. Empty a database with `alembic downgrade base`, never with SQL.
- Module-shape gate: at most 8 public top-level defs per file. In TS, `export const`/`export function` count, `export type`/`interface` do not. Split by resource (see `frontend/src/queries/`).
- `pytest-asyncio` needs `asyncio_default_test_loop_scope = "session"` (set) because the engine fixture is session-scoped.
- Pin `typescript@5`: typescript-eslint rejects TS 7. Vite 8 resolves tsconfig paths natively (`resolve.tsconfigPaths`).
- React Compiler lint rules are on: per-item state lives in a keyed child (`QuestionRunner`), derived lists replace effect-synced state, refs are not read during render.
- `app` is importable only with `backend/` as the working directory (`[tool.uv] package = false`). A background job or a script run from elsewhere must use `uv run --directory backend python -m app.cli …`.
- Content: item slugs and option ids are permanent once shipped (answers reference them). Change text by re-importing (new revision); never rename. The pack field is `slug`, not `key`: gitleaks reads `"key": "<value>"` as a credential.

## 10. Workflow

1. Read `PROGRESS.md` (session orientation) then `TASK_STATE.md` §0 and current slice.
2. Read `CONVENTIONS.md` before editing code.
3. Use `MAP.md` for exploration; `agent_docs/` for deep-dive detail.
4. Use Context7 MCP for up-to-date library docs; don't rely on training data.

## 11. When ending a session

- Update `TASK_STATE.md` §6 (Handoff note).
- Update `PROGRESS.md` "Last session".
- Propose AGENTS.md updates for durable new facts — don't accumulate tribal
  knowledge in auto-memory.

## 12. Subdirectory AGENTS.md (precedence: nearest wins)

- `infra/AGENTS.md` — Terraform/Ansible specific (safe commands, forbidden ops)
- `app/<domain>/AGENTS.md` — domain-specific invariants

## 13. Composition with skills

This repo was bootstrapped with:
- `agentic-skeleton` (collaboration container — this file's shape — plus
  universal contracts: VIBE.yaml core schema, .env standard, /api/health
  contract, flat layout, line limits, Pushover)
- `lang-python`, `lang-react-spa`, `lang-docker` (code-style patterns +
  stack-specific implementation of the contracts)

Add new durable rules to the RIGHT skill, not to this file. Transient context
goes in `TASK_STATE.md`; never here.
