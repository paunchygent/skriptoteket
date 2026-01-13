---
type: sprint
id: SPR-2026-03-31
title: "Sprint 2026-03-31: Tool editor schema editor v1"
status: done
owners: "agents"
created: 2025-12-29
updated: 2026-01-12
starts: 2026-03-31
ends: 2026-04-13
objective: "Replace schema textareas with a JSON-aware editor experience (CodeMirror) to reduce schema authoring errors."
prd: "PRD-editor-sandbox-v0.1"
epics: ["EPIC-14"]
stories: ["ST-14-13", "ST-14-14"]
---

## Objective

Make authoring `settings_schema` and `input_schema` substantially safer and faster via a JSON-aware editor.

Reference context: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`

## Scope (committed stories)

- [ST-14-13: CodeMirror JSON editor for tool schemas](../stories/story-14-13-editor-schema-editor-json-codemirror.md)
- [ST-14-14: Schema editor snippets + inline diagnostics UX](../stories/story-14-14-editor-schema-editor-snippets-and-diagnostics.md)

## Out of scope

- Backend schema validation endpoint (planned next sprint).
- Schema “v2” extensions (defaults/required/help/min/max/placeholder).

## Decisions required (ADRs)

- None expected (frontend-only), unless we decide to standardize schema examples/snippets centrally.

## Risks / edge cases

- Large schemas: ensure the editor stays responsive.
- Ensure schema editor still supports copy/paste and raw editing (no forced wizards).

## Demo checklist

- Show JSON editor for both schemas with syntax highlighting and parse errors.
- Insert snippets and run sandbox preview using the unsaved schema.

## Verification checklist

- `pdm run docs-validate`
- `pdm run lint`
- `pdm run test`
- Live functional check (backend + SPA dev); record steps in `.agent/handoff.md`.
