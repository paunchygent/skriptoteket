---
type: task
id: TASK-SKRIPT-REP-0024-PART-02
title: Solver-owned rule marker semantics — part 02
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: TASK-SKRIPT-REP-0024
part: 2
---

- Added a focused diagnostic freshness helper that builds a canonical SHA-256
  key from diagnostic schema version, draft id/revision, smart-rule
  revision/shape, template seat/furniture shape, roster/student ids, and sorted
  seat assignments.
- Extended `SmartRuleDiagnosticDto` with additive `freshness_key` and attached
  the key to authenticated Smart-run diagnostics, public Smart-run diagnostics,
  and authenticated seating-workspace reload diagnostics.
- `GET /drafts/{draft_id}/workspace` now recomputes seating rule diagnostics
  from current persisted truth instead of persisting diagnostic blobs in draft
  data. Grouping workspaces return an empty diagnostic list and do not touch the
  smart-rule repository.
- Frontend workspace hydration now applies returned `rule_diagnostics`; local
  workspace clears and save acknowledgements without diagnostics neutralize
  stored diagnostic colors.
- Soft-rule marker coloring now requires a backend freshness key plus current
  rule kind/student-shape and current student-seat assignment matches. Missing
  freshness renders neutral, so stale transient diagnostics cannot keep coloring
  after reload or local edits.
- Regenerated OpenAPI frontend types with `pdm run fe-gen-api-types`; generated
  `openapi.d.ts` now includes `rule_diagnostics` on workspace responses and
  `freshness_key` on diagnostic DTOs.

Public/guest decision:

- Public Smart-run responses now carry the same freshness key.
- A new stateless public diagnostic-rehydrate endpoint is intentionally not
  introduced in this slice because the current reported reload issue is the
  authenticated persisted-draft workspace. Browser-owned public snapshots
  should remain neutral unless they pass through a backend Smart-run or an
  explicitly scoped future public rehydrate API.

Additional verification:

- `pdm run pytest tests/unit/application/apps/classroom_planner/test_smart_rule_diagnostic_freshness.py tests/unit/application/apps/classroom_planner/test_draft_workspace_diagnostics.py tests/unit/web/apps/classroom_planner/test_draft_workspace_api.py tests/unit/web/apps/classroom_planner/test_smart_seating_api.py -q`
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_workspace_diagnostics.py -q`
- `pdm run fe-test -- --run classroomPlannerSeatRuleMarkers classroomPlannerStateSupport useAnchoredRoomViewportZoom useRoomTouchViewportGestures PlannerPhoneClassroomSeatMap`
- `pdm run fe-gen-api-types`
- `pdm run typecheck`

## Impact And Escalation

The migrated source records no separate statement for this section.

## Decision And Assumption Ledger

The migrated source records no separate statement for this section.

## Plan

The migrated source records no separate statement for this section.

## Implementation Steps

The migrated source records no separate statement for this section.

## Proof

The migrated source records no separate statement for this section.

## Validation

The migrated source records no separate statement for this section.

## Stop Conditions

The migrated source records no separate statement for this section.

## Lessons Learned

The migrated source records no separate statement for this section.

## Notes

The migrated source records no separate statement for this section.

## Readiness

The migrated source records no separate statement for this section.

## Closeout

The migrated source records no separate statement for this section.
