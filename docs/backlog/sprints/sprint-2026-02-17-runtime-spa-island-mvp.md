---
type: sprint
id: SPR-2026-02-17
title: "Sprint 2026-02-17: Runtime SPA island MVP"
status: done
owners: "agents"
created: 2025-12-19
starts: 2025-12-19
ends: 2025-12-21
objective: "Ship a runtime SPA island MVP that renders typed outputs/actions/state for end users and supports turn-taking."
prd: "PRD-script-hub-v0.2"
epics: ["EPIC-10"]
stories: ["ST-10-10"]
adrs: ["ADR-0022", "ADR-0024", "ADR-0025"]
---

## Objective

Deliver a runtime SPA island MVP that renders typed outputs, exposes action forms, and supports multi-turn interactions
for both runner-based tools and curated apps.

## Scope (committed stories)

- ST-10-10: Runtime SPA island MVP (end-user interactive tool UI)

## Out of scope

- Additional curated apps beyond the initial MVP
- Support for arbitrary tool-provided UI JavaScript (explicitly not supported)

## Risks / edge cases

- Concurrency: handle stale `expected_state_rev` cleanly in the UI.
- Replay: ensure the UI can re-render past runs via stored `ui_payload`.

## Demo checklist

- Render a run and submit at least one next action (turn-taking).
- Demonstrate state persistence across page reload.
- Show concurrency failure handling for stale state_rev.

## Verification checklist

- `pdm run docs-validate`
- `pdm run test` (or a targeted set of API + renderer tests)
