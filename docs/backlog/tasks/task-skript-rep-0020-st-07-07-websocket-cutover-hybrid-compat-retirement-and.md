---
type: task
id: TASK-SKRIPT-REP-0020
title: 'ST-07-07: websocket cutover, hybrid compat retirement, and production proof'
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: orchestrator
  decided_at: '2026-10-28'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'TASK-SKRIPT-REP-0020#closeout'
task_kind: repository
acceptance_criteria:
  - Given websocket endpoints still require DI, when this slice ships, then they use explicit websocket-aware resolution rather than the HTTP hybrid fallback.
  - Given HTTP routes are already migrated, when this slice ships, then `dishka_compat.py` is removed instead of retained as dead compatibility code.
  - Given Hemma production is redeployed after the full cutover, when verification runs, then the web container becomes healthy and the deploy gate plus production health proof both pass.
backlog_document_profile: contract-derived
---

## Implementation Contract

Closed as done on 2026-10-28 under TASK-SKRIPT-REP-0055 D1 on merge evidence. The original contract below is kept as history; see Closeout for what shipped and what was not checked.

## Contract Inputs

The source record did not define a separate section for this package heading.

## Core Vertical And Performance

The source record did not define a separate section for this package heading.

## Context

The hybrid layer cannot truly be retired until websocket handling and the remaining route wiring are
moved onto explicit supported paths. Otherwise the repo keeps dead or risky compatibility code even
after the HTTP migration.

## Impact And Escalation

No separate impact and escalation is stated in the source.

## Decision And Assumption Ledger

| source | semantic | carried_forward | Source material is retained in the sections above. | source |

## Plan

1. Migrate websocket-aware handlers to explicit websocket/container resolution.
2. Delete `src/skriptoteket/web/dishka_compat.py` and update imports/usages to the new public
   adapter paths.
3. Re-run local and containerized verification.
4. Redeploy Hemma and prove:
   - healthy web container
   - successful `/healthz`
   - successful seating-export deploy/readiness gate still intact

## Implementation Steps

No separate implementation steps is stated in the source.

## Proof

- targeted pytest for websocket-aware routes and any remaining route wiring
- `tests/test_smoke.py`
- containerized/live route proof including `/healthz`
- Hemma redeploy + health proof
- `pdm run docs-validate`

## Validation

No separate validation is stated in the source.

## Stop Conditions

- If websocket cutover proves unstable, revert the deletion tranche while keeping the earlier HTTP
  migration slices available for re-entry.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                 |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Closed as done on 2026-10-28 on merge evidence confirmed in code and git history (TASK-SKRIPT-REP-0055 D1); the Closeout section lists the evidence and the checks that were not run. |

## Lessons Learned

No separate lessons learned is stated in the source.

## Notes

No separate notes is stated in the source.

### Source: Goal

Finish the migration, delete the hybrid compatibility layer, and re-prove the full production web
readiness path on Hemma.

### Source: Non-goals

- New product features.
- Additional DI/provider redesign beyond what is needed to remove the hybrid layer.

### Source: References

- Story parent: [ST-07-07](../stories/story-07-07-retire-hybrid-dishka-fastapi-compatibility-layer-and-restore-supported-web-di.md)
- HTTP migration slice: [PR-0163](pr-0163-st-07-07-http-route-dependency-cutover-off-hybrid-dishka-inject.md)

## Readiness

No separate readiness is stated in the source.

## Closeout

No separate closeout is stated in the source.

## Closeout

Closed as done on 2026-10-28 under TASK-SKRIPT-REP-0055 D1 (orchestrator closeout on merge evidence).

The websocket-aware resolver `resolve_from_websocket` and the removal of `src/skriptoteket/web/dishka_compat.py` shipped in 1743db254 on 2026-03-29, with a real-middleware websocket test in `tests/unit/web/test_dishka_websocket_routes.py`. No websocket endpoint exists in `src`, so criterion 1 is met by the helper and its test. The Hemma redeploy and health proof (criterion 3) is recorded as handoff text in 1743db254 and 7f28576f8 and in the ST-07-07 story Notes (clean redeploy of `1743db25`, healthy web container, in-container `/healthz` and `/metrics`, seating-export gate); it was not re-run. Criterion 3 rests on the handoff sentence and the story notes; no retained output exists.
