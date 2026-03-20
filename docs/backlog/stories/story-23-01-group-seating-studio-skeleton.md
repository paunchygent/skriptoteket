---
type: story
id: ST-23-01
title: "Klassrumskartan — Registry, App Route, Bootstrap Endpoint"
status: done
owners: "agents"
created: 2026-03-20
epic: "EPIC-23"
acceptance_criteria:
  - "Given the backend starts, when `list_all()` is called on the curated apps registry, then `classroom.group-seating-studio` is returned."
  - "Given the app loads, a `GET /api/v1/apps/classroom.group-seating-studio/bootstrap` request returns typed metadata including available Lesson Modes."
---

## Context
Initial scaffolding ensuring backend presence and strict curated app rules. Includes exposing the bespoke bootstrap payload.

## Implementation Plan

### [ ] PR 1: Backend Registry Integration & Bootstrap Endpoint
- **Intent**: Register the app in the catalog and provide essential initialization payload for the bespoke UI.
- **Code Choice**: Update `InMemoryCuratedAppRegistry` with `app_id="classroom.group-seating-studio"` and `ui_mode=CuratedAppUiMode.BESPOKE_REQUIRED`.
- **API Surface**: Create `web/api/v1/apps_classroom_planner.py` providing the `GET /api/v1/apps/classroom.group-seating-studio/bootstrap` route. This should return typed data including `LessonModePreset` entries and active feature flags.

### [ ] PR 2: Vue SPA Skeleton & Routing
- **Intent**: Fail-closed generic view rendering and provide a blank landing zone.
- **Code Choice**:
  - Install `vue-draggable-plus` via `pnpm add`.
  - Create `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.vue` with an empty scaffold.
  - Wire it to `AppHostView.vue` `bespokeRegistry` dictionary.
- **Verification**: Run `pdm run dev-local` and trigger visual inspection mapping to `/apps/classroom.group-seating-studio`.
