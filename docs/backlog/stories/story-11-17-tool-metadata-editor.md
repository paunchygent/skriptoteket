---
type: story
id: ST-11-17
title: "Tool metadata editor (title + summary)"
status: ready
owners: "agents"
created: 2025-12-22
epic: "EPIC-11"
acceptance_criteria:
  - "Given an admin in the editor, when they update title or summary and save, then the changes persist and the editor shows the updated values."
  - "Given an admin submits an invalid title (blank/too long), when the save fails, then the SPA shows the validation error."
  - "Given a contributor (non-admin), when viewing the editor, then the metadata panel is not shown."
ui_impact: "Adds metadata editing panel to the script editor."
dependencies: ["ST-11-04", "ST-11-05", "ST-11-12"]
---

## Context

The SSR editor supports metadata updates via
`POST /admin/tools/{tool_id}/metadata` in `src/skriptoteket/web/pages/admin_scripting.py`,
rendering `src/skriptoteket/web/templates/admin/script_editor.html` (admin-only section).

## Scope

### Backend API

- Create `PATCH /api/v1/editor/tools/{tool_id}/metadata` in `src/skriptoteket/web/api/v1/editor.py`.
- Request DTO: `{ title: string; summary?: string | null }`.
- Reuse `UpdateToolMetadataHandlerProtocol` + `UpdateToolMetadataCommand` (admin+).
- Return updated metadata fields in response (id, title, summary, slug).

### Frontend

- Add a “Metadata” panel to `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue` (admin/superuser only).
- Form fields: title (required), summary (optional).
- Save action calls the API and updates the in-memory `editor.tool` values.
- Surface validation errors inline (reuse existing `errorMessage`).

## Out of scope

- Editing professions/categories (see ST-11-20)
- Slug editing
- Tool deletion
