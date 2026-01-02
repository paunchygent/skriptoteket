---
type: sprint
id: SPR-2026-03-03
title: "Sprint 2026-03-03: Tool editor DX quick wins"
status: planned
owners: "agents"
created: 2025-12-29
updated: 2026-01-02
starts: 2026-03-03
ends: 2026-03-16
objective: "Reduce high-frequency authoring footguns in the tool editor (schema JSON QoL)."
prd: "PRD-editor-sandbox-v0.1"
epics: ["EPIC-14"]
stories: ["ST-14-10"]
---

## Objective

Ship small, high-leverage UX/DX improvements for tool authors that reduce common mistakes and iteration time.

Reference context: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`

## Before / After

**Before**

- Authors get late feedback and spend time on avoidable JSON formatting/boilerplate.

**After**

- Authors can quickly format and insert minimal valid examples for schemas, reducing setup friction.

## Scope (committed stories)

- [ST-14-10: Editor schema JSON QoL (prettify + examples + guidance)](../stories/story-14-10-editor-schema-json-qol.md)

## Out of scope

- CodeMirror-based JSON schema editor (planned later).
- Backend schema validation endpoint (planned later).
- Review diff/compare workflow (planned later).

## Decisions required (ADRs)

- None expected (UI-only changes), unless the team decides to formalize `input_schema` mode semantics.

## Risks / edge cases

- File schema constraints must remain consistent with server upload limits (`UPLOAD_MAX_FILES`).

## Execution plan (suggested)

### Update (2026-01-02)

ST-14-09 shipped early (schema-only `input_schema`, no legacy `null` semantics). This sprint now focuses on ST-14-10.

## Pacing checklist (suggested)

- [ ] Add schema helper actions: “Prettify JSON”, “Insert example”, “Reset”.
- [ ] Ensure snapshot preview uses the resulting schema as-is (no implicit conversions).

## Demo checklist

- Show prettify + insert example for both schemas.
- Run a sandbox preview using the inserted example schema and verify the behavior matches the schema.

## Verification checklist

- `pdm run docs-validate`
- `pdm run lint`
- `pdm run test`
- `pdm run fe-gen-api-types` (only if API types change)
- Live functional check (backend + SPA dev); record steps in `.agent/handoff.md` if UI behavior changes.

## Notes / follow-ups

- If this sprint surfaces ambiguous semantics, propose an ADR for a “Tool authoring schema UX contract”.
