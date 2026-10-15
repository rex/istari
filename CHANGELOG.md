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
