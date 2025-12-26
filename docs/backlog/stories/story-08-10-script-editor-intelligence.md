---
type: story
id: ST-08-10
title: "Script editor intelligence Phase 1: Discoverability MVP"
status: done
owners: "agents"
created: 2025-12-24
epic: "EPIC-08"
acceptance_criteria:
  - "Given the editor loads, when typing 'from ', then Skriptoteket helpers appear in autocomplete (pdf_helper, tool_errors)"
  - "Given the user types 'from pdf_helper import ', then save_as_pdf appears in autocomplete"
  - "Given a script missing 'def run_tool', when linting runs, then a warning diagnostic appears in Swedish"
  - "Given run_tool has wrong signature (missing params), when linting runs, then a warning appears"
  - "Given the user hovers over 'save_as_pdf' or 'ToolUserError', then inline Swedish documentation tooltip appears"
ui_impact: "Adds in-editor code intelligence to help script authors discover available helpers."
data_impact: "None - client-side only."
dependencies: ["ST-11-12"]
---

## Context

Script authors need to discover Skriptoteket-specific helpers (`pdf_helper`, `tool_errors`) and follow the runner
contract. Currently, this information exists in the KB (`ref-ai-script-generation-kb.md`) but isn't surfaced in the
editor.

This is **Phase 1** of 3 phases implementing script editor intelligence. Phase 1 focuses on discoverability and can
ship independently.

## Technical Decisions

See [ADR-0035: Script editor intelligence architecture](../../adr/adr-0035-script-editor-intelligence-architecture.md)
for architecture decisions (Lezer-based analysis, extension composition, state sharing).

## Scope

### Import Completions

- Autocomplete `pdf_helper`, `tool_errors` on `from ` prefix
- Autocomplete `save_as_pdf` on `from pdf_helper import `
- Autocomplete `ToolUserError` on `from tool_errors import `
- Trigger completion automatically when typing `from ` (using `startCompletion`)
  - Gate auto-trigger so it does not run inside strings/comments

### Hover Documentation

- `pdf_helper.save_as_pdf(html, output_dir, filename) -> str`
  - Swedish: "Renderar HTML till PDF och sparar under output_dir så att filen blir en nedladdningsbar artefakt."
- `tool_errors.ToolUserError(message: str)`
  - Swedish: "Använd för fel som ska visas för användaren utan stacktrace."

### Entrypoint Lint Rules

| Rule ID | Severity | Swedish Message |
|---------|----------|-----------------|
| `ST_ENTRYPOINT_MISSING` | warning | Saknar startfunktion: `def run_tool(input_dir, output_dir)` |
| `ST_ENTRYPOINT_SIGNATURE` | warning | Startfunktionen ska ta emot `input_dir` och `output_dir`. |

Note: Entrypoint name is configurable per tool. Linting must use the currently configured entrypoint (default
`run_tool`).

## Technical Notes

### Extension Injection

Add `extensions?: Extension[]` prop to `CodeMirrorEditor.vue`:

```typescript
defineProps<{ modelValue: string; extensions?: Extension[] }>()
```

Implementation note: `extensions` must be applied via a CodeMirror `Compartment` and reconfigured on prop change (do not
destroy/recreate the editor).

NOTE: To keep Vite chunks under 500 kB, load the intelligence bundle via dynamic import and pass it into CodeMirror via
the `extensions` prop (see `useSkriptoteketIntelligenceExtensions.ts`).

### Detection Using Lezer

Use the Python syntax tree to find function definitions:

```typescript
// Collect all function defs: { name, params }
// Compare against configured entrypoint (default "run_tool")
// Validate first two params are "input_dir" and "output_dir"
```

## Files

### Create

- `frontend/apps/skriptoteket/src/composables/editor/skriptoteketIntelligence.ts`
- `frontend/apps/skriptoteket/src/composables/editor/skriptoteketCompletions.ts`
- `frontend/apps/skriptoteket/src/composables/editor/skriptoteketHover.ts`
- `frontend/apps/skriptoteket/src/composables/editor/skriptoteketLinter.ts`
- `frontend/apps/skriptoteket/src/composables/editor/skriptoteketMetadata.ts`
- `frontend/apps/skriptoteket/src/composables/editor/skriptoteketPythonTree.ts`
- `frontend/apps/skriptoteket/src/composables/editor/useSkriptoteketIntelligenceExtensions.ts`

### Modify

- `frontend/apps/skriptoteket/src/components/editor/CodeMirrorEditor.vue`
- `frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue`

## Follow-up Stories

- [ST-08-11: Phase 2 - Contract validation + security](story-08-11-script-editor-intelligence-phase2.md)
- [ST-08-12: Phase 3 - Best practices + polish](story-08-12-script-editor-intelligence-phase3.md)
