# Content packs: schema, scoring and import semantics

A content pack is one JSON document (`content/packs/<slug>/pack.json`) that carries a
whole learning track: subject, certification, exam version, domains and objectives,
and the items (lessons, questions, flashcards, labs). The schema is defined with
Pydantic in `backend/app/domain/content/schemas/` and is **strict**: unknown keys are
errors, so a typo can never silently drop content.

Validate without a database:

```bash
cd backend && uv run python -m app.cli validate-pack ../content/packs/aws-saa-c03-starter/pack.json
```

## Document shape

| Section | Required fields | Notes |
|---|---|---|
| `schema_version` | literal `1` | |
| `pack` | `slug`, `name`, `version` (semver), `authored_by` (`ai` / `human`) | `coverage_notes_md` is shown in the app; say what the pack does and does not cover |
| `subject` | `slug`, `name` | e.g. `aws` |
| `certification` | `slug`, `name`, `provider` | |
| `exam_version` | `code`, `name`, `duration_minutes`, `scored_questions`, `unscored_questions`, `passing_scaled_score`, `score_scale` | `verification.status` is `unverified` unless `checked_on` and at least one source are present; `current_since` (optional date) is when this version replaced the previous one, so a course that names the certification and an earlier year counts as an older version; `scope` (optional) copies the guide's appendix: `technologies`, `in_scope` and `out_of_scope` as `{category, services[]}` groups |
| `domains[]` | `code`, `name`, `weight_percent`, `objectives[]` | objective codes must start with the domain code (`1.2` belongs to domain `1`) |
| `lessons[]`, `questions[]`, `flashcards[]`, `labs[]` | see below | may be empty lists |

Every item carries the shared base fields:

- `slug`: `^[a-z0-9][a-z0-9-]{1,98}$`, unique across the pack, stable forever (user notes,
  answers and cards reference it). The field is not called `key` because secret scanners
  read `"key": "<value>"` as a credential; the API and database still say `item_key`.
- `objectives`: one or more objective codes, unique.
- `sources`: at least one `{title, url, checked_on}`; `url` must be `http(s)`.
- `provenance`: `{authored_by, author, authored_on, source_checked, notes}`. `source_checked`
  means every technical claim was checked against the listed sources. It is not human review.
- `review_status`: `draft` | `source_checked` | `human_reviewed`.
- `tags`: free-form strings.

### Lessons

`title`, `summary`, `body_md` (at least 200 characters), optional `foundations_md` (shown on
demand for readers who want groundwork first), `estimated_minutes` (1 to 60), `checks[]` of
`{prompt_md, answer_md}` self-checks that are revealed, never graded. `figures[]` lists the
pack's figures the lesson shows, by slug; `body_md` may place one where it belongs with
`![alt](figure:slug)`, and the rest follow the body. `labs[]` lists the pack's labs the
lesson's "Do it" step uses, by slug: the viewer runs a graded lab inline (task, set up,
terminal, check) and shows a brief's goals, steps and expected observations; a lab may serve
several lessons and links back to each.

### Questions

- `stem_md`, `difficulty` (`easy` | `medium` | `hard`), `decisive_constraint` (the one
  requirement that decides the answer), `explanation_md`.
- `options[]`: 3 to 6 of `{id, text_md}`. **Option ids are stable descriptive slugs**
  (`^[a-z0-9][a-z0-9-]{0,31}$`), never letters: options are shuffled per session, and the
  answer key is matched by id.
- `select_count` must equal the number of `correct_option_ids`; at least two distractors are
  required; option texts must be distinct after whitespace and case normalisation.
- `distractor_rationales`: a map from **every incorrect option id** to why it is wrong. The
  validator rejects missing or extra keys.
- `family`: optional; groups variants of one scenario so a learner never sees two members in
  one session and first-attempt evidence is counted once per family. Defaults to `slug`.

### Flashcards

`front_md`, `back_md`, optional `hint_md`.

### Labs

`title`, `estimated_minutes` (5 to 480), `goals_md`, `prerequisites_md`, `cost_warning_md`
(at least 40 characters: every lab names what costs money), `steps_md` (at least 200
characters), `expected_observations_md`, `cleanup_md` (at least 40 characters). Labs are
briefs for work the learner does in their own account. Istari never provisions anything.

A lab may carry a `verifier`, which turns the brief into a task graded by a backend the
owner runs (see `docs/labs-k16s.md`):

```json
"verifier": {"backend": "k16s", "profile": "cka", "question": "02-fix-crashloop", "weight": 5}
```

`backend` is one of `k16s` and `localemu` (implemented), `ck-x`, `real-aws`, `kubernetes`
(reserved; a pack naming a reserved backend fails validation with "not implemented").
`localemu` grades AWS labs against the LocalEmu emulator in the owner's lab; its `profile`
is a scenario family (`saa`) and its `question` a scenario id (`s3-versioning`):

```json
"verifier": {"backend": "localemu", "profile": "saa", "question": "s3-versioning"}
```

`profile` is the backend's own grouping, `question` its question id (a slug), `weight`
(1 to 20, default 1) its relative weight, `time_limit_minutes` optional. The task text
lives in the backend and is fetched live (for `localemu`, the backend is Istari's own
scenario code, so its text is ours); the pack holds only the reference. With a
verifier present, `cost_warning_md`, `steps_md` and `cleanup_md` only need to exist (20
characters), since the backend supplies the task. The verifier is part of the revision
hash, so changing it makes a new revision like any other content edit.

### Figures

A figure is a drawing of the thing a lesson teaches, kept as pack content so it is reviewed,
versioned and served like any item: `title`, `caption_md` (the decision rule the drawing
shows, a sentence or two), `alt` (what it shows, for readers who cannot see it), and the
drawing itself as `svg`, or as `file`, a path relative to the pack folder that the loader
reads into `svg` before validation (`seed`, `import-pack` and `validate` do; a pack sent to
`/api/content/import` carries `svg` inline). The path never enters the content hash, so an
export, which carries `svg`, re-imports as unchanged. The SVG must be inert: no scripts,
event handlers, embedded documents or external references; icons are inlined as data URIs.
`GET /api/figures/<slug>.svg` serves the current revision. Drawings are rendered offline
from a script kept beside them (`figures/<slug>.py`, mingrammer/diagrams on Graphviz, with
the provider's own icons) by `make figures`, and `make figures-check` catches a committed
drawing that drifted from its script (`docs/figures.md`). A figure attaches to objectives,
never to a course or a lecture: a lesson shows it by slug, and lectures mapped to the same
objectives borrow it.

## Cross-reference validation

`validate_pack` runs after the schema passes and reports:

- objective codes referenced by an item that no domain defines (error);
- duplicate item keys across kinds (error);
- objectives with no items at all (warning);
- near-duplicate question stems (warning);
- a lesson that lists or places a figure the pack does not ship (error);
- a lesson that lists a lab the pack does not ship (error);
- a figure with no drawing, because its `file` was never read (error).

The CLI and the `/api/content/import` endpoint both run it; import refuses on errors.

## Scoring policy

- The answer key never leaves the server before submission. A session item view carries
  option ids and texts only; `FeedbackView` (correct ids, explanation, rationales, sources)
  is attached after the item is answered, and in **assessment** sessions it is withheld until
  the whole session is completed.
- Multi-answer questions are graded as an **exact set**: the selection must equal the
  correct set. There is no partial credit. The server also rejects a selection whose size
  does not match `select_count`.
- Confidence (`guessing` | `uncertain` | `confident`) is optional and never affects the
  score. It feeds the Progress view's "confident mistakes" list and the planner's retry order.
- Answers are idempotent: one answer per session item, and a repeated submission with the same
  `request_id` returns the recorded result instead of recording twice.

## Import semantics

Import is idempotent and content-addressed:

1. Each item is hashed over its content (the base fields, kind-specific fields and sources).
2. A new slug creates an item with revision 1. A known slug with a changed hash creates a
   **new revision** and marks it current; earlier revisions stay, so old answers keep pointing
   at the text the learner actually saw.
3. A slug present in the database but absent from the pack is **retired** (status
   `retired`), never deleted. Retired items drop out of selection but keep their history.
4. Track metadata (exam version, domains, objectives) is updated in place; weight or title
   changes are reported as `track_changes`.
5. User data (answers, notes, cards, evidence, progress) is never touched by import.
6. `dry_run=true` performs the whole import inside a savepoint and rolls it back, returning
   the same report.

`uv run python -m app.cli seed` imports every `content/packs/*/pack.json`; `import-pack`
takes one file; `export-pack` writes a pack back out of the database in the same schema, so
an exported pack re-imports as "unchanged".

## Review flags in the app

The Content page lets the owner set two flags per item:

- `user_approved`: lets an item whose `review_status` is `draft` count toward sessions and
  progress. Items at `source_checked` or `human_reviewed` are eligible without it.
- `status`: `active` | `invalidated` | `retired`. Invalidating keeps the history but excludes
  the item's answers from every progress figure, which is the right move when a question
  turns out to be wrong.

## The shipped pack

`content/packs/aws-saa-c03-starter/pack.json`: 8 lessons, 40 questions (2 multiple-response),
24 flashcards and 2 labs covering all 14 SAA-C03 task statements. Exam metadata was verified
against the official exam guide and certification page on 2026-10-05; since pack version
1.1.0 (2026-10-16) the objectives carry the guide's 107 knowledge and 82 skills statements
verbatim (exam guide version 1.1) and `exam_version.scope` its appendix of 13 technology
areas, 130 in-scope and 61 out-of-scope services. Every item is
AI-authored (`Claude Fable 5.1`), `source_checked` against AWS documentation on the same date,
and awaits human review. The test `tests/integration/test_real_pack.py` pins the counts,
objective coverage and a clean import.
