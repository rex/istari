# TASK_STATE — <feature-name>

> Source of truth for in-flight work. Humans and agents both write here.
> This file is **committed** to the repo. It survives sessions, machines,
> and context compactions.
>
> Spec: `specs/<slug>/spec.md` · Plan: `specs/<slug>/plan.md`
> Branch: `<branch>` · Owner (human): @<user> · Last update: <date> by <agent>

## 0. TL;DR for a fresh agent session

<2–4 sentences. What phase are we in, what's the next action, what NOT to touch.>

Example:
> We are mid-Phase 2 of adding `/api/health` to billing-service. Phase 1
> (contract+schema) is done and merged to branch. **Next action: pick up
> Slice 2.2** — Redis probe with timeout. Do NOT touch
> `app/health/contracts.py` (frozen Phase 1).

## Standing user directives

<!-- Record durable per-task user directives here. "Continue until blocked",
     "do not wait for my input unless blocked", "skip tests for this slice"
     — anything Pierce said that should survive compaction. -->

- (none currently)

## 1. Phases

| # | Phase | Status | Exit criteria |
|---|---|---|---|
| 1 | <phase name> | ⏸ pending | <what's true when this phase is done> |
| 2 | <phase name> | ⏸ pending | <...> |

Statuses: `⏸ pending` · `🟡 in-prog` · `✅ done` · `🔴 blocked`

## 2. Slices (vertical, atomic, independently mergeable)

### Slice 1.1 — <imperative title>

- Status: ⏸ pending
- Owner: <agent or human>
- Files (planned edits): `<path>`, `<path>`
- Files (do NOT edit): `<path>`
- Depends on: (none) | Slice X.Y
- Acceptance (EARS notation):
  - [ ] When <trigger>, the system shall <behavior>.
  - [ ] While <state>, the system shall <constraint>.
  - [ ] If <event>, then the system shall <response>.
  - [ ] Tests: <test names>
  - [ ] Lint + typecheck green

### Slice 1.2 — <next>

- Status: ⏸ pending
- Files (planned edits): ...

## 3. Blockers / open questions

- (none yet)

## 4. Recent decisions (append-only, newest first)

- <date> — <decision> (<who decided>, <context>)

## 5. Next actions (ordered)

1. <immediate next action>
2. <then>
3. <then>

## 6. Handoff note (fill when ending a session)

<Last session>: <what was accomplished, what's half-finished, where to
resume. Specific files + failing tests if applicable.>
