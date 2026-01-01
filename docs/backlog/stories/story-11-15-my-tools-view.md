---
type: story
id: ST-11-15
title: "My Tools view (contributor dashboard)"
status: done
owners: "agents"
created: 2025-12-22
epic: "EPIC-11"
acceptance_criteria:
  - "Given a contributor visits /my-tools, when the SPA loads, then it lists the tools they maintain showing title, optional summary, and published state."
  - "Given a tool row, when the contributor clicks Redigera, then they navigate to /admin/tools/{toolId}."
  - "Given a contributor with no maintained tools, when the view loads, then an empty state message is shown."
ui_impact: "Implements the contributor dashboard showing maintained tools."
dependencies: ["ST-11-04", "ST-11-05", "ST-11-12"]
---

## Context

The SSR version lives in `src/skriptoteket/web/pages/my_tools.py` and renders
`src/skriptoteket/web/templates/my_tools.html` using `ListToolsForContributorHandlerProtocol`.
The SPA view exists as a placeholder only.

## Scope

### Backend

- Create `GET /api/v1/my-tools` in `src/skriptoteket/web/api/v1/my_tools.py` (new router).
- Use `ListToolsForContributorHandlerProtocol` + `ListToolsForContributorQuery`.
- Response DTO includes: `id`, `title`, `summary`, `is_published`.
- Enforce contributor+ via `require_contributor_api`.

### Frontend

- Implement `frontend/apps/skriptoteket/src/views/MyToolsView.vue`.
- Render list rows with title, summary (if present), and published status text (“Publicerad” / “Ej publicerad”).
- Link each row to `/admin/tools/{toolId}` (editor route from ST-11-12).
- Empty state copy: “Du har inga verktyg att underhålla ännu.”

## Out of scope

- Creating new tools (handled via suggestions flow)
- Tool deletion
- Version-state badges (draft/in_review)
