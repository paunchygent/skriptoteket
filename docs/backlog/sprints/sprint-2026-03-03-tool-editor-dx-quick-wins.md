---
type: sprint
id: SPR-2026-03-03
title: "Sprint 2026-03-03: Tool editor DX quick wins"
status: planned
owners: "agents"
created: 2025-12-29
starts: 2026-03-03
ends: 2026-03-16
objective: "Reduce high-frequency authoring footguns in the tool editor (schema modes + JSON QoL)."
prd: "PRD-editor-sandbox-v0.1"
epics: ["EPIC-14"]
stories: ["ST-14-09", "ST-14-10"]
---

## Objective

Ship small, high-leverage UX/DX improvements for tool authors that reduce common mistakes and iteration time.

Reference context: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`

## Before / After

**Before**

- `input_schema: null` vs `input_schema: []` semantics are easy to accidentally change via an empty textarea.
- Authors get late feedback and spend time on avoidable JSON formatting/boilerplate.

**After**

- Authors explicitly choose an input preset (no inputs vs optional files vs required files), and the UI makes the
  runtime behavior predictable (schema-driven only).
- Authors can quickly format and insert minimal valid examples for schemas, reducing setup friction.

## Scope (committed stories)

- [ST-14-09: Editor input_schema modes (remove null vs [] footgun)](../stories/story-14-09-editor-input-schema-modes.md)
- [ST-14-10: Editor schema JSON QoL (prettify + examples + guidance)](../stories/story-14-10-editor-schema-json-qol.md)

## Out of scope

- CodeMirror-based JSON schema editor (planned later).
- Backend schema validation endpoint (planned later).
- Review diff/compare workflow (planned later).

## Decisions required (ADRs)

- None expected (UI-only changes), unless the team decides to formalize `input_schema` mode semantics.

## Risks / edge cases

- Script bank migration must preserve current runtime behavior by rewriting legacy tool versions to the schema-driven
  file representation (i.e. update stored `input_schema` data; no long-lived legacy code paths in runtime/UI).
- File schema constraints must remain consistent with server upload limits (`UPLOAD_MAX_FILES`).

## Execution plan (suggested)

## Pacing checklist (suggested)

- [ ] Add explicit “Input preset” selector and map it to schema representation (`[]` or `file` field with min/max).
- [ ] Add schema helper actions: “Prettify JSON”, “Insert example”, “Reset”.
- [ ] Ensure snapshot preview uses the resulting schema as-is (no implicit conversions).

## Demo checklist

- Show switching `input_schema` preset between no inputs / optional files / required files.
- Show prettify + insert example for both schemas.
- Run a sandbox preview with each preset and verify behavior matches the selected preset.

## Verification checklist

- `pdm run docs-validate`
- `pdm run lint`
- `pdm run test`
- `pdm run fe-gen-api-types` (only if API types change)
- Live functional check (backend + SPA dev); record steps in `.agent/handoff.md` if UI behavior changes.

## Notes / follow-ups

- If this sprint surfaces ambiguous semantics, propose an ADR for a “Tool authoring schema UX contract”.
