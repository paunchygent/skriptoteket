---
type: story
id: ST-04-03
title: "Admin script editor UI (create, edit, run sandbox)"
status: done
owners: "agents"
created: 2025-12-14
epic: "EPIC-04"
acceptance_criteria:
  - "Given I am an admin, when I navigate to a tool's script editor, then I see a code editor with the current draft (or active) source."
  - "Given I am editing a draft, when I click Save, then a new immutable draft version is created."
  - "Given I have a draft, when I click Run Sandbox and upload a file, then the script executes and I see HTML output, logs, and artifacts."
  - "Given I am a contributor, when I try to edit another user's draft, then I am denied access."
  - "Given a new tool with no versions, when I open the editor, then a starter template is pre-filled."
---

## Context

This story provides the web UI for script authoring. Admins can create drafts, edit code, run sandbox tests, and view results without leaving the browser.

See REF-scripting-api-contracts for detailed endpoint specifications, request/response DTOs, and UX flow mapping.

## Scope

- Application handlers:
  - `CreateDraftVersionHandler`
  - `SaveDraftVersionHandler`
  - `RunSandboxHandler`
  - `SubmitForReviewHandler`
- Web routes:
  - `src/skriptoteket/web/pages/admin_scripting.py` (editor + draft routes)
  - `src/skriptoteket/web/pages/admin_scripting_runs.py` (sandbox run + run refresh + artifact download)
  - Entry point: link from `GET /admin/tools` (ST-03-03) to the script editor
  - `GET /admin/tools/{tool_id}` - load tool metadata
  - `GET /admin/tools/{tool_id}/versions` - version history
  - `GET /admin/tool-versions/{version_id}` - open version (load source)
  - `POST /admin/tools/{tool_id}/versions` - create draft
  - `POST /admin/tool-versions/{version_id}/save` - save draft snapshot (append-only) with an expected-parent check
  - `POST /admin/tool-versions/{version_id}/run-sandbox` - run sandbox
  - `POST /admin/tool-versions/{version_id}/submit-review` - submit for review
  - `GET /admin/tool-runs/{run_id}` - refresh run details
  - `GET /admin/tool-runs/{run_id}/artifacts/{artifact_id}` - download artifact
- Templates:
  - `templates/admin/script_editor.html` - main editor page
  - `templates/admin/partials/run_result.html` - HTMX partial for results
  - `templates/admin/partials/version_list.html` - version history
- Starter template for new scripts

## UI Components

- Code editor: CodeMirror (server-rendered `<textarea>` fallback)
- Entrypoint field: text input (default "run_tool")
- File upload: input for sandbox test file
- Run button: triggers sandbox execution
- Result display: HTML preview, stdout/stderr tabs, artifacts list
- Version history: table with version/state/author/timestamp, actions

## Technical Notes

- HTMX for partial updates (run result, version list refresh)
- Asset strategy: vendor pinned JS/CSS under `src/skriptoteket/web/static/vendor/` (no CDN at runtime).
- Execution preflight: `compile(source_code, "<tool_version>", "exec")` before runner execute; on `SyntaxError`, persist
  a FAILED run without calling Docker and with an actionable `error_summary`.
- Concurrency control: use `expected_parent_version_id` (see `REF-scripting-api-contracts`) rather than DB-level
  optimistic locking; reject with `DomainError(CONFLICT)` if the draft head has advanced.
- Role guards: contributor can edit only own drafts (ownership via `tool_versions.created_by_user_id`)
  - Contributor can still view the published ACTIVE/ARCHIVED versions derived from their work, to enable iteration after publication (create a new draft from the published baseline).
  - This story SHOULD include a minimal discoverability surface for contributors (e.g. “My tools” list) or document
    how contributors obtain a `tool_id` to open the editor.
- Template pre-fill for new tools:

  ```python
  def run_tool(input_path: str, output_dir: str) -> str:
      import os
      size = os.path.getsize(input_path)
      return f"<p>Received file of {size} bytes.</p>"
  ```
