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
track with 36 such labs (question ids only, never K16S text; `docs/labs-k16s.md`). K16S
runs in the ring since 2026-10-16 (its URL lives in the private inventory; the deployed
app points at it) and `make labs-check` maps all 36 labs against it; the one setup/check
round trip from the deployed app waits for Pierce's word, since it records a graded
attempt. v0.15.0 to v0.19.0 (2026-10-15) adopted
the Istari design system Pierce built in Claude Design (#55: #56–#60): the system's tokens,
stylesheet and fonts replace the v0 styles, markup is aligned, a course picker with per-track
counts and progress replaces the onboarding radio list and sits behind a chip on Settings,
and phones get the bottom tab bar with a More sheet. The system is the source for tokens
and rules, the code for markup (`docs/architecture.md`, Styles). v0.20.0 to v0.21.0
(2026-10-16) added the lecture-to-objective index and its review page (#61: #62): the
share's captions ranked against the track's objectives, title rules for the track's own
exam, a one-lecture-at-a-time review queue whose pins and exclusions survive rebuilds, and
objective badges on the player; on the real share it indexes 59 AWS courses and 4,597
captioned lectures for SAA-C03. v0.22.0 (2026-10-16) added courses compared (#63) at
`/watch/compare`: one row per course with objectives touched, currency (the certification's
name in a title counts), captions, minutes mapped per domain and lectures watched; never a
quality score. v0.23.0 (2026-10-16) added the master path (#64): one learning path per
objective at `/learn/path/<code>`, composed across courses continuity first (the deepest
course's run in course order, the other courses' strongest lectures behind it, older-exam
courses stepping aside, capped at two hours), kept as a proposal the owner reorders,
excludes or restores; the player follows it (`?path=`), and a 30-minute plan takes one
lecture from the weakest objective's path. That closes the first pass of #61; #65
(outcomes), #66 (queue ordering, course-level decisions) and #67 (ranking tuning, which is
what will separate courses whose objectives column saturates at 14/14) are follow-ups in
Inbox. Next agent slice otherwise: #26 (related-in-Istari rail, Ready). CKAD needs the CK-X backend (#48, Inbox); #49–#53 are labs follow-ups in Inbox; the
Watch roadmap is #29 with #30–#39 (Inbox). v0.24.0 (2026-10-16) added `make transcribe`
(#28): generated captions for lectures that have none, written next to the video on the
share with a manifest (Pierce's decision), backends parakeet-mlx, whisper.cpp and
openai-whisper; Pierce picked Parakeet and the SAA run onto the share started 2026-10-16
(the five uncaptioned Solutions Architect courses, in order). v0.25.0 (2026-10-16) tuned
the ranking (#67) on a hand-labelled 57-lecture sample kept in `corpus/eval/`: generic terms
out, scores divided by query mass, housekeeping lectures unmapped; top-1 67% to 69%, any of
top-3 91% to 93%, course intros left unmapped 0% to 33%; `make lectures-eval` is the harness.
v0.26.0 (2026-10-16) made the review queue finishable (#66): courses for the track's own
exam first, the lecture's place among the pending courses on the card, and accept or
exclude a whole section or course at once (`s`, `c`; excluding asks twice). v0.27.0
(2026-10-16) added watch outcomes (#65): per objective, the mapped lectures watched to the
end and first-attempt accuracy before and after the first of them, on the objective's
Progress row; per course, first attempts after watching its lectures as the comparison's
"After watching" column (a rate from three attempts on). That completes #61's plan.
The SAA transcription run finished at 10:16 (937 lectures, 0 failures, 2 h 41 min); the dev
index rebuilt to 5,534 captioned lectures and 14,687 mappings, and v0.28.0 fixed what that
showed (a Professional course of the same family is another exam; an own-exam course with
two hours of its own leads a path). The deployed app needs one "Rebuild index" click on
Content → Lecture mapping (no owner credentials here). Waiting on Pierce: that click, the lab
round trip, the rest of the transcription order (remaining `Cloud/AWS`, then Kubernetes,
#36), reviewing the AI-authored pack items, and yes/no on #13, #27, #39, #48. Do NOT rename
item slugs or option ids in `content/packs/**/pack.json`, and never commit anything under
`corpus/` or `content/private/`, or any K16S text.
v0.29.0 (2026-10-16, evening) gave the pack `exam_version.current_since` (SAA-C03
2022-08-30, the revised CKA curriculum 2025-02-18) and reads a dated course's year against
it, so the 2018 Solutions Architect Associate course is an older version and steps aside
(#68). v0.30.0 put the SAA-C03 exam guide into the pack verbatim (107 knowledge and 82
skills statements; the 130 in-scope and 61 out-of-scope services as `exam_version.scope`,
migration 0007; #71): the labelled sample's top-1 went from 69% to 64% because the guide
repeats its boilerplate across sibling objectives and no existing lever recovers it; the
fix belongs to the ranking, not the pack. Pierce's quality-first program is filed as #70
with #71–#76 (checklist #72, LLM lecture assessment #73, master course #74, gap lessons
#75, a verified lab for every lesson #76; #68 and #69 moved under it); the compute spend
waits on his three decisions (assessment model and budget, consent to send the purchased
transcripts to the API, the AWS lab substrate).
2026-10-17, 07:03: Pierce paused #70 to regroup ("I'm letting my perfectionist tendencies
derail my own progress"). The direction now: every lecture and lesson lets him **see** the
thing and **do** the thing inside the viewer: figures per lesson and per lecture first,
do-steps (labs, executables) in the viewer as the stretch. The grading effort's outcome,
measurements and decisions are captured on #70 and #73 (consent to send transcripts to the
API; hybrid AWS labs with a $0.50 cap; local models measured on the laptop: Qwen3.6-35B-A3B
graded a real S3 lecture correctly in 19 s, gpt-oss-20b in schema mode did not; assess the
machine and tell Pierce before loading a model). #72–#77 stay in Inbox. Pierce answered the
three decisions the same morning (figures drawn with mingrammer/diagrams and committed as
SVG; the 8 SAA lessons first, then the player rail; LocalEmu in the ring with a verifier
backend after the figures) and approved the concept, so the plan is #78 with #79–#85, Ready.
v0.32.0 shipped #79: figures as a fifth item kind (`schemas/figures.py` with the SVG
sanitizer, `domain/content/load.py` reading the drawing from the file beside the pack,
import, export and admin paths, `/api/figures/{key}.svg`, the lesson view's `figures`, the
viewer's `<Figure>` placed by `![alt](figure:slug)`, the design system's Figure component at
version 13) and the first figure, the two-tier VPC, in "Securing the network and the data".
Portability rule (Pierce's ask): a figure attaches to objectives only; lessons reference it
by slug; lectures borrow it through their objective mapping; a per-course variant later is
another mapping, never another drawing format. v0.33.0 shipped #80: `make figures` draws
every pack's figure scripts (stable node ids, generator comments dropped, the pack
validated after), `make figures-check` catches drift, the `figures` dependency group holds
mingrammer/diagrams, `docs/figures.md` has the conventions. Next in order: #81 the 8 SAA
figures, #82 the player rail, #83 "Do it" in the lesson, then #84 and #85 (LocalEmu).

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
| 13 | Adopt the Istari design system (#55: #56 foundation, #57 markup, #58 course picker, #59 phone shell, #60 docs and re-sync) | ✅ done | every page renders in the system's tokens and stylesheet; picker and chip switch tracks; the phone tab bar and More sheet pass the mobile e2e; the system's README and PlanList preview match the code |

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

- 2026-10-15 — The UI identity lives in the Istari design system on claude.ai/design (Pierce's, built from this repo's marks and inventory); `styles/tokens.css` and `styles/bundle.css` are its files, Prettier-formatted. The system owns tokens and rules, the code owns markup; the v0 partials and tokens are gone, and the fonts ship as OFL subsets with their licences (Claude Fable 5.1, #55–#60).
- 2026-10-15 — Track progress on a course card is coverage in words (lessons read, question families seen, labs verified on the first graded attempt; accuracy only past the evidence threshold) and a capped fraction for the meter; never a readiness score. Switching tracks is `PATCH /api/settings {active_exam_version_id}` and keeps everything done on the other track (Claude Fable 5.1, #58).
- 2026-10-15 — Phones: five tabs (Today, Learn, Practice, Review, Watch); Progress, Labs and Settings behind More; Labs stays mostly a desktop screen because the terminal wants one (Claude Fable 5.1, #59, per the system's AppBar guidelines).
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

1. Pierce: say the word for one setup → terminal → check round trip on a `cka` lab from the deployed app (K16S is up and `make labs-check` passes; the round trip records a graded attempt, so the agent waits).
2. Pierce: click "Rebuild index" on the deployed app's Content → Lecture mapping (the SAA transcripts are on the share); then say go for the rest of `Cloud/AWS` and the Kubernetes folders (#36): `make transcribe SRC=<topic dir> ALL=1 SHARE=1 ASR=parakeet`, roughly 1,400 and 1,500 lectures.
3. Agent (Ready, in order): #81 one or two figures for each of the 8 SAA lessons (`make figures` draws them, `docs/figures.md`); #82 the player's "See it" rail; #83 "Do it" inside the lesson; then #84 LocalEmu in the ring and #85 its verifier backend. Pierce: open "Securing the network and the data" and say whether the VPC figure is the thing; review `fig-vpc-two-tier` on the Content page. #70's sub-issues (#72–#77) stay parked in Inbox; the decisions already taken there (API consent, hybrid AWS labs with a $0.50 cap, the local-model protocol) stand.
3. Pierce: review a few courses on `/content/lectures` and a few paths on `/learn/path/<code>`; once a few hundred pins and exclusions exist, grow `corpus/eval/saa-c03.json` from them and re-run `make lectures-eval` (the sample so far is the agent's judgment on 57 lectures).
3. Pierce: open the deployed app in the new identity, open the track chip on Settings, look at Labs and a lab page, and the phone layout; the design iterates from the system (tokens and rules there, markup here). Review pack items on the Content page.
4. Agent (Ready now): #26, the related-in-Istari rail beside the player.
5. Pierce: decide on CK-X for CKAD (#48), the labs follow-ups (#49–#53), the content pipeline (#13 with #14–#19), the per-lecture context cards (#27), Whisper (#28), and the CKA knowledge pack (#9, Ready; lessons, questions and cards for the track the labs now cover).
6. Agent (Inbox): the Playwright e2e suite in Gitea CI (#41).
7. Local dev: `LEARNING_ROOT=/Volumes/MinasTirith-Data/MinasTirith-Learning` in `.env` for Watch, `make bootstrap-owner USERNAME=<you>` for a local owner, `K16S_BASE_URL=http://127.0.0.1:8081` with the stub (`docs/labs-k16s.md`) for the lab pages.

## 6. Handoff note (fill when ending a session)

2026-10-17, morning (Claude Fable 5.1): Pierce approved the "see it, then do it" concept
("literally dead on accurate") with one design rule: figures and do-steps must be portable
across the courses that share a topic, and minor per-course differences must be
accommodatable later without tight coupling. #79 shipped as v0.32.0 along those lines: a
figure is its own item mapped to objectives, a lesson references it by slug (`figures[]`
plus `![alt](figure:slug)` in the body), and nothing in a figure knows which course or
lecture shows it. The drawing lives beside the pack (`figures/<slug>.svg`, rendered from
`figures/<slug>.py` with mingrammer/diagrams; the script inlines the icon PNGs so the SVG
is self-contained), the loader reads it into the spec, the sanitizer refuses scripts,
handlers, embedded documents and external references, and the content hash excludes the
file path so an export re-imports unchanged. The viewer replaces the paragraph that holds
a placed figure with a captioned `<figure>` (the figure item's own `alt` is the accessible
name, not the Markdown alt); an image URL the renderer drops now shows its alt text. The
design system got the Figure component and the `.figure` rules (artifact version 13;
`bundle.css` copied back and Prettier-formatted). Gates: ruff/mypy/import-linter/tsc/
eslint/prettier clean, pytest 205, vitest 51, Playwright on desktop, mobile and ultrawide
including the new `lesson-figure.spec.ts`, `make validate` clean. The one-figure pass took
the morning; #80 makes the render step a command and #81 draws the other seven lessons.

2026-10-17, early morning (Claude Fable 5.1): the Cloud/AWS transcription finished at
19:13 on 2026-10-16 (1,401 lectures, 30 courses, 0 failures; every course under
`Cloud/AWS` is captioned, 71 courses, 6,935 lectures). Pierce's answers to the program's
decisions turned on cost: money is tight, time and local compute are not. Facts gathered
for him (all on #70 and #73): Batches API terms and the October 2026 prices; the corpus is
5,533 captioned lectures and 2.26 million words; a full grading pass is about $3 on Haiku
5.5 batch, $25 to $55 on Sonnet 5.5, $0 locally; LocalStack archived its open-source
edition and needs an account (Hobby free for non-commercial), LocalEmu is the Apache-2.0
fork (132 services, young); 13 SAA services have no LocalStack page at all. On the laptop
(M4 Pro, 48 GB) one real lecture was graded: gpt-oss-20b (12 GB) loads in 15 s and answers
in 7 to 11 s but, in LM Studio's json_schema mode, reasons 0 tokens and wrongly says skip;
Qwen3.6-35B-A3B (20 GB) with thinking off answers in 19 s and gets it right (3.1 and 4.1 at
depth 3, evidence quoted, quality 5, include), with the JSON in `reasoning_content`. Pierce
had feared the model would crash the machine; it did not (memory 45% free before, 71%
after). His rule from here: assess the machine's state before any load, tell him before
loading, no per-request authorization while a model stays loaded. Then he paused the
program to regroup toward seeing and doing in the viewer (§0). Nothing new is claimed.

2026-10-16, evening (Claude Fable 5.1): Pierce's direction after the transcription run:
quality is the core grading factor, the 2018 course must rank lower or be ignored, master
courses must cover everything on the current exams, and every lesson gets a verified lab.
Done: v0.29.0 (#68) `current_since` on the exam version and the year rule in
`services/course_currency.py` (`tests/unit/test_course_currency.py`); v0.30.0 (#71) the
exam guide in the pack verbatim and `exam_version.scope` (`schemas/scope.py`, three JSONB
columns with a server default, migration 0007). The guide text came from the official
SAA-C03 exam guide PDF (version 1.1) through `pdftotext` and a parser kept in the session
scratchpad; `test_real_pack.py` pins the counts. The AWS certification page on 2026-10-16
links SAA-C03 resources only, so there is no C04 to build against. Measured on the
57-lecture sample after `make seed` against the index database (5434): top-1 69% to 64%
(31 to 29 of 45), any-of-top-3 93% to 91%; GENERIC 0.3 and 0.5, MASS 0.5 and 1.5, BODY 2,
STEM 2 and their pairs reach 67% at best (MASS 0.5 with BODY 2), so the defaults stayed and
the follow-up (strip the guide's boilerplate from the objective queries, then re-measure)
is filed under #70. Both local databases are migrated to 0007 and seeded. The program is
#70 with #71–#76, in Inbox until Pierce answers the three decisions asked at the end of
the turn. Gates for both commits: ruff/mypy/import-linter/tsc/eslint/prettier clean, pytest
191, vitest 48, `make validate` clean; no page changed, so no Playwright run. The Cloud/AWS
transcription run started at 14:28 and was still going at the end of the turn.

2026-10-16, early morning (Claude Fable 5.1): the lecture-to-objective index shipped as
v0.20.0 (`domain/lecture_text.py`, `lecture_index.py`, `lecture_rules.py`, the service,
four tables in migration 0004, `/api/lecture-index`) and v0.21.0 (the review page at
`/content/lectures`, `LectureObjectives` badges on the player, the Playwright fixture
course); #61 is the parent, #62 closes with v0.21.0. The first run on the real share (dev
API with `LEARNING_TOPICS=Cloud/AWS`) took about five minutes from the laptop over SMB: 59
candidate courses (the track's subject is `aws`, so every course under `Cloud/AWS`), 6,935
lectures, 4,597 with captions, roughly 12,000 mappings. It found three defects, fixed
before the commit: the runner rescans the catalog first (the e2e API had never scanned, so
Rebuild found nothing); title rules fire only for a course of the track's own exam
(`own_exam`: the Cloud Practitioner course's "(OBJ 4.3)" file names put 138 wrong `rule`
rows on SAA-C03); the status counts candidates by subject before the first run. Lexical
precision on a random sample of twelve reads as about half right, with generic words
(`five`, `another`, `work`) reaching the queries through lesson bodies and question stems;
#67 lists the levers in order. The queue is one lecture at a time in course order, which
does not finish at 4,600 lectures; #66 proposes exam-matched courses first and
course-level decisions. Book chapters are not indexed (captions only). Gates:
ruff/mypy/import-linter/tsc/eslint/prettier clean, pytest 157, vitest 40, Playwright 16 on
desktop, mobile and ultrawide, `make validate` clean. K16S went live in the ring during the
session (another agent's work): `make labs-check` maps all 36 CKA labs; the graded round
trip waits for Pierce.

Later the same morning: #63 shipped as v0.22.0, courses compared at `/watch/compare`
(`services/course_comparison.py`, `GET /api/lecture-index/courses`,
`pages/CourseComparisonPage.tsx`; the design system gained sortable headers and
`table--courses`, artifact version 11). On the real share every captioned AWS course touches
all 14 SAA-C03 objectives, so the objectives column saturates and the minutes per domain
carry the comparison; #67's tuning is what will separate them. Currency reads the
certification's name out of a title (`names_certification`), which turns "no exam named"
into "same exam, no version named" for most Solutions Architect courses. 25 of the 59 AWS
courses have no captions at all (2,338 lectures, among them the SA Professional,
ZeroToMastery and A Cloud Guru 2020 SAA courses); #28 and #36 (Whisper into the corpus) are
the way to measure those and wait on Pierce's model-size and output-location decision.
Gates: pytest 160, vitest 44, Playwright 19 on three viewports.

Then #64 as v0.23.0: `domain/learning_path.py` (pure composition: anchor course by depth,
course-order run, fill by source rank and score skipping titles already covered, older-exam
courses stepping aside at half coverage, two-hour cap, pins first, exclusions out),
`services/learning_path.py` and `objective_path_entries` (migration 0005; `proposed` rows
rewritten by every index run and decision, `pinned`/`excluded` kept), `/api/paths`, the
path page, the player's path mode, the Progress and Learn links, and the planner's
"lecture" block at 30 minutes (`LectureCandidate`, `PlanBlock.course_slug/lecture_path`).
Course currency moved to `services/course_currency.py` to break the import cycle the index
would otherwise have with the comparison. The paths are only as good as the mappings:
with the objectives column saturated, the anchor is simply the longest course on each
objective, so #67 is the lever that makes the paths opinionated. Gates: pytest 167, vitest
47, Playwright 22 on three viewports. On the real share the first composition of 1.1
anchored on the DevOps Professional course's opening lectures; two rules fixed it: depth
is minutes weighted by match strength with a course made for this exam leading when it
has at least half the deepest depth, and the anchor's sections are ordered by relevance.

Then #28 as v0.24.0: `app/corpus/transcribe.py` (pending jobs by the catalog's caption
rule, ffmpeg to 16 kHz mono, three backends behind an injectable runner, a manifest per
course, resumable), `app/cli/transcribe_cmds.py`, `make transcribe`. Pierce decided the
VTTs go on the share beside each video. For the backend he asked for current data, not
memory: the Hugging Face Open ASR leaderboard's May-2026 snapshot tops with IBM Granite
Speech 4.1 2B (5.33% mean WER), Cohere Transcribe, NVIDIA Canary-Qwen 2.5B and Qwen3-ASR
1.7B, all PyTorch or NeMo with no MLX fast path; on Apple silicon NVIDIA Parakeet TDT 0.6B
v3 via parakeet-mlx (Apache-2.0, `uv tool install parakeet-mlx`, about 1.2 GB) transcribes
English at roughly 100× realtime on an M4 Pro against about 14× for Whisper large-v3-turbo
under whisper.cpp, with equal or better English WER (2.5% against 2.9% on LibriSpeech clean
in one independent benchmark); Whisper turbo keeps 99 languages. Recommendation:
parakeet-mlx for the English backlog (the five uncaptioned SAA courses are about 900
lectures), Whisper turbo only for non-English material. Nothing installed and no run
started; the pick is Pierce's. A one-lecture trial with the installed openai-whisper
`base.en` took 113 s for a short intro: fine for the pipeline check, far too slow for the
backlog.

Pierce then picked Parakeet; `parakeet-mlx` was installed as a uv tool, a one-lecture trial
took 39 s including the model download, and the SAA run onto the share started at 07:35
(about four lectures a minute from the laptop, the SMB read and ffmpeg decode dominating,
so roughly four hours for the five courses). Then #67 as v0.25.0: a 57-lecture sample
across the three SAA courses was labelled by the agent from title, section and excerpt
(45 with an objective, 12 course intros with none) into `corpus/eval/saa-c03.json`, and
`services/lecture_eval.py` plus `make lectures-eval` re-rank it from the stored term counts
under any parameter set. Measured: an absolute floor against each objective's best (or 90th
percentile) score cost top-1 accuracy at every setting; a section prior gained nothing;
lighter lesson bodies and stems did not move it; leaving out terms in more than 40% of the
lectures and dividing each score by the query's mass gained two points each on top-1 and
any-of-top-3 (67% to 69%, 91% to 93%); a housekeeping rule (welcome, course tour, support,
and a section opening only in the first section) leaves 4 of the 12 intros unmapped. The
three gains are the build's defaults now; the harness keeps the other levers. The misses
left are judgment calls between sibling objectives (1.2 over network topics, 2.2 over
database and storage topics), shaped by which objectives the pack's lessons and questions
cover; the pack and Pierce's pins are the levers after this.

Then, on Pierce's "go on #66, then #65": v0.26.0 moved the review queue into
`services/lecture_queue.py` (own-exam courses first by currency, the course's place among
the pending courses and what is left of it and its section on the card, whole-section and
whole-course accept or exclude as one review row per lecture; the review contracts moved to
`contracts/lecture_review.py`, the card's new block is `ReviewWhole`). v0.27.0 added
`services/watch_outcomes.py`: `AnswerFacts` gained `answered_at`, each objective's Progress
row carries `watch` (lectures watched, first attempts before and after the first watch),
and the comparison's `outcome_attempts`/`outcome_correct` count first attempts after
watching a lecture of that course mapped to the objective. Both are correlation on small
samples and say so. #61's five slices are all shipped; the levers left are the pack's
coverage, Pierce's pins, and the transcripts landing on the share.

2026-10-15, early morning, second block (Claude Fable 5.1): the Istari design system
Pierce built in Claude Design was adopted as v0.15.0 to v0.19.0 (#55: #56–#60). The
analysis before the go: the system's stylesheet covered 174 of the 185 class names the code
uses; Pierce's session added the rest (layout rules, the phone tab bar, explicit modifiers,
page previews, OFL texts) in a third pass, after which 185/185 were covered and no token
was undefined. Then: fonts, tokens and the stylesheet replaced the seven v0 partials with
the markup untouched (v0.15.0); the few markup differences were aligned (v0.16.0); the
course picker, the track chip and the per-track counts and progress landed with
`PATCH /api/settings {active_exam_version_id}` (v0.17.0); the phone shell got the More
sheet and the desk-only Progress link (v0.18.0); the plan rows lost their duplicated kind
prefix and the docs, this file and the system's README and PlanList preview were brought in
line (v0.19.0). Gates at each commit: ruff/mypy/import-linter/tsc/eslint/prettier clean,
pytest 150 passed, vitest 40 passed, Playwright 13 passed on desktop, mobile and
ultrawide (the phone-shell spec skips off mobile), `make validate` clean. Every page was
eyeballed at desktop and phone widths against the dev servers. One known wart left for the
system: its PlanList preview had a tag-and-duration row shape its own CSS does not
implement; the preview now shows the code's shape and the README says so.

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
