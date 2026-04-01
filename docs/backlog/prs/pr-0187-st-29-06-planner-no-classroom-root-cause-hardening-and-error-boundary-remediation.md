---
type: pr
id: PR-0187
title: "ST-29-06 remediation: planner no-classroom root-cause hardening and error-boundary refactor"
status: ready
owners: "agents"
created: 2026-04-01
updated: 2026-04-01
stories:
  - "ST-29-06"
tags: ["frontend", "klassrumskartan", "rules", "resilience", "architecture"]
dependencies:
  - "EPIC-29"
  - "PR-0152"
  - "PR-0155"
  - "PR-0185"
acceptance_criteria:
  - "Given a teacher enters `Regler` with a class selected and no classroom selected, when the planner resolves or resumes the seating host draft, then the route shell opens the intended no-classroom rules state instead of failing back to `Översikt`."
  - "Given the planner receives valid but thin payloads for catalog, class summary, workspace, or smart rules, when optional collection fields are omitted or empty, then the frontend normalizes them at the route/API boundary and no planner surface crashes."
  - "Given an unexpected frontend runtime exception still occurs anywhere in the Klassrumskartan planner flow, when the message reaches a user-facing system banner or status surface, then the teacher sees approved fallback copy rather than raw JavaScript or framework internals."
  - "Given the root-cause path is fixed, when focused browser proof is rerun at `1366x768` and `1440x900`, then the approved no-classroom `Regler` empty-map state renders and the organized off-map roster remains actionable."
  - "Given the remediation is reviewed, when implementation is proposed for release, then the diff includes a documented contract boundary for planner response normalization and a narrow explanation of why the earlier slice still leaked the runtime failure."
---

## Problem

`PR-0185` shipped the intended no-classroom `Regler` copy and off-map roster presentation, but a
later production/local verification pass showed that the live flow can still fail before the
rules workspace mounts. In the failing path the backend returns a valid no-classroom draft/workspace
state, yet the frontend surfaces `Cannot read properties of undefined (reading 'map')` and leaves
the user in `Översikt`.

That means the current planner architecture still has a boundary weakness:

- valid no-classroom states are not normalized consistently before entering route-shell and store flows
- one or more planner transitions still assume collection shape too late in the stack
- raw runtime error text can still leak into teacher-facing banners when a later layer rethrows or
  rewraps the failure

The current defensive guard patch is valuable, but it is not yet a proven root-cause fix.

## Verified Root Cause (2026-04-01)

The final local reproduction split the issue into two separate seams:

1. Runtime alignment:
   - the canonical local proof command against `http://127.0.0.1:5173` authenticated through the
     backend and then loaded the backend-served static SPA bundle from `:8000`, not the live Vite
     module graph
   - before rebuilding the SPA, that backend-served bundle was stale relative to the current local
     source tree, which kept the earlier raw `Cannot read properties of undefined (reading 'map')`
     banner and `Översikt` fallback behavior alive even after the source-level hardening existed
   - after `pdm run fe-build`, the rebuilt backend-served bundle picked up the current
     normalization and error-suppression changes, and the raw runtime banner no longer reproduced

2. Rules-map contract:
   - once the runtime was aligned, the planner no longer failed back to `Översikt`; it entered the
     intended `Regler` workspace and the backend payloads remained valid for the no-classroom draft
     path (`workspace-summary`, `drafts/resolve`, `draft workspace`, and `smart-rules`)
   - the remaining live failure was that `PlannerRulesMapCanvas.vue` only rendered the approved
     no-classroom guidance in the classroom-faithful seating branch, while the default
     `Planeringsvy` branch showed the organized roster surface without `[data-test="rules-map-empty-state"]`
   - the planning-view eyebrow also regressed to `Ej på karta`, which is semantically wrong for
     the abstract class roster view; `Planeringsvy` must stay labeled with the active class name,
     while `Ej på karta` remains reserved for `Klassrumsvy`

The verified remediation therefore kept the route/lifecycle normalization hardening in place, but
landed the final user-visible fix narrowly in the rules-map seam.

## Goal

Deliver a root-cause remediation slice for the Klassrumskartan planner boundary so that:

- no-classroom rules entry is reliable in the live route flow
- planner API payload normalization is explicit and centralized
- teacher-facing error surfaces are protected by a proper planner-specific error boundary
- the final explanation is architecture-first rather than “added more guards”

## Non-goals

- No redesign of the rules workspace layout or copy beyond what `PR-0185` already approved.
- No smart-rule product-scope changes.
- No backend behavior changes unless the investigation proves the frontend contract is genuinely wrong.
- No broad cross-app error-boundary rollout outside Klassrumskartan in this slice.

## Implementation plan

1. Reproduce the failing live no-classroom `Regler` entry path with a capture that includes the
   exact throw site and the corresponding workspace/summary payloads.
2. Identify the root-cause planner seam:
   - route-shell orchestration
   - lifecycle hydration
   - store support normalization
   - rules workspace mount path
3. Move planner response normalization to one documented boundary instead of relying on downstream
   ad hoc cloning/guarding.
4. Introduce a planner-specific user-facing error-boundary rule so raw JS/framework/runtime text
   cannot appear in banners, workspace notices, or planner status strips.
5. Add focused regression coverage for:
   - thin payload normalization
   - no-classroom `Regler` entry success
   - suppression of raw runtime text
   - live browser proof at the canonical review viewports
6. Document the verified root cause and why `PR-0185` needed this follow-up despite passing its
   earlier slice-level proof.

## Implementation Summary (as of 2026-04-01)

- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerPayloadNormalization.ts` now
  centralizes planner response normalization for thin optional collections, with focused coverage in
  `classroomPlannerPayloadNormalization.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerStateSupport.ts`,
  `classroomPlannerLifecycle.ts`, `useClassroomPlannerRouteShell.ts`, and
  `classroomPlannerRouteShellErrors.ts` keep the current planner boundary hardening and
  teacher-facing error suppression so valid no-classroom payloads do not surface raw runtime text
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesMapCanvas.vue` now renders the
  approved no-classroom empty-map guidance whenever no classroom template exists, including the
  default `Planeringsvy` entry path, while keeping the planning-view eyebrow tied to the class name
  and reserving `Ej på karta` for `Klassrumsvy`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesMapCanvas.spec.ts` locks the
  no-classroom planning-view contract, and
  `scripts/playwright_pr_0185_rules_no_classroom_fallback_check.py` now proves the live class-name
  eyebrow in `Planeringsvy`

## Verified Evidence (2026-04-01)

- transport/path diagnosis:
  - local API calls for a no-classroom seating draft returned `200` with backend-valid payloads for
    `workspace-summary`, `drafts/resolve`, `draft workspace`, and `smart-rules`
  - focused browser diagnostics confirmed that the failing local `5173` proof had been running
    against the backend-served static SPA bundle until `pdm run fe-build` realigned it
- code verification:
  - `pdm run fe-test -- --run src/views/apps/classroomPlannerPayloadNormalization.spec.ts src/views/apps/classroomPlannerRouteShellErrors.spec.ts src/views/apps/classroomPlannerStateSupport.spec.ts src/views/apps/classroomPlannerRouteShellOverviewCrud.spec.ts src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/PlannerRulesMapCanvas.spec.ts src/views/apps/components/PlannerRulesWorkspacePane.spec.ts`
  - `pdm run fe-type-check`
- live proof:
  - `pdm run fe-build`
  - `pdm run python -m scripts.playwright_pr_0185_rules_no_classroom_fallback_check --base-url http://127.0.0.1:5173` -> `playwright-pr-0185: ok`

## Proposed module focus

- `frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerRouteShell.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerLifecycle.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerStateSupport.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerRouteShellWorkspace.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerRouteShellErrors.ts`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesWorkspacePane.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesMapCanvas.vue`
- focused Vitest coverage around the affected planner seams
- the existing no-classroom Playwright proof under `scripts/`

## Verified findings (2026-04-01)

- The canonical local `http://127.0.0.1:5173` proof does not stay on the Vite runtime after login.
  It authenticates into the backend-served Klassrumskartan route on `:8000`, so `pdm run fe-build`
  is required before trusting local browser-proof results after frontend changes.
- With the current source tree and a rebuilt static SPA bundle, the earlier raw
  `Cannot read properties of undefined (reading 'map')` banner no longer reproduces on the live
  no-classroom `Regler` flow. The route shell now reaches the intended planner state, thin
  workspace/smart-rule payloads normalize safely, and raw runtime/framework text no longer appears
  in the teacher-facing UI for this path.
- The remaining live failure after runtime alignment was a rules-workspace contract mismatch, not a
  pre-mount crash: the approved no-classroom guidance was rendered only in `Klassrumsvy`, while the
  default `Planeringsvy` entry path showed the organized roster without the required empty-state
  explanation. The fix keeps the approved empty-state copy visible whenever no classroom exists,
  while restoring the `Planeringsvy` eyebrow to the class name and reserving `Ej på karta` for the
  seating projection only.
- The sole-reviewer follow-up found one additional boundary gap: stale draft-save acknowledgements
  could still bypass normalization and leave `history_status` undefined. The final implementation
  now normalizes that acknowledgement path through the same workspace helper used during hydration.

## Test plan

- `pdm run fe-test -- --run src/views/apps/classroomPlanner*.spec.ts src/views/apps/ClassroomPlannerView.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- Focused live proof against `http://127.0.0.1:5173`:
  - create/select a class with no classroom
  - enter `Regler`
  - confirm the approved empty-map state renders
  - confirm no raw runtime/internal text appears anywhere in the UI
  - recheck `1366x768` and `1440x900`

## Verification notes (2026-04-01)

- `pdm run fe-test -- --run src/views/apps/classroomPlannerPayloadNormalization.spec.ts src/views/apps/classroomPlannerRouteShellErrors.spec.ts src/views/apps/classroomPlannerStateSupport.spec.ts src/views/apps/classroomPlannerRouteShellOverviewCrud.spec.ts src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/PlannerRulesMapCanvas.spec.ts src/views/apps/components/PlannerRulesWorkspacePane.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`
- `pdm run python -m scripts.playwright_pr_0185_rules_no_classroom_fallback_check --base-url http://127.0.0.1:5173` -> `playwright-pr-0185: ok`
- `pdm run docs-validate`
- Independent `skriptoteket_reviewer` loop:
  - first sole-reviewer pass found the stale draft-save acknowledgement normalization gap
  - `skriptoteket_implementation_specialist` fixed that slice in `classroomPlannerStateSupport.ts`
    and `classroomPlannerStateSupport.spec.ts`
  - the final sole-reviewer rerun returned no actionable findings

## Rollback plan

- Revert only the remediation boundary changes if they introduce planner regressions, while keeping
  the already approved teacher-facing no-classroom copy and organized off-map roster UI from
  `PR-0185`.
- Preserve route-shell/planner separation and use the documented root-cause notes to guide a
  narrower retry if the first remediation attempt overreaches.
