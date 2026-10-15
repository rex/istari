# TASK_STATE — Istari V1

> Source of truth for in-flight work. Humans and agents both write here.
> This file is **committed** to the repo. It survives sessions, machines,
> and context compactions.
>
> Spec: the implementation briefs `istari-agent-kickstart.md` and `istari-agent-kickstart-labs.md` (Pierce's copies, not committed) · Plan: Rivendell rex/istari#1 (V1, #2–#5) and #8 (verified labs, #42–#47)
> Branch: `main` · Owner (human): @rex · Last update: 2026-10-15 by Claude Fable 5.1

## 0. TL;DR for a fresh agent session

V1 is implemented and Istari has run in Pierce's homelab ring since 2026-10-08 (#40):
GitHub is the source of truth, the lab's Gitea pull mirror builds the image, Flux rolls it
out, the owner account comes from the vault. v0.9.0 to v0.14.0 (2026-10-15) added verified
hands-on labs (#8: #42–#47): a lab brief may carry a `verifier` (backend `k16s`, profile,
question id) and is then set up and graded by the owner's K16S exam server over REST;
attempts are recorded, the first graded attempt is the evidence, the planner schedules a
lab only while the cluster answers, and `content/packs/k8s-cka-k16s` ships the CKA v1.35
track with 36 such labs (question ids only, never K16S text; `docs/labs-k16s.md`). No K16S
instance exists in the ring yet: the build was verified against the stub
(`tests/k16s_stub.py`); the real-instance check (`make labs-check` plus one setup/check
round trip) waits for a VM and its URL from Pierce. Next agent slice: #26 (related-in-Istari
rail, Ready). CKAD needs the CK-X backend (#48, Inbox); #49–#53 are labs follow-ups in
Inbox; the Watch roadmap is #29 with #30–#39 (Inbox). Waiting on Pierce: the K16S VM,
reviewing the AI-authored pack items, and yes/no on #13, #27, #28, #39, #48. Do NOT rename
item slugs or option ids in `content/packs/**/pack.json`, and never commit anything under
`corpus/` or `content/private/`, or any K16S text.

## Standing user directives

<!-- Durable per-task directives from Pierce that must survive compaction. -->

- 2026-10-05: build from the kickstart brief; make reasonable, reversible decisions without stopping for routine clarifications; implement, run and test; report what works, what was tested, what remains.
- 2026-10-05: the GitHub repo is public (rex/istari) and secrets must be actively watched (pre-commit detect-secrets + gitleaks, CI gitleaks, GitHub secret scanning + push protection).
- Brief: do not modify homelab infrastructure, open ports, deploy publicly, run cloud commands, or provision AWS resources. Istari needs no AWS credentials.
- 2026-10-08: "Yes, get it deployed": deploy Istari to the homelab through the lab's prescribed workflows (Arda, the inventory, Flux); this supersedes the brief's no-deploy line for that deployment only. Still no exposure beyond the lab's own ingress and no firewall, UDR or tofu changes. The lab's Gitea repo is a pull mirror of GitHub, never a second remote.

## 1. Phases

| # | Phase | Status | Exit criteria |
|---|---|---|---|
| 1 | Slice 1: foundations, migrations, owner login, validated content, five-question session (#2) | ✅ done | login + onboarding + session persists across reload; pack validates and seeds; pytest + e2e green |
| 2 | Slice 2: durable resume, sourced explanations, lessons, FSRS cards, explainable plan (#3) | ✅ done | Today resumes an open session; feedback shows sources; Review schedules with py-fsrs; plan explains itself |
| 3 | Slice 3: honest progress, content editor/import/export, lab evidence, backup/restore, a11y/responsive, regression coverage (#4) | ✅ done | Progress shows evidence not readiness; import dry-run; restore into isolated db tested; 3 viewports in e2e |
| 4 | Deployment notes (#5) | ✅ done | `docs/deployment.md` without assumed hostnames |
| 5 | Human review of pack content | ⏸ pending | items move from `source_checked` to `human_reviewed` or are edited |
| 6 | Build badge: version, commit, build and start time on every page (#6) | ✅ done | `/api/health` reports the stamp; footer on every page incl. login; stale-bundle warning |
| 7 | Content pipeline and Kubernetes tracks (#7–#20) | ⏸ pending | Pierce approves #13/#8; CKA/CKAD knowledge packs (#9, #11) are Ready now |
| 8 | Private corpus from purchased courses (#21) | ✅ done | `corpus-ingest` / `corpus-udemy` work on the real share; three private packs validate and dry-run import |
| 9 | Course player with synced subtitles (#22: #23 catalog, #24 stream, #25 transcript) | ✅ done | courses listed from `LEARNING_ROOT`, video streams with Range + WebVTT, position remembered, transcript synced |
| 10 | Watch follow-ups: #26 related-in-Istari rail, #27 context cards (proposal), #28 Whisper for subtitle-less courses | ⏸ pending | #26 Ready; #27 and #28 wait on Pierce |
| 11 | Homelab deployment (#40): deployable image, Gitea CI, ring stack, database, vault items, learning share mount | ✅ done | the lab ingress serves the app over TLS; `/api/health` ok; owner bootstrapped from the vault; Watch lists the share |
| 12 | Verified labs on K16S (#8: #42 schema, #43 adapter, #44 attempts, #45 lab page, #46 plan and progress, #47 CKA pack) | ✅ done | set up → check → attempt recorded against the stub on three viewports; plan and progress carry labs; the CKA pack maps 36 ids and `make labs-check` verifies them; real-instance check pending a VM |

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
- No K16S instance in the ring yet. The verified-lab build is tested against the stub only; the first real check is `make labs-check` plus one setup/check round trip on a lab, once a VM exists and Pierce gives its URL (`K16S_BASE_URL` / `K16S_PUBLIC_URL` in the ring stack, private inventory). Docker Desktop was broken on the laptop on 2026-10-15, so that day's gates ran against a Homebrew Postgres on 127.0.0.1:5434 (`TEST_DATABASE_URL`).

## 4. Recent decisions (append-only, newest first)

- 2026-10-15 — K16S text (titles, descriptions, hints, scripts) is never committed: the repo is public and K16S is PolyForm Noncommercial; packs reference question ids only and the lab page fetches the text live with attribution. `make labs-check` verifies the ids against a live instance (Claude Fable 5.1, Pierce's labs brief, #42/#47).
- 2026-10-15 — A verified lab is evidence on its first graded attempt only; later passes are repeats, as with questions. The planner schedules one lab, weakest objective first, only while the cluster's 60 s status snapshot says it answers and the session is 15 minutes or longer; health and the planner never call the cluster inline (Claude Fable 5.1, #46).
- 2026-10-15 — A transport failure, a timeout or a non-2xx from K16S is `upstream_error` (502) and records nothing; an `unavailable` answer (the task needs the full install) is a reason, not an error, and records nothing either; retries are the owner's click, never automatic (Claude Fable 5.1, #43/#44).
- 2026-10-08 — GitHub-first deployment: the lab's Gitea repo is a pull mirror of GitHub (Pierce: a second remote drifts and doubles every push); Gitea Actions builds on mirror sync, `.gitea/workflows/ci.yml` derives the registry from the server URL so the public repo names no hosts (Claude Fable 5.1, #40).
- 2026-10-08 — The container entrypoint owns start-up: migrate, seed the shipped packs, create the owner once from `ISTARI_OWNER_USERNAME`/`ISTARI_OWNER_PASSWORD` (`bootstrap-owner --if-missing`, never touching an existing owner), then serve (Claude Fable 5.1, #40).
- 2026-10-08 — `.gitignore` rules for generated directories are anchored to the repo root; the unanchored `corpus/` had hidden `backend/app/corpus/` from git and the linters since v0.4.0 (Claude Fable 5.1, found by the first CI run).
- 2026-10-07 — Purchased course material is read in place and converted into a gitignored corpus and private packs; it is a coverage map and drill source, never a fact source, and nothing derived from it is committed to the public repo (Claude Fable 5.1, #21).
- 2026-10-07 — Imported drill questions live under an `<EXAM>-DRILL` exam version with quiz/test names as domains, so they never mix with a verified pack's objectives (Claude Fable 5.1, #21).
- 2026-10-07 — Build stamp comes from the API (`GIT_COMMIT`/`BUILD_DATE` env, git fallback in a checkout); the SPA embeds its own commit only to detect a stale bundle (Claude Fable 5.1, #6).
- 2026-10-07 — Settings singleton is created inside a savepoint; concurrent first requests read the winner's row (Claude Fable 5.1, e2e-found race).
- 2026-10-07 — CKA/CKAD are performance-based: packs split into knowledge items the engine carries now and hands-on tasks that need a verifier-backed task type (Claude Fable 5.1, proposal in #8).
- 2026-10-05 — Option ids are descriptive slugs up to 32 chars (schema widened from 16); never letters (Claude Fable 5.1, pack authoring).
- 2026-10-05 — `DATABASE_URL` has no default; `TEST_DATABASE_URL` derives from it. The e2e DSN comes from backend settings via `make e2e` (Claude Fable 5.1, detect-secrets gate).
- 2026-10-05 — Alembic revision ids are descriptive (`0001`), generated with `--rev-id`; `make db-revision REV_ID=` supports it (Claude Fable 5.1, detect-secrets gate).
- 2026-10-05 — Modules over the 8-public-def cap were split by resource: `contracts/session_requests.py`, `domain/planning_types.py`, `services/progress_activity.py`, `queries/{lessons,review,labs,progress,track}.ts` (Claude Fable 5.1, module-shape gate).
- 2026-10-05 — Stack per the brief's defaults: FastAPI + SQLAlchemy async + Alembic + py-fsrs; React 19 + Vite 8 + TanStack; Postgres 18 (Claude Fable 5.1, greenfield).

## 5. Next actions (ordered)

1. Pierce: stand up a K16S VM for the ring (the install is K16S's own; Istari never provisions it), set `K16S_BASE_URL` and `K16S_PUBLIC_URL` in `stacks/istari.yml` (private inventory), and give the agent the URL.
2. Agent, once the URL exists: `make labs-check BASE_URL=<url>`, then one setup → terminal → check round trip on a `cka` lab from the deployed app; fix whatever the real server does differently from the stub.
3. Pierce: open the deployed app, switch the track to CKA-1.35 in Settings and look at Labs and a lab page; the design iterates from there. Review pack items on the Content page.
4. Agent (Ready now): #26, the related-in-Istari rail beside the player.
5. Pierce: decide on CK-X for CKAD (#48), the labs follow-ups (#49–#53), the content pipeline (#13 with #14–#19), the per-lecture context cards (#27), Whisper (#28), and the CKA knowledge pack (#9, Ready; lessons, questions and cards for the track the labs now cover).
6. Agent (Inbox): the Playwright e2e suite in Gitea CI (#41).
7. Local dev: `LEARNING_ROOT=/Volumes/MinasTirith-Data/MinasTirith-Learning` in `.env` for Watch, `make bootstrap-owner USERNAME=<you>` for a local owner, `K16S_BASE_URL=http://127.0.0.1:8081` with the stub (`docs/labs-k16s.md`) for the lab pages.

## 6. Handoff note (fill when ending a session)

2026-10-15, 01:20 CDT (Claude Fable 5.1): verified hands-on labs on K16S shipped as
v0.9.0–v0.14.0 (#8: #42 verifier schema, #43 K16S adapter, health field and stub, #44
attempts table and setup/check routes, #45 lab page and Labs list, #46 plan and progress,
#47 CKA pack and `labs check-map`). Pierce's labs brief (`istari-agent-kickstart-labs.md`,
untracked on purpose) was the spec; the one thing it defers is the ring's K16S URL, to be
asked for once a VM exists. No K16S ran during the build (none exists yet; Docker Desktop
was broken on the laptop as well), so everything was verified against `tests/k16s_stub.py`:
pytest 144 passed, vitest 37 passed, Playwright 12 passed (desktop, mobile, ultrawide; the
stub runs as a second Playwright web server), ruff/mypy/import-linter/tsc/eslint/prettier
clean, `make validate` clean, `make check-skeleton` current for every verbatim file with
only the advisory Makefile drift this repo always carries (its own targets). The dev app was
checked by eye with the CKA track active: the Labs list groups the 36 labs by domain and
orders them by objective; a CKA lab page against the stub shows "Task not found on the
instance" with setup disabled, the right state for a mismatched instance. Open: the
real-instance check (§5, items 1 and 2). #10 and #12 carry comments explaining that #47
covers CKA through K16S by a different route than they describe; Pierce re-scopes or closes
them. Rivendell: #8 and #42–#47 closed by their commits; #48–#53 in Inbox. The Homebrew
test Postgres on 127.0.0.1:5434 may still be running
(`/opt/homebrew/opt/postgresql@18/bin/pg_ctl -D ~/.local/share/istari-test-pg stop`); the
dev database there has the SAA, CKA and fixture packs and a local owner.

2026-10-08, 04:10 (Claude Fable 5.1): Istari is deployed in the homelab ring (#40). The
chain: GitHub `main` → the lab's Gitea pull mirror (10-minute interval, or
`arda_gitea_mirror_sync repo=rex/istari` to sync now) → Gitea Actions
(`.gitea/workflows/ci.yml`: the gates against a Postgres service container, then the
image) → Flux image automation → rollout. The first CI runs found two real bugs, fixed as
v0.7.0 (the corpus package had been gitignored since v0.4.0) and v0.8.0 (`node:26-slim`
has no corepack). Verified at 04:05 CDT: pod 1/1 ready; `/api/health` over the lab ingress
reports 0.8.0 / 9e20933; the entrypoint imported the SAA-C03 pack (74 items) and created
the owner; login with the vault credentials returns 200; the Watch catalog scanned 90
courses from the read-only share mount in about 40 seconds; DNS answers on both Pi-holes.
Lab side (private repos): inventory `stacks/istari.yml` (0.23.0), isengard 0.184.0,
homelab-ansible 0.344.0 (the Learning export now also allows the ring node), palantir
0.33.2; CNPG role and database `istari`; vault items `db-postgres-istari` and
`app-istari`. homelab-ansible#71 (the DNS playbook's check mode died on apps with nothing
pending) was fixed the same morning (homelab-ansible 0.345.0) and `make deploy-dns`
converged with nothing to add: the istari host record was already on both Pi-holes through
external-dns. #41 (e2e in CI) is in Inbox. Nothing runs in the background.

2026-10-08, 02:15 (Claude Fable 5.1): session closing. v0.5.0 is on `main` (f3b0ae5).
The whole-dataset corpus ingest finished with no conversion failures: 204 resources,
12,167 Markdown files, ~31M words under `corpus/` (Cloud/AWS 25.2M words, Kubernetes/
General 5.0M, Terraform 683k; CKA/CKAD/CKS nearly empty for lack of subtitles). Watch was
smoke-tested against the real share (streaming, captions, transcript, progress saves).
Roadmap filed as #29 with #30–#39 in Inbox. Nothing is running in the background; the
dev database is migrated to `0002_course_progress`; `.env` does not yet set
`LEARNING_ROOT`, so Watch shows "not configured" until Pierce adds it.

2026-10-07, late (Claude Fable 5.1): v0.5.0, Watch (#23, #24, #25). Backend: catalog
scan in a thread, Range streaming via FileResponse, SRT→WebVTT, `course_progress` with
migration `0002_course_progress`, path safety by catalogue membership. Frontend: Watch,
course and player pages, transcript panel, shortcuts. Gates: pytest 98 passed, vitest 25
passed, Playwright 9 passed, ruff/mypy/import-linter/tsc/eslint/prettier clean. Test
timings were inflated by a machine load average near 85 from other processes, not by the
suite.

2026-10-07, later (Claude Fable 5.1): v0.4.0, private corpus tooling (#21). Real-share
results: Digital Cloud SAA-C03 course → 312 files / 236k words in 18 s; DVA-C01 practice
tests → 368 of 389 questions; SysOps 2021 quizzes → 185 of 198; CLF 2021 quizzes → 172
of 187; all three private packs validate and import in dry run. A whole-dataset ingest
(`Cloud/*`, `Kubernetes/*`) was started in the background into `corpus/`. Gates: pytest
89 passed, ruff/mypy/import-linter clean, `make validate` clean. The course player epic
(#22, #23–#28) is filed Ready and is the next slice.

2026-10-07 (Claude Fable 5.1): v0.3.0. Build badge on every page (`/api/health` carries
version, commit, built_at, started_at; Docker build args and OCI labels wired). Fixed the
first-run settings race that the e2e run exposed, and a timing race in the keyboard e2e
test. Skeleton synced to 0.50.0. Gates at handoff: pytest 80 passed, vitest 19 passed,
Playwright 9 passed (desktop, mobile, ultrawide), ruff/mypy/import-linter/tsc/eslint/
prettier clean, `make validate` clean (Makefile drift is advisory), pre-commit clean.
Content strategy answered in chat and filed: rex/istari#7–#12 (Kubernetes tracks, two
Ready), #13–#19 (content pipeline, Inbox), #20 (next MCQ tracks, Inbox).

2026-10-05 (Claude Fable 5.1): V1 built end to end in one session. Gates at handoff:
pytest 75 passed (includes backup→restore into `istari_restore_test` and the real-pack
import), vitest 16 passed, Playwright study-loop spec on desktop/mobile/ultrawide (see
CHANGELOG 0.2.0 for the run result), ruff/mypy/import-linter/tsc/eslint/prettier clean,
pre-commit (detect-secrets, gitleaks, architecture, module shape, version) clean. Dev
database is migrated and seeded; no owner account was created (Pierce picks the password).
