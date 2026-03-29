---
type: story
id: ST-07-07
title: "Retire hybrid Dishka/FastAPI compatibility layer and restore supported web DI"
status: done
owners: "agents"
created: 2026-03-29
updated: 2026-03-29
epic: "EPIC-07"
dependencies:
  - "ST-07-02"
  - "ST-07-06"
acceptance_criteria:
  - "Given the web app boots against the locked production runtime, when `GET /healthz` and `GET /metrics` are called, then they succeed through supported public-API DI and no longer depend on the repo-owned hybrid `dishka_compat.py` route injection path."
  - "Given HTTP routes require Dishka-backed dependencies, when this story ships, then they resolve through FastAPI `Depends` and `request.state.dishka_container` rather than synthetic `___dishka_request` / `___dishka_websocket` kwargs."
  - "Given websocket endpoints still need DI, when this story ships, then they use explicit websocket-aware resolution instead of sharing the HTTP injection fallback."
  - "Given local and Hemma verification run against the same locked library tuple, when this story is reviewed, then containerized proof shows the web health gate passes and the repo no longer relies on copied Dishka/FastAPI integration internals."
ui_impact: "No direct UI redesign; route/runtime behavior only."
data_impact: "No persistence contract change."
---

## Context

Production Hemma is now on the latest repo commit, but `/healthz` fails inside the repo-owned
`skriptoteket.web.dishka_compat` layer with `KeyError: '___dishka_websocket'`. The root problem
is not the health logic itself; it is the unsupported hybrid integration that copies
`dishka.integrations.fastapi` behavior while swapping in `starlette-dishka` middleware.

That hybrid layer depends on internal injection mechanics and synthetic request/websocket kwargs.
It is now the wrong abstraction boundary for a production FastAPI app that must stay aligned with
supported library contracts.

## Scope

- Retire the copied FastAPI/Dishka hybrid compatibility layer.
- Replace HTTP route injection with public FastAPI dependency resolution from
  `request.state.dishka_container`.
- Keep websocket DI explicit instead of relying on HTTP fallback semantics.
- Re-establish production health/readiness proof on Hemma.

## Non-goals

- Changing domain/application contracts or Dishka provider topology.
- Rewriting unrelated router behavior, auth semantics, or planner/workspace UI.
- Shipping a quick `/healthz`-only workaround while leaving the hybrid path in place.

## Planned PR slices

- [PR-0162: ST-07-07 public HTTP Dishka adapter and observability cutover](../prs/pr-0162-st-07-07-public-http-dishka-adapter-and-observability-cutover.md)
- [PR-0163: ST-07-07 HTTP route dependency cutover off hybrid Dishka inject](../prs/pr-0163-st-07-07-http-route-dependency-cutover-off-hybrid-dishka-inject.md)
- [PR-0164: ST-07-07 websocket cutover, hybrid compat retirement, and production proof](../prs/pr-0164-st-07-07-websocket-cutover-hybrid-compat-retirement-and-production-proof.md)

## Notes

- The correct solution is explicitly `not` a health-endpoint patch.
- The migration must favor supported public APIs:
  - `starlette-dishka` for container middleware/setup
  - FastAPI `Depends` for HTTP resolution from `request.state.dishka_container`
  - explicit websocket handling for websocket endpoints
- Validation must run against the locked/containerized runtime, not only a drifting local dev venv.
- Shipped on `2026-03-29` by removing `src/skriptoteket/web/dishka_compat.py`, moving HTTP routes/auth
  dependencies onto `src/skriptoteket/web/dishka_dependencies.py`, adding a real websocket middleware
  proof, and re-verifying Hemma with healthy container status plus successful in-container `/healthz` and
  `/metrics` checks on the locked production tuple.

## References

- Epic parent: [EPIC-07](../epics/epic-07-observability-and-operations.md)
- Health/metrics baseline: [ST-07-02](story-07-02-healthz-and-metrics-endpoints.md)
- Correlation middleware baseline: [ST-07-06](story-07-06-asgi-correlation-middleware.md)
- Official Dishka FastAPI docs: [dishka.readthedocs.io/en/stable/integrations/fastapi.html](https://dishka.readthedocs.io/en/stable/integrations/fastapi.html)
