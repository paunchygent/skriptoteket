# Skriptoteket Agent Entrypoint

Skriptoteket is a teacher-first Script Hub with a FastAPI/PostgreSQL backend and
a Vue/Vite SPA. HuleEdu owns the shared browser-session login ceremony and
identity context; Skriptoteket keeps roles local. Curated apps are first-class
application modules with bespoke UX and app-specific APIs.

Target Python is 3.13-3.14.

## Non-Negotiables

- Use skills before planning or implementation. Start with the global skill
  registry, then use repo-owned skills under `.codex/skills/` when they are
  specifically relevant.
- Use docs-as-code for planning and structural changes. Start at `docs/index.md`,
  use the templates in `docs/templates/`, and close doc changes with
  `pdm run docs-validate`.
- Follow `.codex/rules/000-rule-index.md` for targeted repo rules. Do not
  bulk-load the rules directory.
- Do not revert or restore changes you did not make without explicit approval.
- Keep domain pure, web/api thin, and infrastructure behind protocols. Depend on
  `typing.Protocol`; Unit of Work owns commit/rollback; repositories never
  commit; map `DomainError` to HTTP only at the web boundary.
- Keep files small: production and test modules should stay under roughly
  400-500 lines.
- For UI or route changes, run a live functional check and record the exact
  verification in `.codex/handoff.md`.
- Authenticated browser proof must use the HuleEdu browser-session ceremony and
  repo helpers/preflight. Never derive auth proof from prior shell snippets,
  direct product-backend credential POSTs, or local session-cookie shortcuts.
- Git workflow is merge-only: never rebase, amend, force-push, or hide conflict
  resolution in history.
- Never commit secrets. Use environment variables and local `.env` files.
- Use BuildKit for Docker builds; do not use plain `docker build`.

## Session Start

1. Read this file.
1. Check `.codex/handoff.md` only for volatile current-state pointers.
1. Select the task-relevant skill before planning or implementation.
1. Load `.codex/rules/000-rule-index.md` only when repo rules are needed, then
   open the specific rule files the task requires.
1. Use `docs/index.md` for durable docs discovery and backlog context.

## Skill Router

| Task | Start Here |
|---|---|
| Docs-as-code, backlog contracts, scaffolding, governed docs | `agent-docs-governance` |
| Planning, decomposition, tranche sequencing | `agent-planning` |
| Next-session or developer handoff messages | `agent-session-handoff` |
| Backend architecture, DDD/Clean boundaries, FastAPI, UoW, migrations, runner contracts | `.codex/skills/skriptoteket-backend-dev/SKILL.md` |
| Local dev, DB setup, dev stack, command wrappers, local logs | `local-devops` plus its Skriptoteket reference |
| Hemma deploys, remote operations, shared host runtime, GPU/offload lanes | `hemma-devops` plus its Skriptoteket reference |
| SPA, curated-app UI, auth continuation, dense workspaces, frontend tests | `integrated-frontend-stack` plus its Skriptoteket reference |
| Flunk-Out Frenzy pinball playfield geometry, donor table semantics, board underlays, physics-wall carriers | `.codex/skills/pinball-board-authoring/SKILL.md` |
| Visual direction, brutalist/academic UI, design resources | `brutalist-academic-ui` |
| Logs, metrics, traces, dashboards, public-edge logging policy | `observability-stack` plus its Skriptoteket reference |
| Browser automation, screenshots, Playwright proof | `playwright-testing` |
| PDM metadata migration | `pdm-migration-specialist`, explicit use only |
| Hook authoring or hook policy | hooks skill, explicit use only |
| Repomix packages for outside review | shared/global repomix skill |

Shared skills migrated to
`/Users/olofs_mba/Documents/Repos/skill-repository/skills/` are authored there
first. Repo facts belong in shared-skill references or leaves, not in copied
repo-local skills.

- For any skill creation or update, use the system `skill-creator` skill first.
  Keep `SKILL.md` concise; route examples, patterns, rationale, and behavior
  detail into the reference/resource structure recommended there.

## Agent Surface

- `.codex/agents/`: Codex subagents, explicit delegation only.
- `.codex/skills/`: truly Skriptoteket-specific skills only.
- `.codex/rules/`: targeted repo rules.
- `.codex/handoff.md`: volatile current-state handoff; keep it under 200 lines.
- `.codex/long-term-memory/index.md`: durable session-history doorway.
- `.codex/long-term-memory/entries/`: retained session-history entries.
- `CLAUDE.md`: Claude specialist memory only.

When compacting `.codex/handoff.md`, move durable session history to
`.codex/long-term-memory/entries/` first. Promote policy, procedure,
acceptance criteria, and implementation doctrine to governed docs instead of
burying them in handoff or long-term memory.

## Durable Docs

- Contract: `docs/_meta/docs-contract.yaml`
- Start-here index: `docs/index.md`
- Templates: `docs/templates/`
- Review workflow: `docs/reference/ref-review-workflow.md`
- Runbooks: `docs/runbooks/`
- Backlog hierarchy: `EPIC -> STORY -> PR backlog slice`

When a story, epic, PR, or review status/scope changes, update the relevant
backlog doc and `.codex/handoff.md`. When a story is marked `done`, also update
its epic with the current implementation summary. Proposed EPICs and ADRs need
review before implementation.

## Command Policy

Run commands from the repository root and prefer named `pdm run ...` scripts.
Do not invent ad hoc command strings when a script exists.

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
and normal implementation work routed through this file, skills, rules, runbooks,
and docs-as-code.
