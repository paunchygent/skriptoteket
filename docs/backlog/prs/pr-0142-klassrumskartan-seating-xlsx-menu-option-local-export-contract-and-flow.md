---
type: pr
id: PR-0142
title: "Klassrumskartan: seating XLSX menu option, local export contract, and flow"
status: ready
owners: "agents"
created: 2026-03-25
updated: 2026-03-25
stories:
  - "ST-26-03"
tags: ["frontend", "backend", "xlsx", "klassrumskartan", "export", "seating"]
acceptance_criteria:
  - "Given a teacher is in the seating workspace, when they use the export controls, then the primary `Exportera` action still runs the existing `Affisch (A3)` PDF path and `Excel (.xlsx)` appears only as an additional menu option."
  - "Given a seating export job is created with `export_kind=xlsx`, when the request is handled, then the job remains draft-scoped and uses a local workbook-generation path rather than Sir Convert-a-Lot."
  - "Given the teacher starts a seating `XLSX` export, when the flow is in progress, then pending autosave is flushed first, duplicate clicks stay disabled, and success/failure/download-again state stays local to the active seating draft."
  - "Given the teacher later retries the download, when the workbook has already succeeded, then the existing seating export surface can serve `Ladda ned igen` for the `XLSX` artifact without changing the default PDF-first action hierarchy."
---

## Problem

The seating export lane already has a compact PDF-first action hierarchy. If `XLSX` is added
without a locked contract, the next implementation team could accidentally replace the PDF default,
route a lightweight workbook through Sir Convert-a-Lot, or smear flow state across draft changes.

## Goal

Add seating `XLSX` to the existing seating export family without changing the current PDF-first
teacher workflow.

## Locked design decisions

- Keep the current default seating export unchanged:
  - primary button: `Exportera`
  - default path: `Affisch (A3)`
- Add `Excel (.xlsx)` as a secondary seating export option in the existing export menu.
- `XLSX` generation is local inside Skriptoteket.
- Do not submit seating `XLSX` jobs to Sir Convert-a-Lot.
- Reuse the existing seating export job flow and draft-scoped recovery model where practical.

## Non-goals

- Replacing the current seating PDF default.
- Reworking the seating PDF renderer.
- Introducing a second export panel or modal for spreadsheet export.

## Implementation plan

1. Extend the backend seating export contract for `XLSX`:
   - update `src/skriptoteket/protocols/classroom_planner_exports.py`
   - update `src/skriptoteket/web/api/v1/apps_classroom_planner_export_job_contracts.py`
   - update `src/skriptoteket/web/api/v1/apps_classroom_planner_seating.py`
   - update `src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_export_jobs.py`
2. Keep the existing `SeatingExportJob` seam and extend it to allow `export_kind=xlsx`.
3. Extend the SPA export flow:
   - update `frontend/apps/skriptoteket/src/views/apps/classroomPlannerExportApi.ts`
   - update `frontend/apps/skriptoteket/src/views/apps/useSeatingExportFlow.ts`
   - update `frontend/apps/skriptoteket/src/views/apps/components/PlannerExportActionGroup.vue`
   - update `frontend/apps/skriptoteket/src/views/apps/components/PlannerExportActionGroup.spec.ts`
4. Lock the UI wording in this slice:
   - keep `Affisch (A3)` and `Affisch (A4)` unchanged
   - add `Excel (.xlsx)` as the spreadsheet option

## Proposed contract shape

`POST /api/v1/apps/classroom.group-seating-studio/drafts/seating/{draft_id}/exports/jobs`

New request body allowed in this slice:

```json
{
  "export_kind": "xlsx"
}
```

Response shape remains the same typed job envelope already used by the seating export lane, with:

- `export_kind`: `xlsx`
- `layout_id`: `null`
- `paper_size`: `null`
- `download_url`: populated on success

## Test plan

- Backend tests proving `xlsx` jobs do not call Sir Convert-a-Lot.
- Frontend tests proving:
  - default click still exports `Affisch (A3)`
  - menu click can export `Excel (.xlsx)`
  - autosave flush still happens before export
  - duplicate clicks remain disabled
- Live browser proof that the PDF default remains intact after adding the `XLSX` option.

## Rollback plan

- Remove only the `Excel (.xlsx)` option and its local job handling while preserving the existing
  seating PDF flow.
