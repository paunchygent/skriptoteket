---
type: pr
id: PR-0162
title: "ST-07-07: public HTTP Dishka adapter and observability cutover"
status: ready
owners: "agents"
created: 2026-03-29
updated: 2026-03-29
stories:
  - "ST-07-07"
tags: ["backend", "fastapi", "dishka", "observability", "production"]
dependencies:
  - "ST-07-07"
acceptance_criteria:
  - "Given the repo no longer trusts the hybrid compatibility layer for HTTP routes, when this slice ships, then the app has one public-API HTTP adapter pattern based on FastAPI `Depends` + `request.state.dishka_container`."
  - "Given `/healthz` and `/metrics` are production gates, when this slice ships, then both endpoints use that public HTTP adapter path rather than `@inject` from `dishka_compat.py`."
  - "Given the app is run in the locked/containerized runtime, when verification runs, then `/healthz` returns successfully and the Hemma web container can become healthy."
---

## Problem

The current production failure appears first on `/healthz`, but the real issue is broader: HTTP
route DI still depends on a repo-owned hybrid `dishka_compat.py` that copied
`dishka.integrations.fastapi` internals and swapped in `starlette-dishka`.

That is not a stable public-API boundary.

## Goal

Introduce the supported HTTP-side replacement first and prove it on the observability endpoints so
production regains a healthy gate without relying on copied Dishka/FastAPI internals.

## Non-goals

- Global cutover of every injected HTTP route in one PR.
- Websocket DI migration.
- Deleting the hybrid layer before a supported replacement exists.

## Implementation plan

1. Add a shared HTTP dependency adapter module that resolves typed dependencies from
   `request.state.dishka_container` through FastAPI `Depends`.
2. Convert `/healthz` and `/metrics` to that adapter pattern.
3. Add focused tests that prove the observability routes no longer require the hybrid injected
   request/websocket kwarg path.
4. Add containerized/local proof so the verification path matches production more closely than the
   current drifting local venv.

## Test plan

- `pdm run pytest tests/test_smoke.py tests/unit/web/test_startup_checks.py tests/test_openapi_contracts.py`
- `PYTHONPATH=src pdm run python -c "from skriptoteket.web.app import create_app; app=create_app(); print(app.openapi()['info']['title'])"`
- containerized/live proof of `GET /healthz` and `GET /metrics`
- `pdm run docs-validate`

## Rollback plan

- Revert the new HTTP adapter and restore the prior observability route wiring together if the
  supported adapter pattern proves incomplete.
- Do not proceed to the global route cutover until this slice proves stable.

## References

- Story parent: [ST-07-07](../stories/story-07-07-retire-hybrid-dishka-fastapi-compatibility-layer-and-restore-supported-web-di.md)
