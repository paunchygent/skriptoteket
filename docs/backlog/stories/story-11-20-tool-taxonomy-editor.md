---
type: story
id: ST-11-20
title: "Tool taxonomy editor (professions + categories)"
status: done
owners: "agents"
created: 2025-12-22
epic: "EPIC-11"
acceptance_criteria:
  - "Given an admin in the editor, when they open the Taxonomy panel, then they see the current profession + category tags for the tool."
  - "Given an admin updates the selected professions/categories and saves, then the tool appears under the updated browse paths."
  - "Given an admin attempts to save with no professions or no categories, then the SPA shows a validation error and does not persist changes."
ui_impact: "Adds tool profession/category tag management to the editor (admin only)."
dependencies: ["ST-11-04", "ST-11-05", "ST-11-06", "ST-11-12"]
---

## Context

Tool taxonomy (profession/category tags) is currently set when tools are created from suggestions.
The editor does not yet allow admins to adjust these tags. This follow-up story adds that capability
as a distinct feature from metadata editing (ST-11-17).

## Scope

### Backend API (IDs, not slugs)

- Add `PATCH /api/v1/editor/tools/{tool_id}/taxonomy` in `src/skriptoteket/web/api/v1/editor.py`.
- Request DTO uses IDs (not slugs): `{ profession_ids: UUID[]; category_ids: UUID[] }`.
- Response DTO returns selected IDs: `{ profession_ids: UUID[]; category_ids: UUID[] }`.
- Add `GET /api/v1/editor/tools/{tool_id}/taxonomy` to load current tag IDs (separate from editor boot).
- New command/handler in `application.catalog` to replace tool profession/category tags.
- Validation: tool exists; all IDs exist; at least one profession + category.
- Repository support:
  - `list_tag_ids(tool_id)` to load current selections.
  - `replace_tags(tool_id, profession_ids, category_ids, now)` to update `tool_professions`/`tool_categories`
    within the UoW.

### Frontend

- Add a “Taxonomy” panel in `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`
  (admin/superuser only).
- Use catalog endpoints for options:
  - `GET /api/v1/catalog/professions` (IDs + labels)
  - `GET /api/v1/catalog/categories` (IDs + labels)
- Load current selection via `GET /api/v1/editor/tools/{tool_id}/taxonomy` (kept separate from editor boot).
- Multi-select or checkbox list for professions and categories.
- Save button calls taxonomy API and updates local editor state.
- Display validation errors inline.

## Out of scope

- Creating or editing professions/categories
- Suggestion decision workflows
- Bulk taxonomy updates across tools

## Implemented (2025-12-23)

- Backend: `GET/PATCH /api/v1/editor/tools/{tool_id}/taxonomy` in `src/skriptoteket/web/api/v1/editor.py` (admin + CSRF).
- Application/infra: handlers `ListToolTaxonomyHandler`, `UpdateToolTaxonomyHandler`; repo `list_tag_ids`/`replace_tags` in `src/skriptoteket/infrastructure/repositories/tool_repository.py`.
- SPA: taxonomy checkboxes in `frontend/apps/skriptoteket/src/components/editor/MetadataDrawer.vue` wired via `frontend/apps/skriptoteket/src/composables/editor/useToolTaxonomy.ts`.
