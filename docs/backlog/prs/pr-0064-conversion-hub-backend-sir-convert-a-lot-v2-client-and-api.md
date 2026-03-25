---
type: pr
id: PR-0064
title: "Conversion Hub: backend Sir Convert-a-Lot v2 client + curated app API surface"
status: done
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

- [x] Add app registry entry in `src/skriptoteket/infrastructure/curated_apps/registry.py` (bespoke-required).
- [x] Add app contract models under `src/skriptoteket/application/curated_apps/` (request/response payloads).
- [x] Add protocol(s) under `src/skriptoteket/protocols/` for the v2 client and app handler.
- [x] Add infra httpx client that implements the protocol:
  - timeouts (connect/read/overall),
  - deterministic error mapping (including correlation id passthrough),
  - idempotency support via per-submit generated keys (new key per job).
- [x] Add API routes under `src/skriptoteket/web/api/v1/apps_conversion_hub.py`:
  - list supported routes,
  - submit conversion jobs (multipart; supports batch),
  - poll job status,
  - download artifact (proxy).
- [x] Wire DI in `src/skriptoteket/di/curated_apps.py` and mount router in `src/skriptoteket/web/router.py`.
- [x] Add unit tests for:
  - client request shaping + error mapping,
  - v2 job spec mapping (including `conversion.pdf_layout` and required PDF-source defaults).

## Test plan

- `pdm run lint`
- `pdm run typecheck`
- `pdm run test` (focus unit tests for new modules)

## Rollback plan

- Remove the new registry entry and routes; keep config keys unused if needed until PR-0065 lands.

## Validation evidence (2026-03-01)

- `pdm run lint`: pass
- `pdm run typecheck`: pass
- `pdm run test`: pass
- OpenAPI contract: `pdm run pytest -q tests/test_openapi_contracts.py::test_openapi_schema_builds`: pass
- Historical local test for this PR slice (not a canonical current lane guide):
  - Started Sir Convert-a-Lot v2 service on `http://127.0.0.1:8085` with `SIR_CONVERT_A_LOT_V2_API_KEY=dev-only-key`
  - Started Skriptoteket with `SIR_CONVERT_A_LOT_V2_BASE_URL=http://127.0.0.1:8085` and
    `SIR_CONVERT_A_LOT_V2_API_KEY=dev-only-key`
  - Performed `HTML -> PDF` via `/api/v1/apps/documents.conversion_hub/jobs`, polled status, downloaded artifact, and
    verified the PDF header `%PDF-` (artifact saved under `.artifacts/conversion-hub-live/output.pdf`).
