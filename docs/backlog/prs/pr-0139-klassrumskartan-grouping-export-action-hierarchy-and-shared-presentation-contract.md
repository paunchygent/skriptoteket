---
type: pr
id: PR-0139
title: "Klassrumskartan: grouping export action hierarchy and shared presentation contract"
status: ready
owners: "agents"
created: 2026-03-25
updated: 2026-03-25
stories:
  - "ST-26-05"
  - "ST-26-04"
tags: ["frontend", "backend", "contract", "klassrumskartan", "export", "grouping"]
acceptance_criteria:
  - "Given a teacher is in the grouping workspace, when they use the export controls, then the primary `Exportera` action defaults to `Excel (.xlsx)` and a compact adjacent menu exposes `Excel (.xlsx)` and `PDF (A4 stående)` without teaching a generic file-type matrix."
  - "Given grouping export is prepared, when backend and frontend exchange data, then a shared grouping presentation contract exists that is independent from the live planner DOM and from the seating poster-scene contract."
  - "Given a grouping export job is created, when the request is serialized, then it is keyed to an explicit grouping draft id and uses only the approved export kinds `xlsx` and `pdf`, with `paper_size=a4_portrait` as the only allowed PDF page contract in this slice."
  - "Given a teacher starts a grouping export, when the flow is in progress, then pending autosave is flushed first, duplicate clicks stay disabled, and status remains scoped to the active grouping draft rather than leaking into seating or overview state."
---

## Problem

Grouping export is still only a generic story idea. The app does not yet have a grouping-specific
export contract, and the next team would still have to invent the action hierarchy, API shape, and
shared presentation semantics before building either `XLSX` or `PDF`.

## Goal

Lock the teacher-facing grouping export hierarchy and create one shared grouping presentation
contract that both later artifact renderers must consume.

## Locked design decisions

- The grouping workspace export cluster lives in the existing grouping action row. Do not create a
  separate modal or drawer for the first export release.
- The primary grouping export path is `Excel (.xlsx)`.
- `PDF` is available from the same export family, but only as `PDF (A4 stående)` in this planning
  package.
- Grouping export must not reuse the seating `poster_scene` contract or the seating default
  `Affisch (A3)` / `Affisch (A4)` wording.
- A shared `GroupingExportPresentation` model is the canonical renderer input for both grouping
  `XLSX` and grouping `PDF`.
- The shared presentation model must carry:
  - grouping draft id
  - roster/class naming needed for filenames and headings
  - deterministic group order
  - deterministic member order inside each group
  - teacher-facing group labels
  - a teacher-safe filename stem

## Non-goals

- Rendering the final `XLSX` workbook bytes.
- Rendering the final `PDF` bytes.
- Introducing cross-draft export history or a global export inbox.

## Implementation plan

1. Extend the backend export seams for grouping:
   - update `src/skriptoteket/protocols/classroom_planner_exports.py`
   - add `src/skriptoteket/application/curated_apps/classroom_planner/exports/grouping_presentation.py`
   - add `src/skriptoteket/application/curated_apps/classroom_planner/handlers/grouping_exports.py`
   - add `src/skriptoteket/application/curated_apps/classroom_planner/handlers/grouping_export_jobs.py`
2. Add grouping-specific web DTOs by extending the existing planner export contract modules instead
   of inventing a second naming scheme:
   - update `src/skriptoteket/web/api/v1/apps_classroom_planner_export_contracts.py`
   - update `src/skriptoteket/web/api/v1/apps_classroom_planner_export_job_contracts.py`
   - update `src/skriptoteket/web/api/v1/apps_classroom_planner_grouping.py`
3. Add a dedicated grouping export-job persistence seam instead of overloading seating rows:
   - add `src/skriptoteket/infrastructure/db/models/classroom_planner_grouping_export_job.py`
   - add `src/skriptoteket/infrastructure/repositories/classroom_planner_grouping_export_jobs.py`
4. Extend the SPA export surface for grouping:
   - update `frontend/apps/skriptoteket/src/views/apps/classroomPlannerExportApi.ts`
   - add `frontend/apps/skriptoteket/src/views/apps/useGroupingExportFlow.ts`
   - generalize `frontend/apps/skriptoteket/src/views/apps/components/PlannerExportActionGroup.vue`
   - update `frontend/apps/skriptoteket/src/views/apps/components/PlannerExportActionGroup.spec.ts`
   - update `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspacePane.vue`
5. Lock the UI wording in this slice:
   - section label: `Export`
   - primary button: `Exportera`
   - primary/default option: `Excel (.xlsx)`
   - alternate option: `PDF (A4 stående)`

## Proposed contract shape

### Prepare grouping export

`POST /api/v1/apps/classroom.group-seating-studio/drafts/grouping/{draft_id}/exports`

Request body:

```json
{
  "export_kind": "xlsx"
}
```

or

```json
{
  "export_kind": "pdf",
  "paper_size": "a4_portrait"
}
```

Response body:

```json
{
  "draft_id": "uuid",
  "draft_kind": "grouping",
  "export_kind": "xlsx",
  "paper_size": null,
  "presentation": {
    "class_name": "SA24D",
    "title": "Gruppindelning",
    "groups": [
      {
        "group_label": "Grupp 1",
        "group_order": 1,
        "members": [
          {"member_order": 1, "display_name": "Ada Lovelace"}
        ]
      }
    ],
    "filename_stem": "sa24d-gruppindelning"
  }
}
```

### Create grouping export job

`POST /api/v1/apps/classroom.group-seating-studio/drafts/grouping/{draft_id}/exports/jobs`

Allowed request bodies in this planning package:

```json
{"export_kind": "xlsx"}
```

```json
{"export_kind": "pdf", "paper_size": "a4_portrait"}
```

## Test plan

- Focused backend contract tests for grouping prepare/create/status/download routes.
- Focused unit tests for `GroupingExportPresentation` proving deterministic group/member ordering.
- Frontend unit tests for the grouping export action hierarchy:
  - default click runs `Excel (.xlsx)`
  - menu click can start `PDF (A4 stående)`
  - duplicate clicks stay disabled while busy
  - autosave flush runs before submit

## Rollback plan

- Remove grouping export routes, DTOs, and SPA action wiring while preserving the already-shipped
  seating export lane.
