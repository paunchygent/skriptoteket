---
type: story
id: ST-11-18
title: "Maintainer management (add/remove contributors)"
status: done
owners: "agents"
created: 2025-12-22
epic: "EPIC-11"
acceptance_criteria:
  - "Given an admin in the editor, when they open the Maintainers panel, then they see the current maintainers with email + role."
  - "Given an admin enters an existing user email, when they add the maintainer, then the list updates and the user gains edit access."
  - "Given an admin removes a maintainer, when the action completes, then the list updates and that user loses edit access."
  - "Given an invalid email or non-contributor user, when add fails, then the SPA shows the error message."
ui_impact: "Adds maintainer management panel to the script editor (admin only)."
dependencies: ["ST-11-04", "ST-11-05", "ST-11-12"]
---

## Context

The SSR editor exposes maintainer management routes in
`src/skriptoteket/web/pages/admin_scripting.py` and renders
`src/skriptoteket/web/templates/admin/partials/maintainer_list.html`.

## Scope

### Backend API

| Endpoint | Method | Role | Action |
|----------|--------|------|--------|
| `/api/v1/editor/tools/{tool_id}/maintainers` | GET | admin+ | List current maintainers |
| `/api/v1/editor/tools/{tool_id}/maintainers` | POST | admin+ | Add maintainer by email |
| `/api/v1/editor/tools/{tool_id}/maintainers/{user_id}` | DELETE | admin+ | Remove maintainer |

- Reuse handlers + commands:
  - `ListMaintainersHandlerProtocol` / `ListMaintainersQuery`
  - `AssignMaintainerHandlerProtocol` / `AssignMaintainerCommand`
  - `RemoveMaintainerHandlerProtocol` / `RemoveMaintainerCommand`
- For add: resolve email via `UserRepositoryProtocol.get_auth_by_email` (same as SSR).
- Validation mirrors domain rules (user must be contributor+).

Suggested response DTO:

```ts
type MaintainerSummary = {
  id: string;
  email: string;
  role: string;
};

type MaintainerListResponse = {
  tool_id: string;
  maintainers: MaintainerSummary[];
  error?: string | null;
};
```

### Frontend

- Add a “Maintainers” panel to `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue` (admin/superuser only).
- List maintainers with email + role badge; remove button per row.
- Email input to add a maintainer; submit calls the API and refreshes list.
- Surface API errors inline (reuse existing `errorMessage` or panel-level message).

## Out of scope

- Bulk maintainer operations
- Maintainer invitations (user must already exist)
- Self-removal prevention
