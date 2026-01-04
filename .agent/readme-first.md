# Read Me First (Agents)

Use this file as the starting point when you begin a new session.

## Behavioral Rules (must follow)

- **No legacy support / workarounds**: do the full refactor; delete old paths instead of shims.
- **Preserve template structure**: when editing `.agent/handoff.md` or the next-session prompt template, keep headings and section order unchanged; only fill in content.
- **No secrets**: never include API keys/tokens, passwords, or personal data in `.agent/` or `docs/`.
- **Use the prompt template for new agents/devs**: if the user asks for a “message to a new developer/agent”, generate it by filling `.agent/next-session-instruction-prompt-template.md` (address the recipient as “you”).
- **Pre-commit required**: run `pdm run precommit-install` once, then `pdm run precommit-run` before pushing.
- **Admin editor features**: extract logic into `frontend/apps/skriptoteket/src/composables/editor/`
  (views stay UI-only).
- **Agent-doc size budgets**: keep `.agent/readme-first.md` ≤ 300 lines and `.agent/handoff.md` ≤ 200 lines (enforced by pre-commit).

## Pre-commit & quality gates (required)

- Install hooks: `pdm install -G monorepo-tools` then `pdm run precommit-install`
- Run before push: `pdm run precommit-run`
- Quick local gate: `pdm run lint` (Ruff + agent-doc budgets + docs contract)

## What this repo is

Skriptoteket is a teacher-first Script Hub: users log in, browse tools by profession/category, upload files, and receive results.
Auth is **local accounts + server-side sessions in PostgreSQL** (v0.1). Future HuleEdu SSO is planned via identity federation.

## Current sprint dashboard (keep current only)

- Sprint: `SPR-2026-01-05` (EPIC-14 editor sandbox vertical slice) — done (completed 2026-01-01)
- Focus: ST-14-03..08 (sandbox next_actions parity, preview snapshots, settings isolation, draft locks)
- Production: Full Vue SPA (SSR/HTMX removed)
- Done: EPIC-11 (SPA migration)
- Active: EPIC-14 admin tool authoring — `docs/backlog/epics/epic-14-admin-tool-authoring.md`
- Active: EPIC-16 catalog discovery — ST-16-08 pending

## Current EPIC-04 decisions (dynamic scripts)

- **Execution**: run scripts in hardened *sibling* Docker containers via `docker.sock` + Python Docker SDK (no host-path bind mounts; archive copy or scoped volumes for I/O). See `docs/adr/adr-0013-execution-ephemeral-docker.md`.
- **Storage**: hybrid: source + logs/HTML in DB; binary artifacts on disk with retention cleanup; production inputs not retained by default. See `docs/adr/adr-0012-script-source-storage.md`.
- **Versioning**: append-only; publish is copy-on-activate and archives the reviewed `in_review` version (publish “consumes” it). See `docs/adr/adr-0014-versioning-and-single-active.md`.
- **Governance**: Admins can publish script versions and tools; Superusers can rollback. “Published implies runnable” (requires `tools.active_version_id`). See `docs/reference/ref-dynamic-tool-scripts.md`.

## Read order (mandatory)

1. `docs/index.md` (PRD/ADRs/backlog entrypoint)
2. `.agent/rules/000-rule-index.md` (engineering rules and patterns)
3. `AGENTS.md` (repo contributor guide)
4. `doc_structure_requirements.md` (docs-contract governance)
5. `docs/prd/prd-spa-frontend-v0.1.md` (SPA migration PRD)
6. `docs/backlog/epics/epic-11-full-vue-spa-migration.md` (epic + story index)
7. `docs/backlog/sprints/sprint-2026-01-05-tool-editor-vertical-slice.md` (current sprint plan)

## Where to work

- Production code lives in `src/skriptoteket/` (DDD/Clean layers).
- `docs/` is contract-governed; do not add new top-level folders under `docs/` without updating the contract.

## Key commands

- Docs contract: `pdm run docs-validate`
- Format/lint/typecheck: `pdm run format` / `pdm run lint` / `pdm run typecheck`
- Tests: `pdm run test`
- DB (dev): `docker compose up -d db` then `pdm run db-upgrade`
- Bootstrap first superuser: `pdm run bootstrap-superuser`

## Dev Idioms (must follow)

### SPA Button Primitives
Use `btn-primary`/`btn-cta`/`btn-ghost` from `frontend/apps/skriptoteket/src/assets/main.css`. Never inline ad-hoc button styles.

### Editor Composables Pattern
Extract all editor logic to `frontend/apps/skriptoteket/src/composables/editor/`. Views stay UI-only:
- `useScriptEditor.ts` - main editor state (source, settings, usageInstructions, save)
- `useToolTaxonomy.ts` - profession/category editing
- `useToolMaintainers.ts` - maintainer management
- `useEditorWorkflowActions.ts` - submit/publish/rollback

### CodeMirror Intelligence (Editor)
Editor intelligence is lazily loaded via `frontend/apps/skriptoteket/src/composables/editor/useSkriptoteketIntelligenceExtensions.ts`
and assembled in `frontend/apps/skriptoteket/src/composables/editor/skriptoteketIntelligence.ts`.

- Keep `frontend/apps/skriptoteket/src/components/editor/CodeMirrorEditor.vue` generic (no feature keymaps).
- Linter entrypoints: `frontend/apps/skriptoteket/src/composables/editor/skriptoteketLinter.ts` and
  `frontend/apps/skriptoteket/src/composables/editor/skriptoteketLintPanel.ts`.
- References: `docs/reference/ref-linter-architecture.md`, `docs/reference/ref-codemirror-integration.md`,
  `docs/adr/adr-0048-linter-context-and-data-flow.md`.
- Playwright + CodeMirror patterns: `.agent/rules/075-browser-automation.md`.

### Runner Input Contract
Scripts receive inputs via environment variables (not CLI args):
- `SKRIPTOTEKET_INPUT_DIR` - directory containing uploaded files
- `SKRIPTOTEKET_INPUT_MANIFEST` - JSON manifest of input files
- `SKRIPTOTEKET_MEMORY_PATH` - path to `memory.json` (personalized settings)
- `SKRIPTOTEKET_OUTPUT_DIR` - write outputs here

### Key Architecture Patterns
- Sessions + optimistic concurrency (ADR-0024): `expected_state_rev` on actions
- Contract v2 (ADR-0022): outputs `notice|markdown|table|json|html_sandboxed`
- UI: Vue 3 + Vite + Tailwind 4 with `@theme` design tokens (ADR-0032)

## Session handoff

Before ending a session, update `.agent/handoff.md` with what changed, decisions, and next steps.

Completed stories belong in story docs + link index here (not in `.agent/handoff.md`):

### EPIC-11 (SPA Migration) - Complete
All stories ST-11-01..23 done. Cutover deployed 2025-12-23. See `docs/backlog/epics/epic-11-full-vue-spa-migration.md`.

### EPIC-02 (Identity) - Active (ST-02-02 pending)
Most EPIC-02 stories are complete (self-registration, profiles, lockout). ST-02-02 remains ready; see `docs/backlog/stories/story-02-02-admin-nomination-and-superuser-approval.md`.

### Older Stories
- ST-07-02: `docs/backlog/stories/story-07-02-healthz-and-metrics-endpoints.md`
- ST-07-04: `docs/backlog/stories/story-07-04-logging-redaction-and-policy.md`
- ST-05-12: `docs/backlog/stories/story-05-12-mobile-editor-ux.md`
- ST-04-04: `docs/backlog/stories/story-04-04-governance-audit-rollback.md`

### Recent context links (from handoff compression)
- EPIC-14 admin tool authoring: `docs/backlog/epics/epic-14-admin-tool-authoring.md`
- EPIC-08 AI editor features: `docs/backlog/epics/epic-08-contextual-help-and-onboarding.md`
- AI infra runbooks: `docs/runbooks/runbook-gpu-ai-workloads.md`, `docs/runbooks/runbook-tabby-codemirror.md`
- LLM ops note: `llama-server-hip` disabled; `llama-server-vulkan` enabled for A/B testing (see `.agent/handoff.md`).
- Ops runbooks: `docs/runbooks/runbook-home-server.md`, `docs/runbooks/runbook-observability.md`
