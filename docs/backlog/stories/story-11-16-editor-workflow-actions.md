---
type: story
id: ST-11-16
title: "Editor workflow actions (review, publish, request changes, rollback)"
status: ready
owners: "agents"
created: 2025-12-22
epic: "EPIC-11"
acceptance_criteria:
  - "Given a contributor viewing their own draft version, when they submit for review (with optional note), then the version transitions to in_review and the editor reloads that version."
  - "Given an admin on an in_review version, when they publish, then the new active version becomes current and the editor reloads it."
  - "Given an admin on an in_review version, when they request changes (optional message), then a new draft is created and the editor reloads it."
  - "Given a superuser viewing an archived version in history, when they rollback, then that version becomes active and the editor reloads it."
ui_impact: "Adds workflow action buttons to the script editor for version lifecycle management."
dependencies: ["ST-11-04", "ST-11-05", "ST-11-12"]
---

## Context

The SSR editor (`src/skriptoteket/web/pages/admin_scripting.py` +
`src/skriptoteket/web/templates/admin/script_editor.html`) exposes workflow actions that are
missing in the SPA editor. Rollback is available from
`src/skriptoteket/web/templates/admin/partials/version_list.html` for archived versions.

## Scope

### Backend API (add to `src/skriptoteket/web/api/v1/editor.py`)

| Endpoint | Method | Role | Action |
|----------|--------|------|--------|
| `/api/v1/editor/tool-versions/{version_id}/submit-review` | POST | contributor+ | Submit draft for admin review |
| `/api/v1/editor/tool-versions/{version_id}/publish` | POST | admin+ | Publish version (makes it active) |
| `/api/v1/editor/tool-versions/{version_id}/request-changes` | POST | admin+ | Return to draft with feedback |
| `/api/v1/editor/tool-versions/{version_id}/rollback` | POST | superuser | Rollback to archived version |

- All endpoints require CSRF via `require_csrf_token`.
- Reuse handlers + commands:
  - `SubmitForReviewHandlerProtocol` / `SubmitForReviewCommand` (optional `review_note`)
  - `PublishVersionHandlerProtocol` / `PublishVersionCommand` (optional `change_summary`)
  - `RequestChangesHandlerProtocol` / `RequestChangesCommand` (optional `message`)
  - `RollbackVersionHandlerProtocol` / `RollbackVersionCommand`

Suggested response DTO:

```ts
type WorkflowActionResponse = {
  version_id: string;
  redirect_url: string;
};
```

### Frontend

- Update `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue` to add a “Process” panel.
- Show actions based on state + role (matching SSR behavior and domain rules):
  - Draft + contributor maintainer: “Skicka för granskning” (optional note input).
  - In review + admin/superuser: “Publicera” and “Begär ändringar” (optional message input).
  - Archived + superuser: “Återställ” action in version history list.
- Use API `redirect_url` to reload the editor for the resulting version.
- Surface API errors inline (reuse existing `errorMessage` pattern).

## Out of scope

- Metadata editing (ST-11-17)
- Maintainer management (ST-11-18)
- Email notifications on state changes
