---
type: pr
id: PR-0164
title: "ST-07-07: websocket cutover, hybrid compat retirement, and production proof"
status: ready
owners: "agents"
created: 2026-03-29
updated: 2026-03-29
stories:
  - "ST-07-07"
tags: ["backend", "fastapi", "dishka", "websocket", "production", "hemma"]
dependencies:
  - "PR-0163"
acceptance_criteria:
  - "Given websocket endpoints still require DI, when this slice ships, then they use explicit websocket-aware resolution rather than the HTTP hybrid fallback."
  - "Given HTTP routes are already migrated, when this slice ships, then `dishka_compat.py` is removed instead of retained as dead compatibility code."
  - "Given Hemma production is redeployed after the full cutover, when verification runs, then the web container becomes healthy and the deploy gate plus production health proof both pass."
---

## Problem

The hybrid layer cannot truly be retired until websocket handling and the remaining route wiring are
moved onto explicit supported paths. Otherwise the repo keeps dead or risky compatibility code even
after the HTTP migration.

## Goal

Finish the migration, delete the hybrid compatibility layer, and re-prove the full production web
readiness path on Hemma.

## Non-goals

- New product features.
- Additional DI/provider redesign beyond what is needed to remove the hybrid layer.

## Implementation plan

1. Migrate websocket-aware handlers to explicit websocket/container resolution.
2. Delete `src/skriptoteket/web/dishka_compat.py` and update imports/usages to the new public
   adapter paths.
3. Re-run local and containerized verification.
4. Redeploy Hemma and prove:
   - healthy web container
   - successful `/healthz`
   - successful seating-export deploy/readiness gate still intact

## Test plan

- targeted pytest for websocket-aware routes and any remaining route wiring
- `tests/test_smoke.py`
- containerized/live route proof including `/healthz`
- Hemma redeploy + health proof
- `pdm run docs-validate`

## Rollback plan

- If websocket cutover proves unstable, revert the deletion tranche while keeping the earlier HTTP
  migration slices available for re-entry.

## References

- Story parent: [ST-07-07](../stories/story-07-07-retire-hybrid-dishka-fastapi-compatibility-layer-and-restore-supported-web-di.md)
- HTTP migration slice: [PR-0163](pr-0163-st-07-07-http-route-dependency-cutover-off-hybrid-dishka-inject.md)
