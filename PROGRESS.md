# PROGRESS

<!-- ≤50 lines. Read this first when a fresh agent session starts.
     Points to TASK_STATE.md for the details. -->

- **Project**: Istari (FastAPI + SQLAlchemy async backend, React 19 + Vite SPA, Postgres 18)
- **Active branch**: `main`
- **Active feature spec**: none; the plan lives in Rivendell (rex/istari issues)
- **Active TASK_STATE**: `TASK_STATE.md` (phase 10: Watch follow-ups; #26 is next; phases 5 and 7 wait on Pierce)
- **Last session**: 2026-10-07 (Claude Fable 5.1, v0.4.0 private corpus tooling and v0.5.0 Watch: video courses from the learning share with synced subtitles)

## Last three decisions

- 2026-10-07 Watch reads the learning share in place (`LEARNING_ROOT`), serves only paths the catalog reported, and never writes to the share.
- 2026-10-07 Purchased course material becomes a gitignored corpus and private drill packs; it is never a fact source and never committed.
- 2026-10-07 Build stamp: the API is the source of truth (`/api/health`); the bundle embeds its own commit and warns when it differs.
- 2026-10-07 Performance-based exams (CKA, CKAD) need a hands-on task item type with verify scripts, not MCQs (rex/istari#8, proposal).

## Open blockers

- Human review of the SAA-C03 pack items (Pierce). Items are `source_checked`, not `human_reviewed`.
- Content pipeline, task engine and context cards are proposals in Inbox (rex/istari#13, #8, #27); nothing starts until Pierce says go.
- Whisper transcription (#28) needs a check-in on model size and output location before it runs.

## How to resume (for a fresh agent)

1. Read `AGENTS.md` (§9 first) then `TASK_STATE.md` §0 and §5.
2. `rivendell_list(repo="rex/istari", status="Ready")` is the next-task question.
3. Do NOT re-plan what is filed; claim the issue, implement, `Closes #<n>` in the commit.
4. `make test` (pytest + vitest) must be green before and after; `make e2e` when a page or flow changed.

## Do NOT

- Rename item slugs or option ids in `content/packs/**/pack.json` (answers reference them).
- Add a default `DATABASE_URL` or any literal credential, even in tests (detect-secrets, gitleaks).
- Put a JSON field called `key` in content (gitleaks false positive); use `slug` / `id`.
