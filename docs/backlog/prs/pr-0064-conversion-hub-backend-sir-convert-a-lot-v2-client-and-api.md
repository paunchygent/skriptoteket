---
type: pr
id: PR-0064
title: "Conversion Hub: backend Sir Convert-a-Lot v2 client + curated app API surface"
status: ready
owners: "agents"
created: 2026-03-01
updated: 2026-03-01
stories:
  - "ST-21-01"
tags: ["backend", "curated-apps", "integration"]
acceptance_criteria:
  - "Given Skriptoteket config provides Sir Convert-a-Lot v2 base URL and credentials, when the Conversion Hub API calls are exercised, then v2 jobs can be submitted, polled, and artifacts downloaded deterministically."
  - "All request/response models are typed and validated (Pydantic v2); no `Any`, casts, or type ignores are introduced."
  - "Unit tests cover success + failure cases (including timeouts and terminal failure) and remain within file size limits."
---

## Problem

Skriptoteket currently has no curated-app backend surface for orchestrating Sir Convert-a-Lot v2 conversions.

## Goal

Implement the backend portion of the Conversion Hub curated app:

- typed integration client (httpx) for Sir Convert-a-Lot v2 job lifecycle,
- curated app endpoints under `/api/v1/apps/<app_id>/...`,
- DI wiring + config.

## Non-goals

- No frontend UI in this PR (PR-0065).
- No migration of E2E tests (PR-0066).

## Implementation plan

- [ ] Add app registry entry in `src/skriptoteket/infrastructure/curated_apps/registry.py` (bespoke-required).
- [ ] Add app contract models under `src/skriptoteket/application/curated_apps/` (request/response payloads).
- [ ] Add protocol(s) under `src/skriptoteket/protocols/` for the v2 client and app handler.
- [ ] Add infra httpx client that implements the protocol:
  - timeouts (connect/read/overall),
  - deterministic error mapping (including correlation id passthrough),
  - idempotency support at the v2 API boundary (if available).
- [ ] Add API routes under `src/skriptoteket/web/api/v1/apps_<app>.py`:
  - submit conversion (single + batch form),
  - poll job status / result,
  - download artifact (proxy or signed URL strategy, depending on v2).
- [ ] Wire DI in `src/skriptoteket/di/curated_apps.py` and mount router in `src/skriptoteket/web/router.py`.
- [ ] Add unit tests for:
  - client request building (including `conversion.pdf_layout` mapping),
  - failure mapping (422 vs 5xx vs timeouts),
  - batch orchestration result shape.

## Test plan

- `pdm run lint`
- `pdm run typecheck`
- `pdm run test` (focus unit tests for new modules)

## Rollback plan

- Remove the new registry entry and routes; keep config keys unused if needed until PR-0065 lands.
