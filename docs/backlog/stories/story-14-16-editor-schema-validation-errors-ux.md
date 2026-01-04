---
type: story
id: ST-14-16
title: "Editor: structured schema validation errors UX"
status: done
owners: "agents"
created: 2025-12-29
updated: 2026-01-04
epic: "EPIC-14"
acceptance_criteria:
  - "Given the validation endpoint reports structured errors, when viewing schemas in the editor, then the UI renders them in a user-actionable format (what/where/how to fix)."
  - "Given the schema JSON is parseable but fails backend validation, when attempting to save or run sandbox, then the editor blocks the action and points to the validation errors."
  - "Given validation is expensive, then the UI throttles calls (no per-keystroke spam)."
dependencies:
  - "ST-14-15"
ui_impact: "Yes"
data_impact: "No"
---

## Notes

Scope: ST-14-16 covers backend validation errors for parseable JSON. JSON parse errors are handled by the schema editor
(ST-14-13/14) and should block actions without calling the validation endpoint.

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`

## Decisions (locked in)

- The backend validation endpoint returns `200 OK` with `{ valid, issues[] }` (no `DomainError`/422 for invalid schemas).
- UI calls the endpoint only when JSON is parseable (parse errors short-circuit locally).
- UI calls are throttled/debounced and also triggered explicitly on blocking actions (Save / Run sandbox).
- Backend issues are displayed per schema editor (`settings_schema` vs `input_schema`) with clear location (`path`) and fix guidance.

## Implementation Plan

- Types:
  - Regenerate OpenAPI TS types after backend is merged: `pdm run fe-gen-api-types`.
- State/composable:
  - Add a dedicated composable (e.g. `useEditorSchemaValidation`) that:
    - accepts the current parsed schema values + parse error state + tool id
    - debounces validation calls (no per-keystroke spam)
    - exposes `issuesBySchema`, `hasBlockingIssues`, and `validateNow()`
    - avoids calling the endpoint when the editor is read-only (no lock) unless we explicitly need read-only diagnostics.
- Blocking rules:
  - Save: block in the editor save flow and surface `issues[]` before sending `/save` or `/draft`.
  - Sandbox run: block in sandbox runner before `run-sandbox`/`start-action` calls.
- Rendering:
  - Show backend issues under each schema editor (separate from JSON parse errors) and keep messages short and actionable.
  - Prefer a small list grouped by schema; include `path` when present.
- Verification (planned):
  - `pdm run fe-test`
  - `pdm run fe-type-check`
  - Manual: set parseable-but-invalid schema → issues render + save/run blocked; fix schema → issues clear + actions succeed.
