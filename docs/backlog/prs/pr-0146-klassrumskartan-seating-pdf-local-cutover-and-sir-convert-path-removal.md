---
type: pr
id: PR-0146
title: "Klassrumskartan: seating PDF local cutover and Sir Convert path removal"
status: done
owners: "agents"
created: 2026-03-26
updated: 2026-03-26
stories:
  - "ST-26-01"
tags: ["backend", "frontend", "pdf", "klassrumskartan", "export", "cleanup"]
dependencies:
  - "ADR-0075"
  - "PR-0119"
  - "PR-0121"
  - "PR-0124"
  - "PR-0125"
  - "PR-0141"
acceptance_criteria:
  - "Given a teacher exports the current seating draft as `Affisch (A3)`, when the PDF artifact is generated, then Skriptoteket renders and finalizes it locally from the seating poster renderer instead of delegating final conversion to Sir Convert-a-Lot."
  - "Given the seating PDF export path is migrated locally, when the backend executes the export, then no seating-specific Sir Convert webhook onboarding, callback dispatch, subscription reconciliation, or upstream job polling remains on the final artifact path."
  - "Given the seating export action already ships, when the cutover lands, then the teacher-facing behavior remains stable: `Affisch (A3)` stays the default seating action, `Excel (.xlsx)` stays the secondary option, and existing draft-scoped export ownership/download semantics still work."
  - "Given the seating poster uses the shared Skriptoteket branding assets, when the teacher opens the exported PDF, then the letterhead/logo renders correctly from the local renderer-owned asset path on the host `127.0.0.1:5173` lane."
  - "Given the local cutover is complete, when obsolete code is reviewed, then the seating-specific Sir Convert artifact path is deleted without compatibility shims in Skriptoteket, including the seating callback route, webhook reconciliation command/runbook references, and seating-only Sir Convert smoke assumptions."
---

## Problem

Seating PDF is the remaining Klassrumskartan export artifact that still crosses the Sir Convert
service boundary even though the artifact is renderer-owned inside Skriptoteket.

That old path adds complexity that the product no longer wants:

- external job submission
- seating-specific webhook and callback plumbing
- subscription reconciliation and recoverability logic tied to the external converter
- trust-mode and upstream auth coupling for a document that already has a local renderer

Grouping PDF has already proven the cleaner model: render locally, persist to Vault, and keep the
teacher-facing export job boundary inside Skriptoteket.

## Goal

Cut seating PDF over to the same local render/finalize model as grouping PDF and delete the
obsolete seating-specific Sir Convert final-artifact path entirely.

## Non-goals

- Changing the existing seating PDF default behavior or layout contract.
- Redesigning the teacher-facing export menu or the `Affisch (A3)` copy.
- Reopening grouping PDF or the grouping/export workbook slices.
- Preserving backwards-compatible shims for the old seating-specific Sir Convert path.
- Replacing Sir Convert usage for class-list import PDF extraction or Conversion Hub workloads.
- Fixing Conversion Hub local job-ledger/auth concerns; those remain separate from this seating cutover.

## Implementation plan

1. Build the local seating PDF finalization path:
   - route seating poster HTML/CSS into the same in-process PDF rendering posture already proven by
     the grouping PDF lane
   - finalize the artifact directly into Vault from Skriptoteket
2. Remove the obsolete seating-specific external final-artifact orchestration:
   - delete seating-only Sir Convert submission/callback/subscription code from the final PDF path
   - delete the seating-specific callback route and dispatcher wiring that exist only for the old
     external seating-PDF artifact path
   - delete seating-specific webhook reconciliation command/runbook references that are no longer
     valid after local cutover
   - delete seating-only Sir Convert readiness/smoke assumptions from local verification docs
   - keep only the draft-scoped local ownership/download ledger that the teacher-facing flow still
     needs
3. Preserve the stable teacher UX:
   - keep `Affisch (A3)` as the default seating action
   - keep `Excel (.xlsx)` as the secondary menu option
   - keep `Ladda ned igen` and draft-scoped recovery semantics
4. Verify the local asset path end to end on the host lane:
   - prove the logo/letterhead renders through the local path on
     `http://127.0.0.1:5173/apps/classroom.group-seating-studio`
5. Update docs/handoff to reflect the new boundary and the deleted external path

## Explicit removal targets

- Seating-specific callback/webhook route(s) used only by the old external seating-PDF artifact path
- Seating-specific webhook dispatcher/reconciliation logic
- Seating-only Sir Convert readiness/smoke expectations in docs/runbooks
- Seating-only upstream job/subscription assumptions that no longer belong on the final artifact path

## Test plan

- `pdm run pytest tests/unit/application/apps/classroom_planner/test_seating_export_jobs.py tests/unit/application/apps/classroom_planner/test_seating_export_job_completion.py tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_poster_renderer.py tests/unit/web/apps/classroom_planner/test_seating_export_job_api.py`
- `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/components/PlannerExportActionGroup.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.export.spec.ts src/views/apps/useSeatingExportFlow.spec.ts`
- `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit`
- `pdm run docs-validate`
- live proof on `http://127.0.0.1:5173/apps/classroom.group-seating-studio`:
  - export default seating PDF
  - confirm local success/download
  - confirm branding renders correctly
  - confirm `Excel (.xlsx)` still works as the secondary seating action

## Rollback plan

- Restore the prior seating PDF export path only if the local cutover fails and only as an explicit
  revert of this PR.
- Keep grouping PDF, seating XLSX, and grouping XLSX on their current local lanes.
