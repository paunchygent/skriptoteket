---
type: pr
id: PR-0065
title: "Conversion Hub: SPA bespoke UI (batch + preview + pdf_layout controls)"
status: ready
owners: "agents"
created: 2026-03-01
updated: 2026-03-01
stories:
  - "ST-21-01"
tags: ["frontend", "curated-apps", "ux"]
acceptance_criteria:
  - "Given a user opens `/apps/:appId`, when the app is Conversion Hub, then the bespoke view renders and supports selecting a conversion route supported by Sir Convert-a-Lot v2."
  - "Given the user uploads N files and runs batch conversion, when results return, then the UI shows per-file status and provides artifact download links."
  - "Given a PDF output is selected, when the user changes paper size and orientation, then those map to v2 `conversion.pdf_layout` and are reflected in results."
  - "Given a failure occurs, when the job reaches terminal failure, then the UI renders a stable error summary (including correlation id) and provides an easy rerun action."
---

## Problem

We need a first-class UI that replaces the `html-to-pdf-preview` tool-run view and provides a complete conversion
interface backed by Sir Convert-a-Lot v2.

## Goal

- Add a bespoke Conversion Hub view integrated with the curated apps host.
- Provide batch + preview UX aligned to v2 job semantics.
- Keep UI deterministic and typed via OpenAPI TS types.

## Non-goals

- No E2E test migration in this PR (PR-0066).

## Implementation plan

- [ ] Add bespoke view component under `frontend/apps/skriptoteket/src/views/apps/` and register it in
  `frontend/apps/skriptoteket/src/views/AppHostView.vue`.
- [ ] Add composable(s) for conversion hub state + API calls (pattern: app-specific composables, no logic in views).
- [ ] Add UI primitives:
  - conversion route selector (route list is sourced from backend contract),
  - file picker (multi-file),
  - pdf_layout selector (paper size + orientation; default sensible),
  - per-file result table with download actions,
  - progress/error panel per job.
- [ ] Regenerate OpenAPI types: `pdm run fe-gen-api-types`.
- [ ] Add Vitest coverage for core state machine (batch submission + polling loop integration via mocked API).

## Test plan

- `pdm run fe-gen-api-types`
- `pdm run fe-type-check`
- `pdm run fe-test`

## Rollback plan

- Remove the bespoke view mapping and leave the app hidden from catalog placements until stable.
