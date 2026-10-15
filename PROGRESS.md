# PROGRESS

<!-- ≤50 lines. Read this first when a fresh agent session starts.
     Points to TASK_STATE.md for the details. -->

- **Project**: Istari (FastAPI + SQLAlchemy async backend, React 19 + Vite SPA, Postgres 18)
- **Active branch**: `main`
- **Active feature spec**: none; the plan lives in Rivendell (rex/istari issues)
- **Active TASK_STATE**: `TASK_STATE.md` (phases 12 verified labs and 13 design system done; a K16S VM is Pierce's next step; #26 is the next agent slice; phases 5 and 7 wait on Pierce)
- **Last session**: 2026-10-15 (Claude Fable 5.1, v0.9.0–v0.14.0 verified hands-on labs graded by K16S and the CKA v1.35 pack, rex/istari#8 with #42–#47; then v0.15.0–v0.19.0 adopting the Istari design system from claude.ai/design, rex/istari#55 with #56–#60)

## Last three decisions

- 2026-10-15 The UI identity is the Istari design system on claude.ai/design: it owns tokens and rules (`styles/tokens.css`, `styles/bundle.css` are its files), the code owns markup; course cards show coverage in words, never a readiness score.
- 2026-10-15 Verified labs: K16S sets up and grades them over REST; no K16S text in the repo (question ids only, text fetched live); the first graded attempt is the evidence; the planner schedules a lab only while the cluster answers.
- 2026-10-08 GitHub-first: the lab's Gitea repo is a pull mirror; CI builds on mirror sync; the container entrypoint migrates, seeds and bootstraps the owner once.
- 2026-10-07 Watch reads the learning share in place (`LEARNING_ROOT`), serves only paths the catalog reported, and never writes to the share.
- 2026-10-07 Purchased course material becomes a gitignored corpus and private drill packs; it is never a fact source and never committed.
- 2026-10-07 Build stamp: the API is the source of truth (`/api/health`); the bundle embeds its own commit and warns when it differs.
## Open blockers

- No K16S instance in the ring yet (Pierce); the verified-lab build is tested against the stub only.
- Human review of the SAA-C03 and CKA pack items (Pierce). Items are `source_checked`, not `human_reviewed`.
- The content pipeline (#13), context cards (#27) and CK-X for CKAD (#48) are proposals in Inbox; nothing starts until Pierce says go.
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
- Commit any K16S text (titles, descriptions, hints, scripts); packs reference question ids only.
