---
type: story
id: ST-11-11
title: "Admin tools list + publish/depublish"
status: done
owners: "agents"
created: 2025-12-21
epic: "EPIC-11"
acceptance_criteria:
  - "Given an admin visits /admin/tools, when the SPA loads, then it lists tools and shows publish state via /api/v1/admin/tools"
  - "Given an admin publishes or depublishes a tool, when the action completes, then the SPA reflects the updated state and shows a toast message"
ui_impact: "Moves admin tool management to the SPA and validates CSRF + role enforcement."
dependencies: ["ST-11-04", "ST-11-05"]
---

## Context

Admin tools management is a daily operational surface and must be stable before cutover.

## Notes

### API endpoints (v1)

- `GET /api/v1/admin/tools` - List all tools for admin (admin+)
- `POST /api/v1/admin/tools/{tool_id}/publish` - Publish tool (admin+, CSRF)
- `POST /api/v1/admin/tools/{tool_id}/depublish` - Depublish tool (admin+, CSRF)

### Files implemented

- Backend: `src/skriptoteket/web/api/v1/admin_tools.py` (endpoints + DTOs)
- Backend: `src/skriptoteket/web/router.py` (router registration)
- Frontend: `frontend/apps/skriptoteket/src/views/admin/AdminToolsView.vue`

### Route

- `/admin/tools` (admin guard, `minRole: "admin"`)

### UI features

- Tool list with slug, title, summary (truncated), publish status badge
- Publish button (shown when unpublished with active version)
- Depublish button (shown when published)
- Inline success/error messages
- Swedish copy throughout

### Reused handlers

- `ListToolsForAdminHandler` (via `ListToolsForAdminHandlerProtocol`)
- `PublishToolHandler` (via `PublishToolHandlerProtocol`)
- `DepublishToolHandler` (via `DepublishToolHandlerProtocol`)
