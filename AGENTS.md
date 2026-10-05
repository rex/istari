# AGENTS.md

<!-- Single source of truth for Claude Code, Codex, Gemini CLI, Cursor, Copilot.
     CLAUDE.md and GEMINI.md are symlinks to this file. Keep under 150 lines. -->

## 1. Project snapshot
- **What**: <one sentence>
- **Runtime**: <language + versions + frameworks>
- **Infra**: <Terraform / Ansible / Helm / etc.>
- **Owner**: #<channel>. On-call: `docs/oncall.md`
- **Non-goals**: <what this service will NOT do>

## 2. Setup

```bash
# Replace per stack (lang-* skill fills these in at bootstrap time)
make setup
```

## 3. Commands the agent MUST run before declaring done

- `make lint`
- `make typecheck`
- `make test`  (if testing is enabled in `VIBE.yaml`)
- `make check-architecture`  (if declared)
- `make check-skeleton` — skeleton-owned files (`scripts/`, `.claude/{hooks,commands,agents,rules}`) match the installed agentic-skeleton; if behind, `make sync-skeleton`, then commit + push
- If `infra/**` changed: `terraform fmt -recursive infra/ && terraform validate`
- If `ansible/**` changed: `ansible-lint ansible/ && ansible-playbook --syntax-check`

## 4. Repo layout

```
app/           Application code (flat, layered by concern — see CONVENTIONS.md)
tests/         Mirrors source layout
infra/         Terraform + Ansible (if applicable)
specs/         Spec-driven dev artifacts — read specs/<active>/ first
docs/adr/      Architectural decisions (MADR) — read README.md index
agent_docs/    On-demand deep-dive (not auto-loaded)
scripts/       Repo tooling (gates, version bumps, scripts/mcp/ credential helper)
.claude/       Subagents, slash commands, rules, hooks, MCP config
```

## 5. Code style (non-negotiable)

See `CONVENTIONS.md`. Linters enforce formatting and import order — **do not
write style rules here that the linter already checks.**

## 6. Testing policy

See `VIBE.yaml` (`quality_gates.tests`). If testing is `required`, every code
change gets a corresponding test update.

## 7. Security (hard stops)

- No secrets committed. `detect-secrets` + gitleaks enforce.
- Parameterized queries only.
- No wildcard IAM. No `0.0.0.0/0` except 443 on ALBs.
- MCP credentials never touch `.env` — they resolve at connect time through
  `scripts/mcp/op-headers.sh` and degrade to OAuth / anonymous tier.
- See `.claude/rules/security.md` for full checklist.

## 8. Architectural decisions

- Read `docs/adr/README.md` index before proposing layering / DB / auth / deploy changes.
- New decisions: create ADR (`docs/adr/template.md`), merge, THEN implement.

## 9. Things agents get wrong here

<!-- Update whenever an agent makes the same mistake twice. Start empty. -->

- (none yet)

## 10. Workflow

1. Read `PROGRESS.md` (session orientation) then `TASK_STATE.md` §0 and current slice.
2. Read `CONVENTIONS.md` before editing code.
3. Use `MAP.md` for exploration; `agent_docs/` for deep-dive detail.
4. Use Context7 MCP for up-to-date library docs; don't rely on training data.

## 11. When ending a session

- Update `TASK_STATE.md` §6 (Handoff note).
- Update `PROGRESS.md` "Last session".
- Propose AGENTS.md updates for durable new facts — don't accumulate tribal
  knowledge in auto-memory.

## 12. Subdirectory AGENTS.md (precedence: nearest wins)

- `infra/AGENTS.md` — Terraform/Ansible specific (safe commands, forbidden ops)
- `app/<domain>/AGENTS.md` — domain-specific invariants

## 13. Composition with skills

This repo was bootstrapped with:
- `agentic-skeleton` (collaboration container — this file's shape — plus
  universal contracts: VIBE.yaml core schema, .env standard, /api/health
  contract, flat layout, line limits, Pushover)
- `lang-<stack>` (code-style patterns + stack-specific implementation
  of the contracts)

Add new durable rules to the RIGHT skill, not to this file. Transient context
goes in `TASK_STATE.md`; never here.
