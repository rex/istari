# PROGRESS

<!-- ≤50 lines. Read this first when a fresh agent session starts.
     Points to TASK_STATE.md for the details. -->

- **Project**: Istari (FastAPI + SQLAlchemy async backend, React 19 + Vite SPA, Postgres 18)
- **Active branch**: `main`
- **Active feature spec**: none; the plan lives in Rivendell (rex/istari issues)
- **Active TASK_STATE**: `TASK_STATE.md` (phase 5 content review / phase 7 content pipeline, both waiting on Pierce)
- **Last session**: 2026-10-07 (Claude Fable 5.1, v0.3.0: build badge, first-run race fix, skeleton sync; content strategy filed as rex/istari#7–#20)

## Last three decisions

- 2026-10-07 Build stamp: the API is the source of truth (`/api/health`); the bundle embeds its own commit and warns when it differs.
- 2026-10-07 Performance-based exams (CKA, CKAD) need a hands-on task item type with verify scripts, not MCQs (rex/istari#8, proposal).
- 2026-10-05 Pack items are identified by `slug`, not `key` (gitleaks reads `"key": "<value>"` as a credential).

## Open blockers

- Human review of the SAA-C03 pack items (Pierce). Items are `source_checked`, not `human_reviewed`.
- Content pipeline and task engine are proposals in Inbox (rex/istari#13, #8); nothing starts until Pierce says go.

## How to resume (for a fresh agent)

1. Read `AGENTS.md` (§9 first) then `TASK_STATE.md` §0 and §5.
2. `rivendell_list(repo="rex/istari", status="Ready")` is the next-task question.
3. Do NOT re-plan what is filed; claim the issue, implement, `Closes #<n>` in the commit.
4. `make test` (pytest + vitest) must be green before and after; `make e2e` when a page or flow changed.

## Do NOT

- Rename item slugs or option ids in `content/packs/**/pack.json` (answers reference them).
- Add a default `DATABASE_URL` or any literal credential, even in tests (detect-secrets, gitleaks).
- Put a JSON field called `key` in content (gitleaks false positive); use `slug` / `id`.
