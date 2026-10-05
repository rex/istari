# TASK_STATE — Istari V1

> Source of truth for in-flight work. Humans and agents both write here.
> This file is **committed** to the repo. It survives sessions, machines,
> and context compactions.
>
> Spec: the implementation brief `istari-agent-kickstart.md` (Pierce's copy, not committed) · Plan: Rivendell rex/istari#1 (parent) with #2, #3, #4, #5
> Branch: `main` · Owner (human): @rex · Last update: 2026-10-05 by Claude Fable 5.1

## 0. TL;DR for a fresh agent session

V1 is implemented: backend, SPA, SAA-C03 starter pack, docs, backup/restore, e2e. All
gates are green (see §6 for the exact numbers). The next human step is reviewing the
AI-authored pack items on the Content page and approving or editing them. Do NOT rename
item slugs or option ids in `content/packs/aws-saa-c03-starter/pack.json`: answers and
cards reference them; change text and re-import instead.

## Standing user directives

<!-- Durable per-task directives from Pierce that must survive compaction. -->

- 2026-10-05: build from the kickstart brief; make reasonable, reversible decisions without stopping for routine clarifications; implement, run and test; report what works, what was tested, what remains.
- 2026-10-05: the GitHub repo is public (rex/istari) and secrets must be actively watched (pre-commit detect-secrets + gitleaks, CI gitleaks, GitHub secret scanning + push protection).
- Brief: do not modify homelab infrastructure, open ports, deploy publicly, run cloud commands, or provision AWS resources. Istari needs no AWS credentials.

## 1. Phases

| # | Phase | Status | Exit criteria |
|---|---|---|---|
| 1 | Slice 1: foundations, migrations, owner login, validated content, five-question session (#2) | ✅ done | login + onboarding + session persists across reload; pack validates and seeds; pytest + e2e green |
| 2 | Slice 2: durable resume, sourced explanations, lessons, FSRS cards, explainable plan (#3) | ✅ done | Today resumes an open session; feedback shows sources; Review schedules with py-fsrs; plan explains itself |
| 3 | Slice 3: honest progress, content editor/import/export, lab evidence, backup/restore, a11y/responsive, regression coverage (#4) | ✅ done | Progress shows evidence not readiness; import dry-run; restore into isolated db tested; 3 viewports in e2e |
| 4 | Deployment notes (#5) | ✅ done | `docs/deployment.md` without assumed hostnames |
| 5 | Human review of pack content | ⏸ pending | items move from `source_checked` to `human_reviewed` or are edited |

Statuses: `⏸ pending` · `🟡 in-prog` · `✅ done` · `🔴 blocked`

## 2. Slices (vertical, atomic, independently mergeable)

### Slice 5.1 — Review the SAA-C03 pack items

- Status: ⏸ pending
- Owner: Pierce (human review is the point)
- Files (planned edits): `content/packs/aws-saa-c03-starter/pack.json` (re-import after edits)
- Files (do NOT edit): item `slug` and option `id` values
- Depends on: (none)
- Acceptance:
  - [ ] When an item is read and judged correct, the owner marks it approved on the Content page or sets `review_status: human_reviewed` in the pack.
  - [ ] If an item is wrong, the owner edits the pack and re-imports; the old revision stays attached to past answers.
  - [ ] Tests: `tests/integration/test_real_pack.py` still passes (counts and coverage).

## 3. Blockers / open questions

- GitHub's `secret_scanning_non_provider_patterns` could not be enabled through the REST API (stays `disabled`); gitleaks covers generic patterns. Flip it in Settings > Code security if wanted.
- The HTML exam guide shows no version string, so `exam_version.guide_revision` is unset.

## 4. Recent decisions (append-only, newest first)

- 2026-10-05 — Option ids are descriptive slugs up to 32 chars (schema widened from 16); never letters (Claude Fable 5.1, pack authoring).
- 2026-10-05 — `DATABASE_URL` has no default; `TEST_DATABASE_URL` derives from it. The e2e DSN comes from backend settings via `make e2e` (Claude Fable 5.1, detect-secrets gate).
- 2026-10-05 — Alembic revision ids are descriptive (`0001`), generated with `--rev-id`; `make db-revision REV_ID=` supports it (Claude Fable 5.1, detect-secrets gate).
- 2026-10-05 — Modules over the 8-public-def cap were split by resource: `contracts/session_requests.py`, `domain/planning_types.py`, `services/progress_activity.py`, `queries/{lessons,review,labs,progress,track}.ts` (Claude Fable 5.1, module-shape gate).
- 2026-10-05 — Stack per the brief's defaults: FastAPI + SQLAlchemy async + Alembic + py-fsrs; React 19 + Vite 8 + TanStack; Postgres 18 (Claude Fable 5.1, greenfield).

## 5. Next actions (ordered)

1. Pierce: `make bootstrap-owner USERNAME=<you>`, log in, run a five-question session, review the Content page.
2. Pierce: review pack items; approve or edit and re-import.
3. Agent: file follow-ups in Rivendell as they surface (none open beyond content review).

## 6. Handoff note (fill when ending a session)

2026-10-05 (Claude Fable 5.1): V1 built end to end in one session. Gates at handoff:
pytest 75 passed (includes backup→restore into `istari_restore_test` and the real-pack
import), vitest 16 passed, Playwright study-loop spec on desktop/mobile/ultrawide (see
CHANGELOG 0.2.0 for the run result), ruff/mypy/import-linter/tsc/eslint/prettier clean,
pre-commit (detect-secrets, gitleaks, architecture, module shape, version) clean. Dev
database is migrated and seeded; no owner account was created (Pierce picks the password).
