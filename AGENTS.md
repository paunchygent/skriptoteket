# Skriptoteket Agent Entrypoint

Skriptoteket is a teacher-first Script Hub with a FastAPI/PostgreSQL backend and
a Vue/Vite SPA. HuleEdu owns shared browser-session login and identity context;
Skriptoteket keeps roles local. Curated apps are first-class application modules
with bespoke UX and app-specific APIs. Target Python is 3.13-3.14.

## Repo Invariants

- Use docs-as-code for planning and structural changes. Start at `docs/index.md`,
  use the package-owned `pdm run new-*` scaffolders, and close doc changes with
  `pdm run docs-validate`.
- Follow `.codex/rules/000-rule-index.md` for targeted repo rules.
- Unit of Work owns commit/rollback; repositories never commit; map
  `DomainError` to HTTP only at the web boundary.
- For UI or route changes, run a live functional check and record exact
  verification in `handoff.md`.
- Authenticated browser proof must use the HuleEdu browser-session ceremony and
  repo helpers/preflight. Never derive auth proof from prior shell snippets,
  direct product-backend credential POSTs, or local session-cookie shortcuts.

## Session Start

1. Check `handoff.md` for current-state pointers.
2. Load `.codex/rules/000-rule-index.md` only when repo rules are needed, then
   open the specific rule files the task requires.
3. Use `docs/index.md` for durable docs discovery and backlog context.

## Repo-Specific Routes

Keep routes here only when they add Skriptoteket references, local skills,
product workflow, or command-wrapper context.

| Context                                                                                                    | Repo-Specific Route                                                                                                   |
| ---------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Repository topology, layer boundaries, where a concern lives                                               | `.codex/skills/repo-code-map/SKILL.md`                                                                                |
| Docs-as-code, backlog contracts, scaffolding, governed docs                                                | `agent-docs-governance` plus its Skriptoteket reference                                                               |
| Planning, decomposition, tranche sequencing                                                                | `agent-planning` plus its Skriptoteket reference                                                                      |
| Next-session or developer handoff messages                                                                 | `agent-session-handoff` plus its Skriptoteket reference                                                               |
| Backend architecture, FastAPI, UoW, migrations, runner contracts                                           | `.codex/skills/skriptoteket-backend-dev/SKILL.md`                                                                     |
| Testing strategy, test implementation, test repair, or test-quality audits                                 | `testing` plus `.codex/skills/skriptoteket-testing/SKILL.md` when repo-specific fixtures, migrations, or gates matter |
| Local dev, DB setup, dev stack, command wrappers, local logs                                               | `local-devops` plus its Skriptoteket reference                                                                        |
| Hemma deploys, remote operations, shared host runtime, GPU/offload lanes                                   | `hemma-devops` plus its Skriptoteket reference                                                                        |
| SPA, curated-app UI, auth continuation, dense workspaces, frontend tests                                   | `integrated-frontend-stack` plus its Skriptoteket reference                                                           |
| Flunk-Out Frenzy pinball playfield geometry, donor table semantics, board underlays, physics-wall carriers | `.codex/skills/pinball-board-authoring/SKILL.md`                                                                      |
| Logs, metrics, traces, dashboards, public-edge logging policy                                              | `observability-stack` plus its Skriptoteket reference                                                                 |

Shared skills are authored in the canonical skill repository reached through
the harness alias. Repo facts belong in shared-skill references or leaves, not
copied repo-local skills.

## Agent Surface

- `.codex/agents/`: Codex subagents, explicit delegation only.
- `.codex/skills/`: truly Skriptoteket-specific skills only.
- `.codex/rules/`: targeted repo rules.
- `handoff.md`: current-state handoff; keep it under 200 lines.
- `.codex/long-term-memory/index.md`: durable session-history doorway.
- `.codex/long-term-memory/entries/`: retained session-history entries.
- `CLAUDE.md`: Claude specialist memory only.

When compacting `handoff.md`, move durable session history to
`.codex/long-term-memory/entries/` first.

## Durable Docs

- Current contract and scaffolds: package-owned `repository-governance`
- Start-here index: `docs/index.md`
- Historical-only legacy contract: `docs/_meta/historical-docs-contract.yaml`
- Runbooks: `docs/runbooks/`
- Backlog hierarchy: `EPIC -> STORY -> TASK`

When a story, epic, PR, or review status/scope changes, update the relevant
backlog doc and `handoff.md`. When a story is marked `done`, also update
its epic with the current implementation summary. Proposed EPICs and ADRs need
review before implementation.

## Authority Transition Guard

Terminal docs authority changes must cite `agent-planning:user-closure-gate` or
`agent-overseer:approved-review-closeout`. Review verdict
approval is reviewer-owned. Details live in `agent-docs-governance`.

## Command Policy

Default close-out:

- Docs-only change: `pdm run docs-validate`
- Skill-surface change: `pdm run skills-validate` and `pdm run docs-validate`
- Handoff update: `pdm run handoff-validate` and `pdm run docs-validate`
- Backend change: `pdm run lint`, `pdm run typecheck`, and focused tests
- Frontend change: use `integrated-frontend-stack` for the focused
  Vitest/typecheck/build/browser proof

Long-running dev services such as `pdm run dev`, `pdm run fe-dev`, and
`docker compose up -d db` should not be stopped unless the user asks.

## Claude Boundary

`CLAUDE.md` is not a second implementation handbook. It is a narrow specialist
file for Claude UI layout/design review and idiomatic Swedish copy. Keep Codex
and engineering work routed through this file, skills, rules, runbooks, and
docs-as-code.
