---
type: story
id: ST-11-19
title: "Help framework (contextual help panel)"
status: done
owners: "agents"
created: 2025-12-22
epic: "EPIC-11"
acceptance_criteria:
  - "Given any SPA route, when the user clicks the help button, then a help panel opens and can be closed."
  - "Given the help panel is open, when the route changes, then the active help topic matches the current route."
  - "Given an authenticated user opens help, then they see the role-appropriate help index sections."
  - "Given a logged-out user opens help, then the help index and topic fallback show the logged-out content."
ui_impact: "Adds a help button and contextual help panel across all SPA views."
dependencies: ["ST-11-05"]
---

## Context

SSR help is implemented in `src/skriptoteket/web/templates/base.html` with:
- Index views: `partials/help/index_logged_in.html`, `partials/help/index_logged_out.html`
- Topics: `partials/help/topics/*.html` keyed by `data-help-topic`
- Context binding via `{% block help_context_id %}` per page

These templates are the source of truth for content and wording.

## Scope

### Help topics (SSR parity)

| Topic | Route(s) |
|-------|----------|
| `home` | `/` |
| `login` | `/login` |
| `browse_professions` | `/browse` |
| `browse_categories` | `/browse/:profession` |
| `browse_tools` | `/browse/:profession/:category` |
| `tools_run` | `/tools/:slug/run` |
| `tools_result` | `/tools/:slug/runs/:runId` |
| `my_tools` | `/my-tools` |
| `apps_detail` | `/apps/:appId` |
| `suggestions_new` | `/suggestions/new` |
| `admin_suggestions` | `/admin/suggestions`, `/admin/suggestions/:id` |
| `admin_tools` | `/admin/tools` |
| `admin_editor` | `/admin/tools/:toolId`, `/admin/tool-versions/:versionId` |

### Frontend components

- `frontend/apps/skriptoteket/src/components/help/HelpButton.vue`
- `frontend/apps/skriptoteket/src/components/help/HelpPanel.vue`
- `frontend/apps/skriptoteket/src/components/help/useHelp.ts`

### Implementation notes

1. Render `HelpButton` in `frontend/apps/skriptoteket/src/App.vue` header.
2. `HelpPanel` contains:
   - Help index (logged-in/out) with role-based sections (mirroring SSR index files).
   - Help topic view showing the topic for the current route.
3. Route → topic mapping via `useRoute()` (prefer route names from `src/router/routes.ts`).
4. Help copy should match SSR wording (Swedish).

## Out of scope

- Interactive tutorials / walkthroughs
- Search within help
- Video help content
- Feedback mechanism
