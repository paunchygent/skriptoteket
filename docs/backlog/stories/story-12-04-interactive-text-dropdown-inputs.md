---
type: story
id: ST-12-04
title: "Interactive text/dropdown inputs"
status: in_progress
owners: "agents"
created: 2025-12-21
epic: "EPIC-12"
acceptance_criteria:
  - "Given a tool declares input_schema (text/dropdown fields), when user opens run view, then SPA renders a pre-run form and file upload is not required"
  - "Given a tool declares input_schema with one file field, when user opens run view, then SPA renders a file upload widget with accept/min/max constraints"
  - "Given inputs are invalid, when submitting, then user sees validation error and runner is not invoked"
  - "Given input_schema exists, when tool runs, then script receives form values via SKRIPTOTEKET_INPUTS env var"
  - "Given no input_schema, when user opens run view, then legacy upload-required behavior applies (current multi-file picker + at least one file required)"
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

### Unified `input_schema`

All pre-run inputs (text, dropdowns, optional file upload) are declared in one schema stored on the tool version.

```python
input_schema = [
    {"name": "title", "kind": "string", "label": "Title"},
    {"name": "format", "kind": "enum", "label": "Format", "options": [...]},
    {"name": "documents", "kind": "file", "label": "Documents", "accept": [".pdf", ".docx"], "min": 1, "max": 5},
]
```

### V1 scope constraints (explicit)

- **At most one file field** in `input_schema` (0..1). All uploaded files are implicitly associated with that field.
- **No file field mapping** (no “template vs data” buckets) in v1.
- **`accept` is a UI hint/filter only**; backend does not validate file types. Scripts remain the source of truth.
- **No `required` flag for non-file fields** in v1. “Missing required business inputs” are handled by the script on Kör.
- **Run request shape:** always `multipart/form-data` with optional `files[]` plus `inputs` (JSON string).
- **Schema types:** `input_schema` uses a dedicated “tool input” field type (not `UiActionField`) to avoid leaking file fields
  into JSON-only contexts like `settings_schema` and `next_actions`.

### Runner contract

- Files → `SKRIPTOTEKET_INPUT_MANIFEST` (existing, file paths in /work/input/)
- Form values → `SKRIPTOTEKET_INPUTS` (new env var, JSON object; defaults to `{}`)

### UI behavior

- If `input_schema` exists → render form with all declared fields
- If no `input_schema` → legacy upload-required behavior (current multi-file picker + at least one file required)

### Editor UI

`input_schema` is **version-level** content and is edited alongside code (same workflow as `settings_schema`), not in the
tool metadata drawer.

## Implementation Phases

### Phase 1: Backend (schema + storage)

| Step | File | Action |
|------|------|--------|
| 1.1 | `migrations/versions/0016_tool_versions_input_schema.py` | Add `tool_versions.input_schema` (JSONB) |
| 1.2 | `migrations/versions/0017_tool_runs_input_values.py` | Add `tool_runs.input_values` (JSONB) + allow runs without files (nullable `input_filename` or equivalent) |
| 1.3 | `src/skriptoteket/domain/scripting/tool_inputs.py` | NEW: ToolInputField types + schema/value validation |
| 1.4 | `src/skriptoteket/domain/scripting/models.py` | Add `input_schema` to ToolVersion + `input_values` to ToolRun |
| 1.5 | `src/skriptoteket/infrastructure/db/models/tool_version.py` | Persist `input_schema` |
| 1.6 | `src/skriptoteket/infrastructure/db/models/tool_run.py` | Persist `input_values` + allow file-less runs |
| 1.7 | `src/skriptoteket/application/scripting/commands.py` | Add `input_schema` to draft/publish commands; add `input_values` to execute/run commands |
| 1.8 | `src/skriptoteket/application/scripting/handlers/save_draft_version.py` | Validate/normalize `input_schema` |
| 1.9 | `src/skriptoteket/application/scripting/handlers/create_draft_version.py` | Validate/normalize `input_schema` |
| 1.10 | `src/skriptoteket/web/api/v1/editor.py` | Return + accept `input_schema` in editor responses/requests |
| 1.11 | `src/skriptoteket/web/api/v1/tools.py` | Return `input_schema` in tool metadata for run view |

### Phase 2: Runner Contract

| Step | File | Action |
|------|------|--------|
| 2.1 | `src/skriptoteket/web/api/v1/tools.py` | Accept `inputs` (JSON string) + optional `files[]` in run request |
| 2.2 | `src/skriptoteket/application/scripting/handlers/execute_tool_version.py` | Validate/normalize `inputs` against schema; store on ToolRun; pass to runner |
| 2.3 | `src/skriptoteket/infrastructure/runner/docker_runner.py` | Add `SKRIPTOTEKET_INPUTS` env var |

### Phase 3: Frontend (SPA)

| Step | File | Action |
|------|------|--------|
| 3.1 | `frontend/.../composables/tools/useToolInputs.ts` | NEW: manage `input_schema` + form state + validation |
| 3.2 | `frontend/.../components/tool-run/ToolInputForm.vue` | NEW: render text/dropdown fields + optional file picker |
| 3.3 | `frontend/.../composables/tools/useToolRun.ts` | Submit `inputs` + optional `files` (multipart) |
| 3.4 | `frontend/.../views/ToolRunView.vue` | Render ToolInputForm before first run |

### Phase 4: Script Bank & Editor

| Step | File | Action |
|------|------|--------|
| 4.1 | `src/skriptoteket/script_bank/models.py` | Add input_schema to ScriptBankEntry |
| 4.2 | `src/skriptoteket/script_bank/scripts/demo_inputs.py` | NEW: demo tool with input_schema |
| 4.3 | `src/skriptoteket/web/editor_support.py` | Update STARTER_TEMPLATE |
| 4.4 | `frontend/.../components/editor/EditorWorkspacePanel.vue` | Add input_schema JSON editor section (same pattern as settings_schema) |
| 4.5 | `frontend/.../components/editor/SandboxRunner.vue` | Support `inputs` + optional files in sandbox run |

## Key Patterns to Follow

1. **settings_schema pattern** - `tool_settings.py` for validation
2. **Schema normalization** - mirror `tool_settings.py` rules (unknown keys, type coercion, empty values dropped)
3. **Type coercion** - mirror `useToolSettings.ts` for form↔API value conversion
