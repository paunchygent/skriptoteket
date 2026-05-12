---
type: pr
id: PR-0316
title: "ST-27-05: Smart history first-run soft-degrade"
status: done
owners: "agents"
created: 2026-05-11
updated: 2026-05-11
stories:
  - "ST-27-05"
tags: ["backend", "frontend", "api", "ux", "klassrumskartan", "smart", "history"]
dependencies:
  - "PR-0154"
  - "PR-0167"
  - "PR-0305"
  - "PR-0307"
  - "PR-0308"
acceptance_criteria:
  - "Given an authenticated seating draft has `Smart placering` and `Historik` enabled but no eligible seating checkpoints for the selected classroom, when the teacher clicks `Slumpa`, then Smart seating applies a result, returns `used_history=false`, and no no-history warning or blocked run is shown."
  - "Given an authenticated grouping draft has `Smart placering` and `Historik` enabled but no eligible grouping checkpoints, when the teacher clicks `Slumpa`, then Smart grouping applies a result, returns `used_history=false`, and no no-history warning or blocked run is shown."
  - "Given eligible seating or grouping export/share checkpoints exist, when `Historik` is enabled and Smart runs for the matching roster/context, then the existing checkpoint-history window is loaded, `used_history=true` is returned, and history-aware solver behavior remains covered."
  - "Given no eligible checkpoints exist, when Smart soft-degrades, then draft autosave, undo/redo history, active or historic draft rows, history-drawer drafts, and public guest local state are not used as Smart-history substitutes."
  - "Given public guest Smart runs, when this slice lands, then account-backed `Historik` remains omitted/off and guest no-history semantics do not change."
  - "Given `no_history` is the only blocked smart-run business result, when this slice lands, then the seating/grouping blocked response variants are removed from backend, OpenAPI, generated frontend types, and frontend run handling; real failures remain explicit HTTP errors."
  - "Given docs mention Smart-history no-checkpoint behavior, when this slice closes, then EPIC-27, ST-27-03, ST-27-04, ST-27-05, the Smart decision memo, and stale PR-0307 status wording are reconciled."
---

## Problem

Authenticated `Smart placering` and `Historik` are now default-on unless the
teacher opts out. That is the right product default because history and the
solver together reduce repeated seating/grouping outcomes, but it turns the
first run into a normal empty-history case.

Today the backend treats `Historik` + no eligible checkpoints as a blocked run.
For a first-time teacher, that reads like something is broken even though the
only missing input is a future export/share checkpoint.

## Goal

Make the first Smart run calm and useful:

- keep authenticated `Historik` default-on
- run Smart seating/grouping without history when no eligible checkpoint exists
- report `used_history=false` for that run
- show normal Smart result feedback rather than a no-history warning
- keep history source boundaries strict: export/share checkpoints only

## Resolved Questions

- Keep `Historik` default-on for authenticated users? Yes. The first-run fix is
  backend soft-degrade, not weakening the default.
- Show a first-run warning or one-time education toast? No. `Slumpa` should look
  successful when Smart can produce a result. Export/share education belongs in
  calmer help copy later, not in an error-like run response.
- Use historic drafts, undo/redo, autosave history, or active draft rows as a
  fallback source? No. The solver may run without history, but it must not
  broaden the history definition.
- Remove the blocked response DTO now? Yes, if code inspection confirms
  `no_history` is the only blocked business result. Delete the stale blocked
  backend result/DTO, OpenAPI union branch, generated frontend type branch, and
  composable handling. If another valid blocked business state exists, stop and
  document that state instead of silently keeping a generic union.
- Change public guest behavior? No. Public guest Smart remains browser-local and
  account-backed `Historik` stays omitted/off.
- Change grouping `Sittschemat` / live seating influence? No. Seating
  compactness remains a separate grouping input and is not grouping history.

## Non-goals

- No solver-weight redesign.
- No teacher-facing checkpoint browser.
- No use of draft history as Smart history.
- No public guest account-backed history.
- No stale compatibility branch for `no_history`; this slice owns the OpenAPI
  and generated-type cleanup caused by removing that obsolete blocked result.
- No new Smart settings copy beyond removing the erroneous no-history warning
  path from normal first-run behavior.

## Implementation Plan

1. Update Smart seating application flow.
   - In `RunSmartSeatingHandler`, remove the `use_history and not history`
     business block.
   - Continue passing an empty checkpoint list to the solver when no eligible
     history exists.
   - Keep `used_history=bool(history)` so first-run soft-degrade is explicit.
   - Delete or narrow the seating no-history block constant/tests if no longer
     used.

2. Update Smart grouping application flow.
   - In `RunSmartGroupingHandler`, remove the `use_history and not history`
     business block.
   - Keep live seating / seating compactness behavior unchanged.
   - Keep grouping history separate from seating compactness and report
     `used_history=bool(history)`.
   - Delete or narrow the grouping no-history block constant/tests if no longer
     used.

3. Remove the stale blocked response contract.
   - Confirm whether authenticated smart-run blocked result classes only
     represent `reason: "no_history"`.
   - If they do, delete the blocked result classes, web/API response variants,
     OpenAPI union branches, generated frontend type branches, and frontend
     composable handling.
   - Regenerate OpenAPI and TypeScript API types in the same slice.
   - Ensure no-checkpoint first runs return `status: "applied"` with
     `used_history=false`.
   - Leave `404`, `409`, `422`, and real validation/conflict errors as HTTP
     failures, not smart-run business payloads.
   - Stop and amend this task if implementation finds a still-valid blocked
     business state unrelated to history availability.

4. Update frontend run handling and tests.
   - Do not add a frontend workaround. The backend should return the applied
     workspace.
   - Update seating/grouping composable specs so first-run no-history results
     use normal success feedback and workspace mutation.
   - Remove seating/grouping no-history blocked-response handling when the union
     branch is deleted.

5. Add live proof.
   - Use the repo's HuleEdu browser-session helper/preflight.
   - Prove an authenticated first seating run and first grouping run with Smart
     + `Historik` on, no checkpoints, no warning, and applied workspace changes.
   - Prove an authenticated run after export/share checkpoint creation still
     reports `used_history=true`.

## Test Plan

- `pdm run pytest tests/unit/application/apps/classroom_planner/test_smart_seating.py tests/unit/application/apps/classroom_planner/test_smart_grouping.py -q`
- `pdm run pytest tests/unit/web/apps/classroom_planner/test_smart_seating_api.py tests/unit/web/apps/classroom_planner/test_smart_grouping_api.py -q`
- `pdm run openapi-export-v1`
- `npm --prefix frontend/apps/skriptoteket run gen:api-types`
- `pdm run fe-test -- --run useSmartSeatingRun useSmartGroupingRun classroomPlannerSmartPreferences PlannerWorkspaceShell`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run lint`
- `pdm run typecheck`
- `pdm run python -m scripts.playwright_pr_0316_smart_history_first_run_soft_degrade --base-url http://127.0.0.1:5173`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Implementation Summary

- Authenticated Smart seating/grouping no longer return a business-level
  `blocked/no_history` result. Empty eligible checkpoint windows now call the
  existing solver with an empty history list and return `status: "applied"` plus
  `used_history=false`.
- The stale authenticated blocked backend result classes, web response DTOs,
  OpenAPI union branches, generated TypeScript branches, and authenticated SPA
  endpoint-result handling were removed. Public guest Smart keeps its
  public-only blocked response types unchanged.
- Backend, web, and SPA tests now cover first-run no-history success and assert
  authenticated response models are applied-only.
- `scripts/playwright_pr_0316_smart_history_first_run_soft_degrade.py` proves
  the browser-authenticated contract end to end: first run without checkpoints
  soft-degrades, share creation records a checkpoint, and the next draft reports
  `used_history=true` for both seating and grouping. The script deletes any
  stale failure screenshot at startup so a successful rerun does not carry a
  misleading old failure artifact.

## Verification

- `pdm run fe-gen-api-types`
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_smart_seating.py tests/unit/application/apps/classroom_planner/test_smart_grouping.py tests/unit/web/apps/classroom_planner/test_smart_seating_api.py tests/unit/web/apps/classroom_planner/test_smart_grouping_api.py -q`
- `pdm run fe-test -- --run useSmartSeatingRun useSmartGroupingRun classroomPlannerSmartPreferences PlannerWorkspaceShell`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run lint`
- `pdm run typecheck`
- `pdm run pytest tests/unit/scripts/test_playwright_script_surface.py -q`
- `pdm run python -m scripts.playwright_pr_0316_smart_history_first_run_soft_degrade --base-url http://127.0.0.1:5173`
  wrote
  `.artifacts/playwright-pr-0316-smart-history-first-run/summary.json` with
  first-run `used_history=false` and follow-up `used_history=true` for seating
  and grouping.
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback Plan

Restore the backend no-history block, blocked response variants, OpenAPI branch,
generated frontend type branch, and corresponding frontend blocked-response
expectations together. Do not replace the backend source boundary with draft
history fallback; if this slice rolls back, Smart history remains
checkpoint-only and first-run behavior returns to the previous block.
