---
type: story
id: ST-14-24
title: "UI contract: first-class file references (picker + action fields)"
status: done
owners: "agents"
created: 2025-12-29
updated: 2026-06-18
epic: "EPIC-14"
acceptance_criteria:
  - "Given a tool emits next_actions with file fields, when the UI renders the action form, then it shows a picker per file field (multiple file fields in the same action are supported) without exposing runner filesystem paths."
  - "Given a file field has min/max constraints, when the user selects file refs, then validation enforces the constraints and the submitted value is always FileRef[] (array), even when max=1."
  - "Given a file field has a default value (from tool settings or action prefill), when the UI renders the field, then the default is preselected if available (including vault refs); missing defaults block execution with an actionable validation error."
  - "Given a user submits an action containing file fields, when the runner executes the tool, then the referenced files resolve to the correct on-disk paths within the run/session sandbox and the input manifest preserves which field each file belongs to."
  - "Given a file reference is invalid or not available in the current run/session, when normalizing or executing, then the platform returns an actionable validation error (no 500)."
  - "Given a tool does not use file references, when running multi-step tools, then behavior remains unchanged."
dependencies:
  - "ST-19-02"
  - "ST-19-01"
  - "ST-19-03"
  - "ST-14-19"
ui_impact: "Yes (inputs/actions UI + runner integration)"
data_impact: "No (references travel in existing payload/state; no DB migration required)"
---

## Context

Today, tools must know (or assume) that uploaded files land under `/work/input/...` and must manually pass file names via
state to later steps. This works, but it’s leaky and brittle.

## Goal

Add a first-class, stable “file reference” concept to the UI contract so tools can ask users to select files from the
current run/session without hard-coding paths.

## Notes

File references are identifiers (not paths). The UI must only present names/labels and never leak internal filesystem
paths; this keeps the contract compatible with future file sources (e.g. per-user reusable file libraries) without
breaking UX.

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`

## Decisions (LOCKED)

- **Multiple file fields are REQUIRED:** `next_actions[].fields` MUST allow multiple file fields in the same action.
- **Value shape is always list:** file field values MUST be `FileRef[]` (array). There is no scalar `FileRef` value
  shape for actions.
- **UiActionField kind/name (REQUIRED):** action fields MUST use `UiActionField.kind="file_ref"` (NOT `kind="file"`),
  with `min/max` and optional `sources?: ["session","vault"]` (default both). Value is always `FileRef[]`.
- **Available FileRefs API shape (REQUIRED):** implement new endpoints (do not overload session-files):
  - `GET /api/v1/tools/{tool_id}/file-refs?context=default`
  - `GET /api/v1/editor/tool-versions/{version_id}/file-refs?snapshot_id=...`
- **Wire payload shape (REQUIRED):**
  - Non-file inputs are sent as JSON only (existing behavior).
  - File refs are sent as `file_refs_by_field: Record[field_name, FileRef[]]` (no flat list).
  - The platform writes file-ref arrays into `/work/request.json` under `inputs.values[field]` / `action.input[field]`.
- **Per-field mapping is REQUIRED end-to-end:** the platform MUST preserve which field each staged file belongs to
  (e.g. include a `field` property per entry in `/work/request.json`).
- **No flat file_refs semantics:** action submission MUST NOT be a single flat `file_refs: string[]` with ambiguous
  ownership across multiple fields.

### Dependency alignment (no parallel mechanisms)

- The backend-side file reference model and resolver is implemented in ST-19-02.
- UI work in this story should be limited to:
  - adding a file-ref field kind to action schemas,
  - rendering a picker populated by the platform’s “available file refs” API,
  - submitting selected file refs as action input values.
- Do not introduce a UI-only “file id” or path-based fallback; the only identity is `FileRef` values and the only
  staging pipeline is the platform resolver.

## Implementation Summary (as of 2026-06-18)

- The file-ref contract ships in the current platform through
  `ToolFileFieldPicker.vue`, `UiActionFieldFileRef.vue`,
  `/api/v1/tools/{tool_id}/file-refs`,
  `/api/v1/editor/tool-versions/{version_id}/file-refs`, and the shared
  resolver-backed request/manifest path.
- Current runtime/editor surfaces use opaque `session:*` and `vault:*` refs
  rather than filesystem paths, preserve per-field mapping, and support
  defaults plus actionable validation, so `PR-0359` repairs this story to
  `done`.
