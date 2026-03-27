---
type: pr
id: PR-0154
title: "Klassrumskartan: smart seating v1 backend run, use-history gating, and teacher-edge placement"
status: ready
owners: "agents"
created: 2026-03-27
updated: 2026-03-27
stories:
  - "ST-27-03"
tags:
  [
    "backend",
    "frontend",
    "api",
    "planner",
    "smart-assignment",
    "klassrumskartan",
    "seating",
    "history",
  ]
dependencies:
  - "ADR-0074"
  - "EPIC-27"
  - "PR-0149"
  - "PR-0150"
  - "PR-0151"
  - "PR-0152"
acceptance_criteria:
  - "Given the teacher is in `Sittplatser` and `Smart` is `off`, when they use `Slumpa`, then seating remains the current local random reshuffle behavior."
  - "Given the teacher is in `Sittplatser` and `Smart` is `on`, when they use `Slumpa`, then the planner calls one backend-owned smart seating run endpoint and persists the returned seating result instead of performing a frontend-only random shuffle."
  - "Given the teacher reruns smart seating with `Smart` still `on`, when multiple strong rule-respecting seating candidates exist, then the backend prefers a materially different valid result over repeating the current assignment hash."
  - "Given the seating workspace shows smart controls, when the teacher enables or disables `Use history`, then that toggle persists draft-locally and participates in the backend run contract."
  - "Given `Use history` is enabled and no eligible seating checkpoints exist for the draft roster and normalized room context, when the teacher tries to run smart seating, then the run is blocked with one short teacher-facing explanation and the draft assignments stay unchanged."
  - "Given roster-global `Keep apart`, `Keep near`, and `Närmare läraren` rules exist, when smart seating runs, then the backend result applies those rules best-effort without exposing weights, score tables, or solver jargon."
  - "Given room-owned teaching cues exist, when smart seating evaluates teacher distance, then it infers the teaching edge from `Whiteboard` and `Kateder`; if no stronger cue exists, then the default anchor is top-middle in the standard planner view."
  - "Given eligible seating checkpoints exist and `Use history` is enabled, when smart seating runs, then those checkpoints are the only history source used for teacher-distance fairness over time."
  - "Given the room or rule set makes a perfect result impossible, when smart seating completes, then the best available seating is still returned together with one short teacher-facing message rather than a hard failure."
---

## Problem

`ST-27-03` is now the next active smart-assignment slice, but the planner still has one crucial
gap: the visible seating smart-rule surface exists, while the actual `Slumpa` action still performs
frontend-only random assignment.

That leaves the repo in an in-between state:

- teachers can author roster-global smart rules, but those rules do not yet drive seating results
- `Smart` is visible in the seating workspace, but it does not yet switch the planner onto a
  backend-owned smart run
- export-backed checkpoints now exist, but the seating workspace has no honest `Use history` flow
- teacher-distance fairness, teacher-edge inference, and no-history blocking remain accepted in
  docs but unshipped in behavior

Without this slice, smart seating remains a half-visible affordance instead of a trustworthy V1
workflow.

## Goal

Ship one complete vertical smart-seating V1 slice that keeps the teacher surface intentionally
small while making smart seating real end-to-end:

- keep `Slumpa` as the seating action
- keep current local random behavior when `Smart` is `off`
- call one backend-owned smart seating run when `Smart` is `on`
- add the missing teacher-facing `Use history` control in the seating workspace
- consume roster-global smart rules plus export-backed checkpoints only
- infer the teaching edge from room fixtures with a safe default
- return one short teacher-facing message, not solver internals

## Non-goals

- Implementing smart grouping; that remains `ST-27-04`.
- Adding a separate alternate-result button or a teacher-facing randomness setting; rerun diversity
  remains part of the core smart-run contract, while longer explanation polish remains `ST-27-05`.
- Building a generic reusable solver framework beyond this seating slice.
- Adding a teacher-facing checkpoint browser, score panel, or debug surface.
- Reopening rule-authoring semantics already shipped in `PR-0149`, `PR-0151`, and `PR-0152`.
- Treating draft autosave, undo/redo, or abandoned drafts as history inputs.

## Implementation plan

1. Lock the run contract and pure smart-seating rules in tests first.
   - Add pure domain tests for teaching-edge inference.
   - Add pure domain tests for seating objectives:
     - `Keep apart` avoids direct orthogonal adjacency where possible.
     - `Keep near` prefers one local vicinity rather than one exact pair shape.
     - `Närmare läraren` prefers seats closer to the inferred teaching edge.
     - history fairness softens repeated teacher-distance bias across eligible checkpoints.
     - repeated smart reruns prefer a different strong candidate when one exists instead of
       collapsing onto the current assignment hash.
   - Add application tests for no-history blocking, best-effort fallback, and checkpoint-only
     history sourcing.

2. Add the backend smart-seating run seam.
   - Introduce one pure smart-seating domain module for:
     - teaching-edge inference
     - seat distance ranking
     - relationship-cluster scoring
     - history-based teacher-distance fairness
     - diversity-aware rerun behavior that prefers a different strong candidate from the current
       arrangement when possible
   - Add one application handler that loads:
     - the seating draft workspace
     - roster-global smart rules
     - eligible seating checkpoints for the same roster and normalized room context
   - Reject or block clearly when the smart run cannot proceed honestly, especially:
     - `Smart` disabled
     - `Use history` enabled with no eligible checkpoints
   - Persist the chosen seating result back through the draft workspace so undo/redo and autosave
     remain truthful.

3. Extend the checkpoint repository seam for fairness-over-time.
   - Keep `PR-0150` dedupe semantics intact.
   - Add one protocol/repository read path with explicit eligibility semantics for smart seating:
     - same `roster_id`
     - same normalized `room_context_hash`
     - export-success checkpoints only
     - newest first
     - capped to the most recent 12 checkpoints
   - Latest-only lookup remains sufficient for export dedupe, but smart seating fairness must read
     that explicit ordered history window instead of all historical checkpoints or roster-wide
     checkpoints from unrelated room geometry.
   - Keep this protocol-first and repository-owned; do not leak SQLAlchemy concerns into the
     handler.

4. Add the bespoke web/API contract.
   - Add one seating-only endpoint for backend smart runs:
     - `POST /api/v1/apps/classroom.group-seating-studio/drafts/seating/{draft_id}/smart-run`
   - Request body:
     - `expected_revision: int`
   - `200` success response:
     - `status: "applied"`
     - `workspace: DraftWorkspaceResponse`
     - `used_history: bool`
     - `message: str | null`
   - `200` blocked business response for honest no-history gating:
     - `status: "blocked"`
     - `reason: "no_history"`
     - `message: str`
     - `workspace: null`
     - `used_history: false`
   - Reserve HTTP error responses for true failure conditions rather than teacher-facing run
     outcomes:
     - `404` when the seating draft does not exist or is not owner-visible
     - `409` when `expected_revision` is stale
     - `422` for malformed request payloads
   - Map domain/application errors to those thin HTTP responses in the web layer only.

5. Wire the seating workspace onto the smart run without reopening the planner shell.
   - Add a draft-local `Use history` control in the seating workspace.
   - Keep the current `Smart` toggle and current visible rule surface.
   - Branch `Slumpa`:
     - `Smart` off -> current local random behavior
     - `Smart` on -> backend smart seating run
   - Keep rerun semantics on the same `Slumpa` control; do not add a second alternate-result
     action.
   - Show one short result message or one short no-history block in the seating workspace.
   - Keep the frontend authoritative only for orchestration and display, not solver behavior.

## Acceptance criteria mapping by tranche

- Tranche 1: contract and pure domain behavior
  - covers acceptance criteria 5, 6, 7, and 8
- Tranche 2: application handler + checkpoint-history seam + API
  - covers acceptance criteria 2, 4, 7, and 8
- Tranche 3: seating UI controls + planner-state wiring
  - covers acceptance criteria 1, 2, 3, and 4
- Tranche 4: integrated proof and close-out
  - re-validates all acceptance criteria end-to-end, especially the `Smart` off/on branch and the
    honest no-history block

## Story acceptance traceability (`ST-27-03`)

- Criterion 1:
  - implemented in `PR-0154`
  - proof: `Slumpa` branches cleanly and keeps current local random behavior when `Smart` is off
- Criterion 2:
  - implemented in `PR-0154`
  - proof: `Slumpa` calls the backend smart-seating run endpoint when `Smart` is on
- Criterion 3:
  - implemented in `PR-0154`
  - proof: backend smart seating consumes roster-global smart rules plus draft-local `Use history`
- Criterion 4:
  - already satisfied by `PR-0149`
  - regression-verified in `PR-0154`
  - proof: seating smart-rule authoring still works through the class-wide visible surface
- Criterion 5:
  - already satisfied by `PR-0149` and `PR-0151`
  - regression-verified in `PR-0154`
  - proof: overlapping visible relationship clusters remain blocked
- Criterion 6:
  - already satisfied by `PR-0151` and preserved through `PR-0152`
  - regression-verified in `PR-0154`
  - proof: roster-global smart rules remain available across seating drafts for the same class
- Criterion 7:
  - implemented in `PR-0154`
  - proof: smart seating scores `Keep apart` as a strong best-effort anti-adjacency objective
- Criterion 8:
  - implemented in `PR-0154`
  - proof: smart seating scores `Keep near` as a local-vicinity objective
- Criterion 9:
  - implemented in `PR-0154`
  - proof: eligible seating checkpoints drive teacher-distance fairness over time for students
    without `Närmare läraren`
- Criterion 10:
  - implemented in `PR-0154`
  - proof: teacher-distance uses `Whiteboard` / `Kateder` cues, else top-middle fallback
- Criterion 11:
  - implemented in `PR-0154`
  - proof: history comes only from explicit eligible checkpoints, never from draft autosave or
    undo/redo state
- Criterion 12:
  - implemented in `PR-0154`
  - proof: history-enabled smart seating blocks honestly when no eligible checkpoints exist
- Criterion 13:
  - implemented in `PR-0154`
  - proof: the best available seating plus one short teacher-facing message is returned instead of
    a hard failure

## Files expected to change

- `src/skriptoteket/domain/curated_apps/classroom_planner/checkpoints.py`
- `src/skriptoteket/domain/curated_apps/classroom_planner/models.py`
- new smart-seating domain module under `src/skriptoteket/domain/curated_apps/classroom_planner/`
- `src/skriptoteket/protocols/classroom_planner.py`
- new handler module under `src/skriptoteket/application/curated_apps/classroom_planner/handlers/`
- `src/skriptoteket/application/curated_apps/classroom_planner/__init__.py`
- `src/skriptoteket/web/api/v1/apps_classroom_planner_seating.py`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerTypes.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerSmartRuleActions.ts`
- `frontend/apps/skriptoteket/src/views/apps/useClassroomState.ts`
- optional small frontend orchestration module under `frontend/apps/skriptoteket/src/views/apps/`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingSmartRuleSurface.vue`
- new or updated tests under `tests/unit/` and `frontend/apps/skriptoteket/src/views/apps/`

## PR-sized execution checklist

- [ ] Add domain tests for teaching-edge inference and rule-aware seat scoring
- [ ] Add application tests for smart-run success, no-history blocking, and checkpoint-only history
- [ ] Extend the checkpoint protocol/repository seam for eligible history lookup
- [ ] Add the backend smart-seating handler and thin seating API endpoint
- [ ] Persist smart-run results back into the draft workspace with optimistic safety
- [ ] Add the seating `Use history` UI control and persist it draft-locally
- [ ] Wire the seating `Slumpa` action to branch between local random and backend smart run
- [ ] Show short teacher-facing success/block messages in the seating workspace
- [ ] Regression-verify the already-shipped smart-rule authoring surface, overlap blocking, and
  cross-draft roster-global rule reuse
- [ ] Re-run verification and record manual proof steps in `.agents/handoff.md`

## Test plan

- `pdm run pytest tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_teacher_edge.py tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_solver.py -q`
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_smart_seating.py -q`
- `pdm run pytest tests/unit/web/apps/classroom_planner/test_smart_seating_api.py -q`
- `pdm run pytest tests/unit/infrastructure/repositories/test_classroom_planner_seating_export_checkpoints.py -q`
- `pdm run fe-test -- --run src/views/apps/useClassroomState.spec.ts src/views/apps/useRosterSmartRuleLane.spec.ts src/views/apps/useSmartSeatingRun.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- `ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local`
- `pdm run python -m scripts.playwright_pr_0154_smart_seating_check --base-url http://127.0.0.1:5173`

## Rollback plan

- Revert the backend smart-seating handler, API route, checkpoint-history read seam, and seating UI
  wiring together if the run contract is found to be incorrect.
- Do not fall back to draft autosave, undo/redo, or abandoned drafts as substitute history
  sources.
- If the solver behavior proves too weak or too opaque, keep the docs trail and acceptance mapping
  intact so the next slice can improve scoring without reintroducing the wrong history model or
  the old solver-era surface.
