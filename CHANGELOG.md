# Changelog

All notable changes to this project are documented here. This project
follows [Semantic Versioning](https://semver.org/) and
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Format:

```markdown
## [X.Y.Z] — YYYY-MM-DD — Agent: <name>
### Added | Changed | Fixed | Removed | Deprecated | Security
- <what changed, in imperative voice>
```

**Every commit requires a version bump and a matching entry here.** The
`scripts/check_version_bumped.py` gate enforces this; `auto-commit.sh`
calls `scripts/bump_version.py <level>` before commit.

**Bump level guidance** (agent decides per slice):
- `patch` — bug fix, documentation change, refactor with no behavior change
- `minor` — new feature, new public API, any backward-compatible addition
- `major` — breaking change, removal, incompatible behavior change

**Agent attribution is required.** Every entry names the agent (or human)
that authored the change. This is how we keep `git blame` honest when
multiple agents and humans work on the same slice.

Append new entries at the top. One entry per commit (same cadence as
version bumps).

---

## [0.35.0] — 2026-10-17 — Agent: Claude Fable 5.1
### Added
- "See it" in the player's rail (rex/istari#82): the pack's figures for the objectives the
  lecture is mapped to, pinned and ruled mappings first, excluded ones bringing nothing,
  served by `GET /api/figures/lecture/{course}?path=`. One figure serves every lecture on
  its topic; nothing is generated per lecture.

## [0.34.0] — 2026-10-17 — Agent: Claude Fable 5.1
### Added
- Nine more figures for the SAA-C03 pack (rex/istari#81), so every one of its eight
  lessons opens its key section with a drawing: cross-account access by assuming a role;
  envelope encryption with KMS; SNS and SQS fan-out; the four DR strategies; RDS Multi-AZ
  against read replicas (shown in both the availability and the database lessons, the same
  figure); block, file and object storage; a data lake on S3; S3 storage classes and a
  lifecycle; NAT gateway against a gateway endpoint. Each is drawn from the lesson's checked
  AWS sources with `make figures`, captioned with the decision rule, and mapped to its task
  statements.

## [0.33.0] — 2026-10-17 — Agent: Claude Fable 5.1
### Added
- `make figures` and `make figures-check` (rex/istari#80): every `content/packs/<pack>/figures/<slug>.py`
  is a mingrammer/diagrams script that writes `<slug>.svg` beside itself; `render` runs
  each in place, rewrites the node ids the library draws at random into stable ones and
  drops the generator's comments, so a committed drawing changes only when the drawing
  changes, then validates the packs it touched; `check` renders into scratch and compares,
  so a committed SVG never drifts from its script. The `figures` dependency group holds
  `diagrams`; Graphviz is installed by hand. `docs/figures.md` has the conventions.

## [0.32.0] — 2026-10-17 — Agent: Claude Fable 5.1
### Added
- Figures as pack content (rex/istari#79): `figures[]` items (title, caption, alt, and the
  SVG drawing read from a file beside the pack and checked to be inert), imported, exported
  and listed for review like any item, served by `GET /api/figures/{key}.svg`. A lesson lists
  the figures it shows and may place one in its body with `![alt](figure:slug)`; the lesson
  viewer renders them as captioned figures (title, the decision rule, the task statements
  served), the rest following the body, and the Content item page previews a figure. A figure
  attaches to objectives only, so lectures mapped to the same objectives can borrow it. The
  design system gains the Figure component (version 13).
- The first figure, `fig-vpc-two-tier`: a two-tier web app in a VPC with public and private
  subnets, drawn with mingrammer/diagrams on Graphviz from the VPC User Guide's production
  example, placed in "Securing the network and the data".
### Changed
- A Markdown image whose URL the renderer dropped, or a figure the lesson does not carry,
  shows its alt text in place instead of a broken image.

## [0.31.0] — 2026-10-17 — Agent: Claude Fable 5.1
### Added
- Groundwork for figures as pack content (rex/istari#79, not yet wired): the `figures[]`
  item schema with an SVG sanitizer (no scripts, event handlers, embedded documents or
  external references), `load_pack_file` that reads a figure's drawing from the file beside
  the pack, lessons' `figures` list, the figure view contract, the figure service and the
  `/api/figures/{key}.svg` route. Nothing registers or imports them yet; the pack schema
  accepts a `figures` section and `make seed` ignores it until the next slice.

## [0.30.1] — 2026-10-17 — Agent: Claude Fable 5.1
### Changed
- Docs only: `TASK_STATE.md` and `PROGRESS.md` record the outcome of the grading and
  master-course effort (rex/istari#70, parked with its findings and decisions on the issue),
  the finished Cloud/AWS transcription (every course captioned), the local-model
  measurements on the laptop, and the regroup toward seeing and doing inside the viewer.

## [0.30.0] — 2026-10-16 — Agent: Claude Fable 5.1
### Added
- `exam_version.scope` in the pack schema: the exam guide's appendix as `technologies`,
  `in_scope` and `out_of_scope` (category and services), stored with the exam version
  (migration 0007). The SAA-C03 pack carries the guide's 13 technology areas, 130 in-scope
  and 61 out-of-scope services.
### Changed
- The SAA-C03 pack's objectives now carry the exam guide's statements verbatim (version
  1.1): 107 knowledge and 82 skills statements across the 14 task statements, in place of
  the 37 and 36 paraphrases the starter pack shipped with. The lecture index's objective
  queries are built from them; measured on the 57-lecture sample, top-1 went from 69% to
  64% and any-of-top-3 from 93% to 91%, because the guide repeats its boilerplate across
  sibling objectives, and none of the harness's levers recovers it. The authoritative text
  stays; the ranking follow-up is filed under rex/istari#70.

## [0.29.0] — 2026-10-16 — Agent: Claude Fable 5.1
### Added
- `exam_version.current_since` in the pack schema: the date this exam version replaced the
  previous one (SAA-C03: 2022-08-30; the revised CKA curriculum: 2025-02-18, both with a
  source in the pack), imported and stored with the exam version (migration 0006).
### Changed
- A course that names the certification and a year, with no exam code, reads its year
  against `current_since`: dated before, it is an older version; dated after, this one; the
  same year or no year still reads "same exam, no version named". The 2018 Solutions
  Architect Associate course that anchored path 1.1 after the transcription run is now an
  older version and steps aside wherever a current course covers half its minutes.

## [0.28.0] — 2026-10-16 — Agent: Claude Fable 5.1
### Fixed
- A course title that names the certification's family at another level ("Solutions
  Architect - Professional" against the Associate certification) now reads as another exam
  rather than none named. With the five Solutions Architect courses transcribed, the
  Professional course, twice as long as any SAA-C03 course, had anchored every path.
- A course made for this exam leads a learning path whenever it has two hours of mapped
  lectures of its own, not only when it has half the depth of the deepest course.

## [0.27.0] — 2026-10-16 — Agent: Claude Fable 5.1
### Added
- Watch outcomes on Progress: an objective's row says how many of its mapped lectures were
  watched to the end and the first-attempt accuracy before and after the first of them,
  samples in plain sight, labelled correlation and never mastery.
- "After watching" on the course comparison: first attempts on an objective after a
  lecture of that course mapped to it was watched; a rate only from three attempts on,
  otherwise "nothing answered since" or "n answered, too few". Sortable.
### Changed
- Answer facts carry when the answer was given, so outcomes can be split at a watch.

## [0.26.0] — 2026-10-16 — Agent: Claude Fable 5.1
### Changed
- The lecture review queue puts the courses for the track's own exam first (current
  version, then the same certification without one, newer, older, other exams, none named)
  and says where the lecture sits: course n of m pending, the course's currency, how many
  lectures of the course and of its section are left.
### Added
- Decide a whole section or course at once from the review card: accept the rest as ranked
  (`s`, `c`) or exclude it (asks twice). One review row per lecture, so the lookups and the
  index stay as they are. `POST /api/lecture-index/review/course`.

## [0.25.0] — 2026-10-16 — Agent: Claude Fable 5.1
### Changed
- The lecture ranking leaves out terms found in more than 40% of the lectures, divides
  each objective's score by its query's mass (so the objectives with the most lessons and
  questions no longer win on count alone), and maps a welcome, a course tour or a support
  lecture to nothing. On a hand-labelled sample of 57 SAA lectures: top-1 67% to 69%, any
  of top-3 91% to 93%, course intros left unmapped 0 to 4 of 12.
### Added
- `make lectures-eval SAMPLE=corpus/eval/<exam>.json` (`app.cli lectures eval`): re-ranks
  a hand-labelled sample from the index's stored term counts under any parameter set
  (floor, percentile ceiling, generic share, query-mass power, body and stem weights,
  section prior, housekeeping) and prints the rates and every miss. The sample stays with
  the corpus.

## [0.24.0] — 2026-10-16 — Agent: Claude Fable 5.1
### Added
- `make transcribe SRC="<course or topic dir>" [ALL=1] [SHARE=1] [BACKEND=…] [MODEL=…]
  [LIMIT=n]` (`app.cli transcribe`): generated captions for the lectures that have none.
  ffmpeg extracts mono 16 kHz audio and the first installed backend of parakeet-mlx (NVIDIA
  Parakeet TDT 0.6B v3 on MLX), whisper.cpp (`large-v3-turbo`) and openai-whisper writes
  WebVTT. With `SHARE=1` the file lands next to the video on the share, where every player
  and the catalog pick it up, and a `.istari-captions.json` manifest per course names the
  model, backend and date per file; otherwise it lands under `corpus/<course-slug>/captions/`
  for a trial. Idempotent and resumable: lectures with any caption, or whose VTT exists, are
  skipped. The backends and ffmpeg are faked in the tests; a one-lecture trial with the
  installed openai-whisper `base.en` wrote a correct VTT and manifest into the corpus.

## [0.23.0] — 2026-10-16 — Agent: Claude Fable 5.1
### Added
- A learning path per objective (`/learn/path/<code>`, linked from the objective's row on
  Progress and from each domain on Learn): lectures composed across courses, continuity
  first. The course with the deepest coverage of the objective supplies a run of its
  lectures in course order, the other courses' strongest lectures fill in behind it, a
  course for an older version of the exam steps aside when a current one covers the same
  ground, and the path is capped at two hours. Every entry names its course and the reason
  it is there. Pin an order, exclude or restore a lecture, go back to the proposal; pins and
  exclusions survive every index run.
- The player follows a path (`?path=<code>`): previous and next move along it across
  courses, the bar says "n of m in path", and "Continue" on the path page starts at the
  first unwatched lecture.
- A 30-minute plan takes one lecture from the weakest objective's path ("Watch"), with
  its course and length in the reason; shorter plans do not.
- `/api/paths`: summaries, one objective's path, the owner's decisions, and a recompose;
  every lecture index run recomposes the proposals.
### Changed
- Course currency moved to `services/course_currency.py`, shared by the comparison and the
  paths.

## [0.22.0] — 2026-10-16 — Agent: Claude Fable 5.1
### Added
- Courses compared (`/watch/compare`, linked from Watch and from Settings beside the track
  chip): one row per course on the share for the track with the objectives it touches, how
  current its exam is (current, older or newer version, same exam with no version named,
  other exam, none named), captions,
  minutes of captioned lecture time mapped to any objective and to each domain, and the
  lectures watched. Sortable by any column; best coverage first. Coverage and currency,
  never a quality score; a course without captions shows a dash and the page says why.
- `GET /api/lecture-index/courses` serves the matrix from the catalog, the lecture index
  and watch progress; excluded mappings are left out.
- The design system gains sortable table headers (`table__sort`, `aria-sort`) and the
  courses table's phone column set (`table--courses`).

## [0.21.0] — 2026-10-16 — Agent: Claude Fable 5.1
### Added
- Lecture mapping in the Content area (`/content/lectures`): the index's status with a
  Rebuild button (polls while a build runs), then one unreviewed lecture at a time with its
  course, section, length, an excerpt of the captions and its candidate objectives, each
  with a match meter, the mapping's source and the terms that matched. Accept as ranked,
  pin the selected objectives (any objective of the track can be added), exclude the
  lecture, or skip it; `a`, `p`, `x`, `n` and `1` to `9` do the same from the keyboard.
- The player shows what a lecture teaches: its mapped objectives as badges under the title,
  pinned in gold, title rules in green, ranked matches in blue.
- The Playwright suite gets a one-lecture fixture course on the fixture track and a spec
  that rebuilds the index, reviews the lecture and sees the badge on the player.
### Changed
- A rebuild rescans the catalog before it reads a caption, so the index no longer depends
  on a Watch page having been opened first and picks up courses that landed since.
### Fixed
- Title rules fire only for courses in the track's exam family. The Cloud Practitioner
  course's "(OBJ 4.3)" file names name that exam's objectives and put 138 wrong `rule` rows
  on SAA-C03's first real run.
- The index status counted candidate courses by exam family only until the first run had
  finished, so it showed 3 for SAA-C03 while the build read all 59 AWS courses; it now uses
  the track's subject like the build does.

## [0.20.0] — 2026-10-16 — Agent: Claude Fable 5.1
### Added
- A lecture-to-objective index for the active track: the candidate courses on the share
  (same exam family, or filed under the track's subject) have their captions read in a
  worker thread, each lecture becomes term counts, and every lecture is ranked against the
  track's objectives with BM25 over a weighted query built from the objective's title,
  knowledge and skills statements and the lessons and questions already mapped to it.
  Words every objective shares count for nothing; a lecture keeps its few best objectives
  when they stand clearly above the rest and share enough terms to show why. Objective
  codes named in a lecture's title or file name ("obj-1-1", a leading "2.1") outrank the
  ranking; a domain's distinctive word in a section title lifts its objectives.
- The owner's decisions on top: a review queue hands over one unreviewed lecture at a time
  with its candidates, matched terms and an excerpt; pin the right objectives, exclude the
  lecture, or accept it as ranked. Pinned and excluded rows survive every rebuild.
- API under `/api/lecture-index`: status and rebuild (one build at a time, in the
  background), the review queue and decisions, a lecture's mappings, and the lectures
  ranked under an objective. Tables `indexed_lectures`, `lecture_objectives`,
  `lecture_reviews`, `lecture_index_runs` (migration `0004_lecture_index`). The review
  page in the Content area follows in the next version.

## [0.19.0] — 2026-10-15 — Agent: Claude Fable 5.1
### Changed
- Plan rows no longer repeat the kind: the planner's "Lab: …" and "Read: …" labels show as
  the kind badge plus the title, and a bare "Review" label is the badge alone.
- Docs record the split of authority with the design system: `docs/architecture.md`
  (Styles) explains that the system owns tokens and rules and the code owns markup, and how
  to change either; AGENTS.md and the README point at it. The design system's README and
  PlanList preview were brought in line with the adopted code (the preview had a row shape
  the system's own CSS does not implement). TASK_STATE and PROGRESS carry the handoff.

## [0.18.0] — 2026-10-15 — Agent: Claude Fable 5.1
### Added
- The phone layout the design system specifies: under 720px the primary nav is a fixed
  bottom tab bar of five (Today, Learn, Practice, Review, Watch) with 44px targets and the
  safe-area inset, the active tab in gold with a rule along its top edge. Progress is
  dropped from the bar as occasional and table-heavy; it, Labs and Settings live behind a
  ghost More button in the top bar that opens a sheet of ghost buttons (the same native
  dialog as the shortcuts help). Focus mode on a phone hides the bar, keeps the focus bar
  at the top and gives the column the full width; on wide screens nothing changes.
- A phone-only Playwright spec walks the tab bar, the More sheet and focus mode on the
  mobile project; the desktop and ultrawide projects skip it.

## [0.17.0] — 2026-10-15 — Agent: Claude Fable 5.1
### Added
- Choosing what to study is a course picker: one card per track with the provider, the
  certification, the code and its verification date, what the pack holds (lessons,
  questions, cards, labs), a meter with one progress sentence (coverage, in words: lessons
  read, question families seen, labs verified on the first graded attempt; accuracy only
  once there are enough first attempts for it to be evidence), when the track was last
  studied, and one primary button in the grid (Continue on the current track). It is a
  radiogroup: arrow keys move, Enter picks. It replaces the radio list in onboarding, and
  on Settings a compact chip in the page head shows the current track and opens it.
- The track list (`/api/tracks`, `available_tracks` on `/api/me`) carries those counts,
  the progress line and `last_studied_at` per track; `PATCH /api/settings` accepts
  `active_exam_version_id` to switch tracks, keeping everything done on the other.

## [0.16.0] — 2026-10-15 — Agent: Claude Fable 5.1
### Changed
- Markup aligned to the design system where its previews and the code differed. The
  system's stylesheet was written to this app's markup, so the differences were few: the
  confidence buttons are ghost buttons with `aria-pressed` (the pressed one is a raised
  secondary; gold belongs to Submit alone), Progress stats read label, value, note like
  the Today rail and the Stat preview, the objective table carries `table--objectives`
  (under 720px it keeps Objective, First attempt and Evidence with no sideways scroll)
  with right-aligned tabular figures, and the lecture title uses the player's own title
  style instead of a v0 utility class that no longer exists.
- The lab task card's gold top rule, the plan rows, the transcript cue and the
  feedback panel already matched the system's rules and needed no markup change. One
  inconsistency inside the system is left for the re-sync: its PlanList preview shows a
  kind tag with the duration at the right, while its own CSS (and this app) keep the
  count first; the CSS is the contract adopted here.

## [0.15.0] — 2026-10-15 — Agent: Claude Fable 5.1
### Changed
- The app renders in the Istari design system (claude.ai/design, built by Pierce on
  2026-10-15 from this repository's marks and component inventory): warm umber surfaces,
  vellum text, the mark's gold rationed to the one thing to do next, Cormorant Garamond
  for titles, Hanken Grotesk for the interface, Newsreader for anything read at length,
  JetBrains Mono for code and grader output. `styles/tokens.css` is the system's
  generated token file and `styles/bundle.css` its component stylesheet, written to
  this app's own class names; the seven v0 partials (`base`, `_layout`, `_components`,
  `_study`, `_pages`, `_watch`, `_labs`) are gone and nothing references a v0 token.
  Markup is unchanged in this slice; the per-area alignment follows.
- The four typefaces ship as Google Fonts latin subsets under `styles/fonts/`, each with
  its SIL Open Font License text, and load through `@font-face` with `font-display: swap`.

## [0.14.0] — 2026-10-15 — Agent: Claude Fable 5.1
### Added
- The CKA v1.35 track as a content pack (`content/packs/k8s-cka-k16s`): domains and
  objectives from the CNCF curriculum (CC-BY-4.0) and one verified lab per K16S CKA
  question, 36 across the `cka` and `cka2` profiles, each referencing its question by id
  only with brief fields in Istari's own words; the two tasks that need the full install
  are tagged. Exam facts are checked against the Linux Foundation page and the unpublished
  task count is declared an estimate.
- `istari labs check-map` (`make labs-check`): reads the packs, asks the configured K16S
  instance for each profile's questions and reports the labs whose question is not served
  (exit 1), served questions no lab covers, weight drift and full-install-only tasks; exit
  2 when no backend is configured or the instance does not answer.
- The Labs list groups verified labs by domain, ordered by objective within a domain, with
  a passed count per group.
### Changed
- The K16S stub can serve any id list with placeholder text, so the mapping check is
  tested against the shipped pack without a cluster.

## [0.13.0] — 2026-10-15 — Agent: Claude Fable 5.1
### Added
- Verified labs in the daily plan: when the lab cluster answers and the session is 15
  minutes or longer, Today schedules one open verified lab (weakest objective first, after
  resume, review and practice and before a lesson) and explains why; when the cluster is
  silent the plan says labs are skipped and why; a track without a backend never mentions
  them. Today and Progress open the lab straight from the plan.
- Labs as progress evidence: per objective, domain and track, Progress counts verified
  labs, labs attempted and labs passed on the first graded attempt; later passes are
  repeats, as with questions. The objective table gains a Labs column and a stat appears
  only when the track has verified labs.

## [0.12.0] — 2026-10-15 — Agent: Claude Fable 5.1
### Added
- The lab page for a verified lab: a cluster chip that names the first thing in the way
  (not configured, unreachable, task unavailable in this mode, task not found, or ready
  with a note when a setup would switch the cluster's session); the task text fetched
  live from the backend and shown with attribution, context, and the hint behind a
  disclosure; three steps with one primary action each (set up the environment, open the
  terminal in a new tab, check the answer), the done steps ticked and the setup output
  kept behind a disclosure; the verdict verbatim from the grader ("Passed" or "Not yet"
  with its reason line, never a percentage); the attempt history, failures included; and
  the brief's own notes folded underneath. Manual labs render as before.
- The Labs list groups verified labs under a strip showing the cluster's state from the
  API's last poll, and each card carries the latest verdict with its reason line.
- Playwright: `verified-lab.spec.ts` runs the loop against the stub K16S, which
  `playwright.config.ts` now starts as a second web server; the e2e database gains the
  fixture pack with its two verified labs. Component tests cover the phase model, the
  primary-action rule, the verdict and the cluster chip.

## [0.11.0] — 2026-10-15 — Agent: Claude Fable 5.1
### Added
- `lab_attempts` (migration `0003_lab_attempts`): one row per run of a verified lab with
  `setup_at`, `checked_at`, `passed` (NULL until graded), the grader's output capped at
  16 KB, and the setup-to-check duration. `lab_evidence` stays the owner's own notes.
- `GET /api/labs/{key}/verifier`: configured/reachable state, the instance's mode and active
  profile, terminal and map links, the task text fetched live with attribution, an
  `unavailable_reason` when the task cannot run in the current mode, one plain `message`
  when something is in the way, and the attempt history. `POST /api/labs/{key}/setup`
  ensures a session on the lab's profile, runs the setup script and records an attempt;
  `POST /api/labs/{key}/check` grades the open attempt (or a fresh one). An `unavailable`
  answer and a transport failure both record nothing; the latter is a 502.
- Lab summaries carry `verifier`, `attempt_count` and `last_attempt` (the latest graded
  attempt with its reason line) for the cards. Setup and check log the lab, the question,
  the result and the duration.

## [0.10.0] — 2026-10-15 — Agent: Claude Fable 5.1
### Added
- K16S adapter (`app/adapters/k16s`): the exam server's seven endpoints as plain domain
  data (`app/domain/verifier.py`, `app/domain/verifier_mapping.py`), with the session
  policy (one active session, reused on the same profile, switched only when a lab needs
  another), a 60-second question cache, and a status snapshot refreshed in the background
  so `/api/health` and the planner never wait on the cluster. Timeouts: setup 90 s, check
  45 s, reads 10 s. Every transport failure, timeout or non-2xx becomes `upstream_error`
  (HTTP 502) with a sentence naming the server and the limit; `unavailable` is a reason,
  not an error.
- Config `K16S_BASE_URL`, `K16S_PUBLIC_URL`, `HEADLAMP_URL` (unset disables verified labs);
  `/api/health` reports `k16s: {configured, reachable, mode, profiles, checked_at}`.
- `tests/k16s_stub.py`: a stand-in exam server with its own placeholder text, controllable
  pass/fail and modes, used in-process by the integration tests and standalone by Playwright.
  `docs/labs-k16s.md` documents the contract, the licence rule (no K16S text in this
  repository) and development without an instance. `httpx` is a direct dependency.

## [0.9.0] — 2026-10-15 — Agent: Claude Fable 5.1
### Added
- Pack schema: a lab may carry a `verifier` (`backend`, `profile`, `question`, `weight`,
  `time_limit_minutes`), which turns the brief into a task graded by a backend the owner
  runs. `k16s` is implemented; `ck-x`, `localstack`, `real-aws` and `kubernetes` are
  reserved and fail validation with a "not implemented" message. With a verifier, the
  brief's cost, steps and cleanup fields only need to exist (20 characters), because the
  task text comes from the backend; manual labs keep the long-form minimums. The verifier
  is part of the revision hash and round-trips through export and re-import unchanged.
  Documented in `docs/content-schema.md`; the test fixture pack gains two verified labs.

## [0.8.2] — 2026-10-08 — Agent: Claude Fable 5.1
### Changed
- Handoff: homelab-ansible#71 fixed and the static DNS record converged (already present through external-dns); nothing is pending on the lab side

## [0.8.1] — 2026-10-08 — Agent: Claude Fable 5.1
### Changed
- Handoff for the homelab deployment (#40): the GitHub-to-mirror-to-Flux chain, what was verified, the lab-side versions; AGENTS.md gotchas for anchored ignore rules, editor-expanded unicode escapes and the GitHub-first mirror

## [0.8.0] — 2026-10-08 — Agent: Claude Fable 5.1
### Fixed
- The image's frontend stage installs the pinned pnpm with `npm install -g` instead of
  corepack: `node:26-slim` no longer bundles corepack, so the first image build on the
  lab's CI stopped with `corepack: not found` (exit 127). Verified by building the stage
  locally.

## [0.7.0] — 2026-10-08 — Agent: Claude Fable 5.1
### Fixed
- `backend/app/corpus/` is in the repository at last. The ignore rule `corpus/` was meant
  for the derived corpus at the repo root but, unanchored, it also matched the source
  package, so every clean checkout from v0.4.0 to v0.6.0 failed to import `app.corpus`
  (the first Gitea CI run failed typecheck on exactly that). The rules are anchored now
  (`/corpus/`, `/content/private/`); the derived material stays ignored.

## [0.6.0] — 2026-10-08 — Agent: Claude Fable 5.1
### Added
- `scripts/entrypoint.sh` is the container command: `alembic upgrade head`, the pack
  import (`seed`, skipped with `ISTARI_SEED_ON_START=false`), the owner account from
  `ISTARI_OWNER_USERNAME` and `ISTARI_OWNER_PASSWORD` when the database has none yet,
  then uvicorn. A failing step stops the container.
- `bootstrap-owner --if-missing` keeps an existing owner and exits 0, so a restart or a
  rotated secret never replaces the account; `--username` falls back to
  `ISTARI_OWNER_USERNAME`. The shared logic lives in `app/cli/owner.py` with tests.
- `.gitea/workflows/ci.yml`: on a Gitea instance, every push runs `make validate` and
  `make test` against a throwaway Postgres service container (trust authentication, so the
  workflow holds no credential); a push to `main` builds the image and pushes it to that
  instance's registry, derived from the server URL, tagged `latest` and with the commit
  sha, with three push attempts. The file names no hosts.
- `docs/deployment.md`: entrypoint behaviour, the owner variables, the CI flow and a
  hostname-free Kubernetes note (probes on `/api/health`, read-only `LEARNING_ROOT`).

## [0.5.1] — 2026-10-08 — Agent: Claude Fable 5.1
### Changed
- Handoff notes: corpus ingest totals, roadmap issues #29-#39

## [0.5.0] — 2026-10-07 — Agent: Claude Fable 5.1
### Added
- Watch: the video courses on the learning share, inside Istari. `LEARNING_ROOT` and
  `LEARNING_TOPICS` name the mounted share and its course folders; a background scan
  lists every directory with videos as a course, its subdirectories as sections, with
  lectures in natural order and their caption tracks matched by stem. The share is read
  in place and never written.
- `/watch` lists courses grouped by topic with exam code, year, caption coverage and a
  "continue" lecture; `/watch/<course>` lists sections and lectures with progress;
  `/watch/<course>/play` streams the lecture (Range requests, so seeking works) with
  the subtitle track as WebVTT (SRT converted on the fly), resumes where you left off,
  saves position every five seconds and on pause, marks a lecture watched at 95 percent
  or on "Mark watched", and moves on to the next lecture when one ends.
- Transcript panel beside the video: the captions as searchable, click-to-seek text
  with the current cue highlighted and followed.
- Keyboard: Space/k play or pause, j/l ±10 s, arrows ±5 s, f fullscreen, n/p next or
  previous lecture; listed in the shortcuts help.
- `course_progress` table (migration `0002_course_progress`), `/api/courses` endpoints,
  and tests: naming and caption rules, catalog scan of a temporary tree, byte-range
  streaming, caption conversion, progress round trip, path safety (only catalogued paths
  resolve), VTT parsing and the transcript panel.
### Changed
- Exam-code inference, slugs and natural sorting moved to `domain/naming.py`, shared by
  the corpus tooling and the catalog.

## [0.4.0] — 2026-10-07 — Agent: Claude Fable 5.1
### Added
- Private corpus tooling (`backend/app/corpus/`): subtitle tracks (SRT, WebVTT) become
  readable transcript text; HTML, EPUB, DOCX go through pandoc and PDFs through
  pdftotext; `corpus-ingest` walks one course directory into a gitignored
  `corpus/<course>/` with a manifest (exam code and year inferred from the name,
  every file written or skipped with a reason); `--all` treats a topic folder as a set
  of courses. The source directory is never written.
- `corpus-udemy`: Udemy section-quiz HTML exports and practice-test results PDFs parse
  into a private pack (`content/private/`, gitignored) in Istari's own schema: items
  are `draft`, authored by the vendor, not source-checked, grouped into domains by quiz
  or test, under an `<EXAM>-DRILL` exam version so they never mix with a verified
  pack. Invalid questions are reported and left out. `make corpus-ingest` and
  `make corpus-udemy` wrap both.
- `docs/corpus.md`: what the corpus is for (coverage maps, drafting input, drill), what
  it is not (a fact source), the commands, and the currency table for the AWS library.
- Unit tests for captions, ingestion, both Udemy parsers and the private-pack builder,
  all on synthetic samples shaped like the exports.

## [0.3.0] — 2026-10-07 — Agent: Claude Fable 5.1
### Added
- Every page, the login page included, shows a build badge: version, git commit short
  hash, image build time and the process start time ("up since"). The API is the source
  of truth (`/api/health` now reports `version`, `commit`, `built_at`, `started_at`);
  the SPA embeds its own commit and says so when it differs from the API's.
- `backend/app/buildinfo.py` resolves the stamp once at startup: `GIT_COMMIT` and
  `BUILD_DATE` from the environment, else `git rev-parse --short HEAD` in a checkout,
  else `unknown`. The startup log line names version, commit and build time.
- `make docker-build` / `make docker-up` pass `APP_VERSION`, `GIT_COMMIT` and
  `BUILD_DATE` as build args; the image carries them as environment variables and OCI
  labels (`org.opencontainers.image.{version,revision,created,source}`).
- Tests: build-info resolution (unit), health body (integration), `BuildBadge`
  (component, including the stale-bundle warning), badge on login and Today (e2e).
### Changed
- Skeleton synced to agentic-skeleton 0.50.0: `scripts/check_skills.py` and
  `scripts/stamp_skill.py` added, provenance stamped in `VIBE.yaml`. The Makefile
  keeps its repo-specific recipes (advisory drift, reconciled by hand).
### Fixed
- The very first `GET /api/me` on a fresh database created the settings row without
  protection, so two overlapping first requests (the SPA's post-login refetch plus any
  second tab or probe) made one of them fail with a 500. The insert now runs in a
  savepoint and the loser reads the winner's row. Regression test added.
- Playwright: the keyboard-shortcut test decided "abandon or start" before the
  active-session request had answered; it now waits for that response. The login helper
  fails loudly when its `/api/me` probe is not 200 instead of silently skipping
  onboarding.

## [0.2.0] — 2026-10-05 — Agent: Claude Fable 5.1
### Added
- `content/packs/aws-saa-c03-starter/pack.json`: 8 lessons, 40 scenario questions
  (2 multiple-response), 24 flashcards and 2 lab briefs covering all 14 SAA-C03 task
  statements; exam metadata verified against the official exam guide and certification
  page on 2026-10-05; every item AI-authored, `source_checked` against AWS documentation.
- `tests/integration/test_real_pack.py` pins the pack's counts, objective coverage,
  provenance and a clean idempotent import (backend suite: 75 tests).
- `docs/architecture.md`, `docs/content-schema.md` (scoring policy and import semantics),
  `docs/deployment.md` (no assumed hostnames); AGENTS.md, README.md and TASK_STATE.md
  filled in; `.claude/session-context.md`.
### Changed
- Pack items identify themselves with `slug` instead of `key`: gitleaks reads
  `"key": "<value>"` as a generic API key, and a public repo cannot carry that false
  positive in every pack. The API and database keep `item_key`.
- Option ids in the pack schema may be up to 32 characters (descriptive slugs).
- `make e2e` exports `E2E_DATABASE_URL` for the whole recipe; the Playwright global setup
  resolves paths with `import.meta.url` (the frontend is an ES module package).
- Playwright spec: onboarding is completed deterministically by asking `/api/me`, and
  the five-question session starts from the Practice page, because a fresh pack rightly
  puts due flashcards first in the Today plan.
- `make lint` and `make fix` recipes no longer chain two `cd` commands.
### Fixed
- Progress summary and domain headers counted a lesson once per objective it teaches
  (the shipped pack showed 0/14 lessons for 8 lessons). Distinct lessons are counted
  now; per-objective rows are unchanged. Covered by `test_progress_counts_each_lesson_once`.
- First full Playwright run: 9 passed on desktop, mobile and ultrawide.

## [0.1.0] — 2026-10-05 — Agent: Claude Fable 5.1
### Added
- Project scaffold from `agentic-skeleton` (AGENTS.md, VIBE.yaml, Makefile
  gates, `.claude/` hooks, pre-commit with detect-secrets + gitleaks).
- Backend (FastAPI + SQLAlchemy async + Alembic): single-owner auth with
  argon2id, server sessions, CSRF and login throttling; subject →
  certification → exam version → domain → objective model; practice
  sessions with server-side grading, exact-set multi-answer, confidence
  and idempotent answers; py-fsrs review scheduling behind an interface
  with a daily limit and backlog recovery; Today planner; Progress
  evidence views; lessons, notes, labs with evidence; content pack
  import/export with strict validation, revisions and retirement;
  operator CLI (`bootstrap-owner`, `seed`, `import-pack`, `export-pack`,
  `validate-pack`); `/api/health`; structured logs with request ids.
- Frontend (React 19 + Vite 8 + TanStack Router/Query): Today, Learn,
  Practice, Review, Progress, Labs, Settings and Content pages with
  keyboard shortcuts, focus mode, sanitized Markdown and brand assets.
- Postgres compose stack, hardened Dockerfile, backup/restore scripts
  with a tested restore into an isolated database, secret-scan CI
  workflow.
- Backend tests (73) and frontend unit/component tests (16).
- `make db-revision REV_ID=<slug>` to give Alembic revisions descriptive ids; the
  initial migration is revision `0001`.
### Changed
- `DATABASE_URL` is required (no default DSN with a password); `TEST_DATABASE_URL` derives
  from it. `.env.example` and compose interpolate `POSTGRES_PASSWORD`; compose refuses to
  start without it. Playwright takes its DSN from `E2E_DATABASE_URL` only.
- Modules over the eight-public-definition cap are split by resource:
  `contracts/session_requests.py`, `domain/planning_types.py`,
  `services/progress_activity.py`, `queries/{lessons,review,labs,progress,track}.ts`.
### Security
- Test owner passwords are generated per run; no literal credentials are in the tree
  (detect-secrets and gitleaks pass on every file).
