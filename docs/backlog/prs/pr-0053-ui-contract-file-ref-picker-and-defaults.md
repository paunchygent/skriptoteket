---
type: pr
id: PR-0053
title: "UI contract: file-ref picker + defaults + validation"
status: ready
owners: "agents"
created: 2026-01-24
updated: 2026-01-24
stories:
  - "ST-14-24"
tags: ["frontend", "api"]
acceptance_criteria:
  - "File-ref fields render a picker without exposing filesystem paths."
  - "Defaults (settings/action prefill) are preselected when available; missing defaults block execution with a validation error."
  - "Submitted file refs resolve to staged /work/input paths via the resolver pipeline."
---

## Problem

ST-14-24 requires first-class file references in the UI contract, including a picker, default preselects, and
validation when defaults are missing. Without this, tools must pass filenames manually and the UI leaks paths.

Parent: EPIC-14. Dependencies: ST-19-01/02/03, ST-14-19.

## Goal

Define and implement the UI contract for file-ref fields in run/action forms, including defaults and validation,
without adding parallel identifiers or path-based fallbacks.

## Non-goals

- User file vault persistence (ST-14-36).
- Runner contract changes beyond existing file-ref resolver pipeline.
- UI overhaul unrelated to file-ref selection.

## Implementation plan

- UI contract: add file-ref field kind in action schemas and form renderer.
- Picker UI: list available file refs via API, display labels only, no paths.
- Defaults: support settings/action prefill values; preselect when available; block execution with validation error if
  missing.
- Submission: include selected file refs in action inputs and run payloads; ensure resolver handles them.
- Tests: unit tests for form normalization + validation; update OpenAPI types if needed.
- Docs: update story/epic status when done, ensure no overlap in Playwright coverage.

## Test plan

- Frontend: `pdm run fe-test`
- Backend (if API changes): `pdm run test` or targeted tests
- Playwright: relevant picker/action flows (no overlap with sandbox file-refs reuse script)

## Rollback plan

- Revert commit; remove UI field kind and picker wiring; restore previous form rendering.
