---
type: sprint
id: SPR-2026-01-20
title: "Sprint 2026-01-20: SSR typed UI rendering"
status: done
owners: "agents"
created: 2025-12-19
starts: 2026-01-20
ends: 2026-02-02
objective: "Render stored typed ui_payload outputs/actions in SSR pages to enable incremental rollout without requiring SPA islands."
prd: "PRD-script-hub-v0.2"
epics: ["EPIC-10"]
stories: ["ST-10-07"]
adrs: ["ADR-0022", "ADR-0024"]
---

## Objective

Make the default SSR UI capable of rendering typed outputs and next actions from stored `ui_payload`, so interactive
tools can ship without blocking on SPA islands.

## Scope (committed stories)

- ST-10-07: SSR rendering for typed outputs/actions

## Out of scope

- Editor SPA island work
- Runtime SPA island work

## Risks / edge cases

- Rendering safety: keep `html_sandboxed` strictly sandboxed.
- UX fragmentation: keep SSR renderer aligned with the SPA renderer component model.

## Demo checklist

- Render at least 2 output kinds (e.g. markdown + table) from stored `ui_payload`.
- Render an action form and show it triggers a new run (via start_action).

## Verification checklist

- `pdm run docs-validate`
- `pdm run test` (SSR rendering helpers + output component tests if present)
