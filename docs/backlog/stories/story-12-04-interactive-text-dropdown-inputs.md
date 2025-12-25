---
type: story
id: ST-12-04
title: "Interactive text/dropdown inputs"
status: ready
owners: "agents"
created: 2025-12-21
epic: "EPIC-12"
acceptance_criteria:
  - "Given a tool declares input_schema with text/dropdown fields, when user opens run view, then SPA renders form before execution"
  - "Given a tool declares input_schema with file field, when user opens run view, then SPA renders file upload widget with accept/min/max constraints"
  - "Given inputs are invalid, when submitting, then user sees validation error and runner is not invoked"
  - "Given input_schema exists, when tool runs, then script receives form values via SKRIPTOTEKET_INPUTS env var"
  - "Given no input_schema, when user opens run view, then legacy single-file upload behavior applies"
ui_impact: "Reduces friction by allowing form-based inputs; file upload becomes optional for tools that don't need files."
data_impact: "Adds input_schema JSONB column to tool_versions; adds structured input values to ToolRun metadata."
dependencies: ["ST-11-13"]
---

## Context

Many tools need only a few parameters (text, dropdowns) rather than a file upload. Supporting this expands tool
usability and reduces "upload a dummy file" workarounds.

## Status

This story was blocked until EPIC-11 cutover (ST-11-13). EPIC-11 is complete as of **2025-12-23**; implement form UI
directly in the SPA (no SSR duplication).

## Design Decision

**Explicit input declaration** in tool metadata (like GitHub Actions, VS Code tasks):

- Tool author declares ALL input requirements upfront in unified `input_schema`
- UI renders form before execution based on schema
- File fields render as upload widgets, text/enum fields render as form inputs

## Architecture

**Unified input_schema** - all inputs (text, dropdown, files) in one schema:

```python
input_schema = [
    {"name": "title", "kind": "string", "label": "Title"},
    {"name": "format", "kind": "enum", "label": "Format", "options": [...]},
    {"name": "documents", "kind": "file", "label": "Documents", "accept": [".pdf", ".docx"], "min": 1, "max": 5}
]
```

**Runner contract:**

- Files → `SKRIPTOTEKET_INPUT_MANIFEST` (existing, file paths in /work/input/)
- Form values → `SKRIPTOTEKET_INPUTS` (new env var, JSON)

**UI behavior:**

- If `input_schema` exists → render form with all declared fields
- If no `input_schema` → legacy behavior (single file upload required)

**Editor UI:** input_schema editable in Metadata drawer

## Implementation Phases

### Phase 1: Backend (input_schema metadata)

| Step | File | Action |
|------|------|--------|
| 1.1 | `migrations/versions/0016_tool_versions_input_schema.py` | Add input_schema JSONB column |
| 1.2 | `src/skriptoteket/domain/scripting/models.py` | Add `input_schema: list[UiActionField] \| None` |
| 1.3 | `src/skriptoteket/domain/scripting/ui/contract_v2.py` | Add `UiFileField` with accept/min/max |
| 1.4 | `src/skriptoteket/domain/scripting/tool_inputs.py` | NEW: validation functions |
| 1.5 | `src/skriptoteket/application/scripting/commands.py` | Add input_schema to commands |
| 1.6 | `src/skriptoteket/application/scripting/handlers/save_draft.py` | Validate input_schema |
| 1.7 | `src/skriptoteket/web/api/v1/editor.py` | Return input_schema in responses |

### Phase 2: Runner Contract

| Step | File | Action |
|------|------|--------|
| 2.1 | `src/skriptoteket/infrastructure/runner/docker_runner.py` | Add SKRIPTOTEKET_INPUTS env var |
| 2.2 | `src/skriptoteket/web/api/v1/tools.py` | Accept inputs JSON in run request |
| 2.3 | `src/skriptoteket/application/scripting/commands.py` | Add input_values to ExecuteToolVersionCommand |

### Phase 3: Frontend (SPA)

| Step | File | Action |
|------|------|--------|
| 3.1 | `frontend/.../composables/tools/useToolInputs.ts` | NEW: load schema, manage form state |
| 3.2 | `frontend/.../components/tool-run/ToolInputForm.vue` | NEW: render form fields |
| 3.3 | `frontend/.../views/ToolRunView.vue` | Integrate ToolInputForm |
| 3.4 | `frontend/.../components/editor/SandboxRunner.vue` | Support input_schema in sandbox |

### Phase 4: Script Bank & Editor

| Step | File | Action |
|------|------|--------|
| 4.1 | `src/skriptoteket/script_bank/models.py` | Add input_schema to ScriptBankEntry |
| 4.2 | `src/skriptoteket/script_bank/scripts/demo_inputs.py` | NEW: demo tool with input_schema |
| 4.3 | `src/skriptoteket/web/editor_support.py` | Update STARTER_TEMPLATE |
| 4.4 | `frontend/.../components/editor/MetadataDrawer.vue` | Add input_schema editor section |

## Key Patterns to Follow

1. **settings_schema pattern** - `tool_settings.py` for validation
2. **UiActionField types** - `contract_v2.py` has all field kinds (add FILE)
3. **Type coercion** - `useToolSettings.ts` for form↔API value conversion
