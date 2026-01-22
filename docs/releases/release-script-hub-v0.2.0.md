---
type: release
id: REL-script-hub-v0.2.0
title: "Script Hub v0.2.0 release notes (SPA + interactive tools)"
status: draft
owners: "agents"
created: 2026-01-22
product: "script-hub"
version: "0.2.0"
links:
  - "PRD-script-hub-v0.2"
  - "EPIC-10"
  - "EPIC-11"
  - "EPIC-14"
  - "EPIC-18"
  - "EPIC-08"
---

## Summary

v0.2.0 is the first **SPA-first** release of Skriptoteket / Script Hub. It ships a full Vue/Vite UI backed by a FastAPI
API (`/api/v1`) and upgrades the tool/runtime boundary to a **typed UI contract (v2)** with persisted UI payloads and
session state, enabling safe multi-turn tools.

## Highlights

- Full Vue 3 + Vite SPA for all roles (user/contributor/admin/superuser).
- Tool UI contract v2: typed `outputs[]`, optional `next_actions[]`, and persisted `state` with optimistic concurrency.
- Curated apps: owner-authored “apps” served in the catalog without going through the tool editor workflow.
- Queue-backed execution: Postgres-backed execution queue + worker loop for durable tool runs.
- Editor sandbox: schema validation UX, diff/compare, snapshots, debug panel, and draft-head locks.
- Optional editor AI: inline completions (ghost text).
- Optional editor AI: streaming editor chat (SSE).
- Optional editor AI: chat-first edit-ops with diff preview/apply/undo.

## Changes

### Added

- Typed UI rendering primitives and deterministic payload normalization (contract v2).
- Execution worker service for queue-backed runs.
- Editor AI suite (optional): completions, streaming chat, and edit-ops.
- OpenAI Responses API support (for GPT-5 family) with prompt caching guidance (runbook).
- New codemaps for runner execution flow, editor AI API surfaces, and observability correlation tracing.

### Changed

- UI paradigm is a full SPA (legacy SSR/HTMX is removed).
- Runner/app contract is enforced as v2 (`contract_version: 2`) at the boundary.

### Fixed

- Responses structured output shape validation to avoid upstream 400s (Chat vs Responses schema shape separation).

## Compatibility / Upgrade notes

- DB schema is managed via Alembic migrations; upgrade with `pdm run db-upgrade`.
- Tool execution stores artifacts/session files/snapshots under `ARTIFACTS_ROOT`.
- Queue-backed runs are enabled by default; ensure the execution worker is running (`pdm run run-execution-worker`).

## Known issues / limitations

- Runner contract v3 (request envelope + first-class file references) is planned but not yet cut over (EPIC-19).
- User file vault + file-reference pickers depend on EPIC-19 and are not shipped yet (ST-14-24 / ST-14-36).

## Links

- PRD: `docs/prd/prd-script-hub-v0.2.md`
- ADRs: `docs/adr/adr-0027-full-vue-vite-spa.md`, `docs/adr/adr-0022-tool-ui-contract-v2.md`,
  `docs/adr/adr-0062-execution-queue-and-worker-loop.md`
- Epics: `docs/backlog/epics/epic-10-interactive-ui-contract-and-curated-apps.md`,
  `docs/backlog/epics/epic-11-full-vue-spa-migration.md`, `docs/backlog/epics/epic-14-admin-tool-authoring.md`,
  `docs/backlog/epics/epic-18-execution-queue-and-worker-loop.md`, `docs/backlog/epics/epic-08-contextual-help-and-onboarding.md`
- Runbooks: `docs/runbooks/runbook-editor-ai-pipeline.md`, `docs/runbooks/runbook-openai-responses-api.md`
- Codemap: `docs/reference/reports/codemaps/ai-api-surfaces-tool-editor.md`
