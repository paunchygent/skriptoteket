---
type: story
id: ST-11-08
title: "My runs list + detail"
status: ready
owners: "agents"
created: 2025-12-21
epic: "EPIC-11"
acceptance_criteria:
  - "Given an authenticated user, when visiting /my-runs, then the SPA lists the user's runs via /api/v1/my-runs"
  - "Given a run id, when visiting /my-runs/:id, then the SPA renders run detail and allows navigation back to results and artifacts"
ui_impact: "Replaces server-rendered run history pages with SPA equivalents."
dependencies: ["ST-11-04", "ST-11-05", "ST-11-07"]
---

## Context

Users need a reliable history to revisit outputs and artifacts; this also validates pagination and authorization rules.

## Implementation (SPA)

### Backend API (v1)

- My runs listing: `GET /api/v1/my-runs`
  - Response: `ListMyRunsResponse { runs: MyRunItem[] }`
  - Includes `tool_id` + `tool_slug` (nullable) + `tool_title` to power list/detail UX without extra fetches.
  - File: `src/skriptoteket/web/api/v1/my_runs.py`
- Run detail reuse: `GET /api/v1/runs/{run_id}`
  - `RunDetails` now includes `tool_id`, `tool_slug` (nullable), `tool_title`
  - Files: `src/skriptoteket/application/scripting/interactive_tools.py`,
    `src/skriptoteket/application/scripting/handlers/get_tool_run.py`
- Route cutover: SSR `/my-runs/{run_id}` removed; `/my-runs/{run_id}/artifacts/{artifact_id}` retained for legacy links.
  - File: `src/skriptoteket/web/pages/my_runs.py`

After API changes, regenerate TypeScript OpenAPI types:

- `pdm run fe-gen-api-types` (writes `frontend/apps/skriptoteket/src/api/openapi.d.ts`)

### Frontend (Vue/Vite SPA)

- New views:
  - `/my-runs`: `frontend/apps/skriptoteket/src/views/MyRunsListView.vue`
  - `/my-runs/:runId`: `frontend/apps/skriptoteket/src/views/MyRunsDetailView.vue`
- Shared run result renderer:
  - `frontend/apps/skriptoteket/src/components/run-results/RunResultPanel.vue`
  - Props down + emits `submit-action` up; uses `UiOutputRenderer` + `UiActionForm`
- Routes: `frontend/apps/skriptoteket/src/router/routes.ts`
- Navigation: `frontend/apps/skriptoteket/src/App.vue` adds “Mina körningar”

### Verification

- `pdm run lint`
- `pdm run typecheck`
- `pdm run docs-validate`
- `pnpm -C frontend --filter @skriptoteket/spa typecheck`
- `pnpm -C frontend --filter @skriptoteket/spa lint`
- `pnpm -C frontend --filter @skriptoteket/spa build`

### Live flow

- Live check (2025-12-22): ran Playwright e2e `pdm run python -m scripts.playwright_st_11_08_spa_my_runs_e2e --base-url http://127.0.0.1:5173`
  (tool slug: `demo-next-actions`) proving:
  - tool run creates a run
  - `/my-runs` lists the run
  - `/my-runs/:id` renders outputs + downloads artifacts
  - `next_actions` submit from my-runs detail creates a new run and navigates to the new run id
