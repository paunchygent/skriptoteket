---
type: task
id: TASK-SKRIPT-REP-0020
title: 'ST-07-07: websocket cutover, hybrid compat retirement, and production proof'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- Given websocket endpoints still require DI, when this slice ships, then they use
  explicit websocket-aware resolution rather than the HTTP hybrid fallback.
- Given HTTP routes are already migrated, when this slice ships, then `dishka_compat.py`
  is removed instead of retained as dead compatibility code.
- Given Hemma production is redeployed after the full cutover, when verification runs,
  then the web container becomes healthy and the deploy gate plus production health
  proof both pass.
---

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
