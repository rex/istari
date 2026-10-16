# PROGRESS

<!-- ≤50 lines. Read this first when a fresh agent session starts.
     Points to TASK_STATE.md for the details. -->

- **Project**: Istari (FastAPI + SQLAlchemy async backend, React 19 + Vite SPA, Postgres 18)
- **Active branch**: `main`
- **Active feature spec**: none; the plan lives in Rivendell (rex/istari issues)
- **Active TASK_STATE**: `TASK_STATE.md` (phases 12 verified labs, 13 design system, and all of #61 done: lecture index #62, courses compared #63, master path #64, outcomes #65, queue #66, tuning #67; K16S is live and the graded round trip waits for Pierce; the transcription run is on the share; the quality-first program is #70 (#71 done; #72–#76 wait on Pierce's three decisions); #26 is the next Ready agent slice; phases 5 and 7 wait on Pierce)
- **Last session**: 2026-10-16 (Claude Fable 5.1, v0.20.0–v0.30.0: the lecture-to-objective index and review queue, courses compared, the master path per objective, rex/istari#61 with #62, #63 and #64; the transcription command, #28, with the SAA run started on the share; the ranking tuned and measured, #67; the review queue made finishable, #66; watch outcomes on Progress and the comparison, #65; dated courses step aside, #68; the SAA-C03 exam guide verbatim in the pack with its scope appendix, #71; Pierce's quality-first program filed as #70 with #72–#76. All of #61's slices are shipped). Before: 2026-10-15, v0.9.0–v0.14.0 verified labs (#8 with #42–#47) and v0.15.0–v0.19.0 the design system (#55 with #56–#60)

## Last three decisions

- 2026-10-16 Quality first (#70): assessed quality and currency decide what enters a master course, never relevance or coverage alone; the pack carries the official exam guide verbatim and the checklist is built from official sources first; an LLM reads every lecture; every master-course lesson gets a verified lab. A course dated before the exam version's `current_since` is an older version.
- 2026-10-16 Lectures map to objectives by their captions: BM25 against per-objective queries plus title rules for the track's own exam; the owner's pins and exclusions outrank the ranking and survive rebuilds; transcripts are never stored, only term counts. Courses compare on coverage, currency and captions, never a score; a learning path per objective is a proposal composed across courses, never a merged video, and the owner's edits win.
- 2026-10-15 The UI identity is the Istari design system on claude.ai/design: it owns tokens and rules (`styles/tokens.css`, `styles/bundle.css` are its files), the code owns markup; course cards show coverage in words, never a readiness score.
- 2026-10-15 Verified labs: K16S sets up and grades them over REST; no K16S text in the repo (question ids only, text fetched live); the first graded attempt is the evidence; the planner schedules a lab only while the cluster answers.
- 2026-10-08 GitHub-first: the lab's Gitea repo is a pull mirror; CI builds on mirror sync; the container entrypoint migrates, seeds and bootstraps the owner once.
- 2026-10-07 Watch reads the learning share in place (`LEARNING_ROOT`), serves only paths the catalog reported, and never writes to the share.
- 2026-10-07 Purchased course material becomes a gitignored corpus and private drill packs; it is never a fact source and never committed.
- 2026-10-07 Build stamp: the API is the source of truth (`/api/health`); the bundle embeds its own commit and warns when it differs.
## Open blockers

- One graded setup/check round trip on a `cka` lab from the deployed app waits for Pierce's word (K16S is live; `make labs-check` passes).
- Human review of the SAA-C03 and CKA pack items (Pierce). Items are `source_checked`, not `human_reviewed`.
- The content pipeline (#13), context cards (#27) and CK-X for CKAD (#48) are proposals in Inbox; nothing starts until Pierce says go.
- The five Solutions Architect courses are transcribed on the share (937 lectures, 2026-10-16) and the rest of `Cloud/AWS` is running; the deployed app needs a "Rebuild index" click, and the Kubernetes folders (#36) wait for Pierce's go.
- The #70 decisions wait for Pierce: the assessment model and budget cap, consent to send purchased-course transcripts to the Anthropic API, and the AWS lab substrate. #72–#76 stay in Inbox until then.

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
