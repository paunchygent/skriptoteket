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

- Existing tools relying on legacy behavior (`input_schema == null`) must remain unaffected.
- Editors may accidentally change `input_schema` from `null` to `[]` (behavior change); UX must make this explicit.

## Execution plan (suggested)

1) Add explicit “Input mode” selector in the editor and map it to `input_schema` representation.
2) Add schema helper actions: “Prettify JSON”, “Insert example”, “Reset”.
3) Ensure snapshot preview uses the resulting schema as-is (no “helpful” implicit conversions).

## Demo checklist

- Show switching `input_schema` mode between legacy/files-required and schema-driven.
- Show prettify + insert example for both schemas.
- Run a sandbox preview with each mode and verify behavior matches the selected mode.

## Verification checklist

- `pdm run docs-validate`
- `pdm run lint`
- `pdm run test`
- `pdm run fe-gen-api-types` (only if API types change)
- Live functional check (backend + SPA dev); record steps in `.agent/handoff.md` if UI behavior changes.

## Notes / follow-ups

- If this sprint surfaces ambiguous semantics, propose an ADR for a “Tool authoring schema UX contract”.
