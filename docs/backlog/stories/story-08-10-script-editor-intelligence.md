---
type: story
id: ST-08-10
title: "Script editor intelligence (CodeMirror 6 linting and suggestions)"
status: ready
owners: "agents"
created: 2025-12-24
epic: "EPIC-08"
acceptance_criteria:
  - "Given the editor loads, when typing 'from ', then Skriptoteket helpers appear in autocomplete (pdf_helper, tool_errors)"
  - "Given a script missing 'def run_tool', when linting runs, then a warning diagnostic appears"
  - "Given a script uses 'requests' or 'subprocess', when linting runs, then a security warning appears"
  - "Given a script returns a dict missing 'outputs', when linting runs, then an info diagnostic appears"
  - "Given the user hovers over 'save_as_pdf' or 'ToolUserError', then inline documentation tooltip appears"
ui_impact: "Adds in-editor code intelligence to help script authors discover available helpers and catch common errors."
data_impact: "None - client-side only."
dependencies: ["ST-11-12"]
---

## Context

Script authors need to discover Skriptoteket-specific helpers (pdf_helper, tool_errors) and follow the runner contract.
Currently, this information exists in the KB (ref-ai-script-generation-kb.md) but isn't surfaced in the editor.

## Scope

- Custom autocompletions for Skriptoteket imports and contract v2 keys
- Lint diagnostics:
  - Entrypoint rules (missing/wrong signature)
  - Contract validation (outputs structure, kind values, notice fields)
  - Security warnings (network APIs, subprocess)
  - Best practices (encoding, use pdf_helper, mkdir before write)
- Hover tooltips with inline documentation for helper functions

## Technical Notes

Uses CodeMirror 6 extension APIs:

- `@codemirror/autocomplete` for completion sources
- `@codemirror/lint` for diagnostic callbacks
- `@codemirror/view` (Tooltip) for hover docs

## Lint Rules

### Entrypoint rules

- Missing `def run_tool` (warning)
- Wrong signature (missing `input_path` or `output_dir` params) (warning)

### Contract validation

- Return dict missing `outputs`, `next_actions`, or `state` (info)
- `outputs` not a list (error)
- Output dict missing `kind` key (warning)
- Invalid `kind` value (warning)
- `notice` missing `level` or `message` (warning)
- `level` not one of `info`, `warning`, `error` (warning)

### Security warnings

- Using `requests`, `urllib`, `httpx`, `aiohttp` (blocked by `--network none`) (error)
- Using `subprocess`, `os.system`, `os.popen` (sandboxed) (warning)
- Writing outside `output_dir` (warning)

### Best practices

- `raise ToolUserError` without import (error)
- Missing `encoding` param in `open()`, `read_text()`, `write_text()` (info)
- Using `weasyprint.HTML` directly instead of `pdf_helper.save_as_pdf` (info)
- Missing `Path(output_dir).mkdir(parents=True, exist_ok=True)` before writing (info)

## Files

- `frontend/apps/skriptoteket/src/composables/editor/skriptoteketCompletions.ts`
- `frontend/apps/skriptoteket/src/composables/editor/skriptoteketLinter.ts`
- `frontend/apps/skriptoteket/src/composables/editor/skriptoteketHover.ts`
- `frontend/apps/skriptoteket/src/components/editor/CodeMirrorEditor.vue`
