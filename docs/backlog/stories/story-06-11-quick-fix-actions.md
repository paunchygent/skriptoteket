---
type: story
id: ST-06-11
title: "Editor quick fixes (CodeMirror diagnostic actions)"
status: done
owners: "agents"
created: 2025-12-29
epic: "EPIC-06"
acceptance_criteria:
  - "Given a diagnostic supports a quick fix, when the user activates the action, then the code change is applied safely and idempotently"
  - "Given ToolUserError is used without import, when the user selects \"Lägg till import\", then `from tool_errors import ToolUserError` is inserted at a safe import position"
  - "Given an encoding diagnostic is shown for text IO, when the user selects \"Lägg till encoding\", then `encoding=\"utf-8\"` is added to the relevant call without breaking existing args"
  - "Given the entrypoint is missing, when the user selects \"Skapa startfunktion\", then a `def run_tool(input_dir, output_dir):` stub is inserted in a reasonable location"
  - "Given contract keys are missing in a literal return dict, when the user selects \"Lägg till nycklar\", then the missing keys are inserted into the dict"
ui_impact: "Adds IDE-like \"Quick Fix\" buttons in diagnostics tooltip and lint panel."
dependencies: ["ST-06-10", "docs/reference/ref-codemirror-integration.md"]
---

## Context

VS Code-style workflows rely on quick fixes to reduce friction and prevent repetitive mistakes.

CodeMirror supports this through `Diagnostic.actions` (buttons in tooltips and the lint panel).

## Scope

- Add quick-fix actions for agreed diagnostics by attaching `FixIntent[]` to `DomainDiagnostic.fixes`
  (domain stays CodeMirror-free; adapter maps to `Diagnostic.actions`):
  - `ST_BESTPRACTICE_TOOLUSERERROR_IMPORT` → insert missing import
  - `ST_BESTPRACTICE_ENCODING` → add `encoding="utf-8"`
  - `ST_ENTRYPOINT_MISSING` → insert entrypoint stub
  - `ST_CONTRACT_KEYS_MISSING` → insert missing Contract v2 keys
- Add `findImportInsertPosition(text)` helper:
  - inserts after shebang + encoding cookie, module docstring, and `from __future__` imports
  - inserts into/after existing top-of-file import block when present
- Add `argListFrom/argListTo` (paren positions) to call-expression facts so the encoding fix can be inserted
  deterministically (comma/no-comma) and idempotently.

## Files

### Create

- `frontend/apps/skriptoteket/src/composables/editor/linter/domain/utils/pythonImports.ts`

### Modify

- `frontend/apps/skriptoteket/src/composables/editor/linter/adapters/codemirror/skriptoteketLinterAdapter.ts`
- `frontend/apps/skriptoteket/src/composables/editor/linter/domain/pythonFacts.ts`
- `frontend/apps/skriptoteket/src/composables/editor/linter/infra/pythonAnalysis.ts`
- `frontend/apps/skriptoteket/src/composables/editor/linter/domain/rules/bestPracticesRule.ts`
- `frontend/apps/skriptoteket/src/composables/editor/linter/domain/rules/entrypointRule.ts`
- `frontend/apps/skriptoteket/src/composables/editor/linter/domain/rules/contractRule.ts`
