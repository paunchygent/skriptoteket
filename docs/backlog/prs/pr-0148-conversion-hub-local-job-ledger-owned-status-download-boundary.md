---
type: pr
id: PR-0148
title: "Conversion Hub: local job ledger and owned status/download boundary"
status: done
owners: "agents"
created: 2026-03-26
updated: 2026-03-27
stories:
  - "ST-21-01"
tags: ["backend", "curated-apps", "conversion-hub", "integration", "auth"]
acceptance_criteria:
  - "Given a signed-in user submits one or more Conversion Hub files, when Skriptoteket accepts the request, then it creates local conversion-job records and returns local job ids instead of exposing raw upstream Sir Convert job ids as the primary product contract."
  - "Given a user polls Conversion Hub job status, when the request is handled, then Skriptoteket resolves the local job, refreshes upstream state as needed, and only returns status for jobs owned by that user."
  - "Given a user downloads a succeeded Conversion Hub artifact, when the request is handled, then Skriptoteket authorizes access through the local job ledger and proxies the artifact bytes through Skriptoteket rather than issuing an upstream redirect."
  - "Given Skriptoteket and Sir Convert run on the same host, when a trusted local transport is configured, then the client supports a Unix domain socket path as the preferred transport and uses `127.0.0.1` HTTP as the fallback instead of treating internal HTTPS as the default."
  - "Given a different signed-in user attempts to poll or download a Conversion Hub job they do not own, when the request is handled, then the API returns a stable not-found/forbidden outcome without revealing whether the upstream Sir Convert job exists."
---

## Problem

The current Conversion Hub backend is a thin upstream passthrough:

- submit returns upstream `job_id`
- poll addresses upstream `job_id`
- download resolves directly from upstream `job_id`

That shape is too thin for a first-class curated app. Skriptoteket does not own job identity or
authorization strongly enough, and the product boundary leaks Sir Convert internals more than it
should.

## Goal

Add the missing local ownership/auth boundary for Conversion Hub before the bespoke SPA hardens
around the current passthrough contract:

- local conversion-job ledger in Skriptoteket,
- local job ids as the user-facing API contract,
- locally authorized status/download surfaces,
- same-host Unix-socket transport shape defined explicitly.

## Non-goals

- No new conversion engines in Skriptoteket.
- No webhook onboarding or callback orchestration for this slice.
- No redirect/download URL model that exposes Sir Convert as the primary artifact boundary.
- No local Vault persistence of Conversion Hub artifacts in this first slice; downloads may remain
  proxy-through from upstream after local authorization.
- No SPA redesign beyond whatever is required for the backend contract to return local job ids.

## Decisions (locked for PR-0148)

- Conversion Hub job identity is local-first: Skriptoteket owns the durable job id presented to the
  user.
- Upstream Sir Convert job ids are treated as internal integration details and are not the primary
  user-facing contract.
- Artifact download stays proxied through Skriptoteket.
- Same-host transport prefers Unix domain sockets when configured.
- `127.0.0.1` HTTP remains the fallback transport for local development and non-socket
  deployments.
- Internal HTTPS between co-located services is not the default same-host transport contract.

## Implementation plan

- [x] Add a local Conversion Hub job persistence model and repository:
  - local job id
  - owner user id
  - route metadata
  - input filename
  - upstream Sir Convert job id
  - local status / timestamps / correlation id / failure summary fields needed for UX
- [x] Add application-layer orchestration for:
  - submit: create local job, submit upstream, persist mapping
  - status refresh: load local job, authorize owner, refresh upstream status as needed
  - artifact download: load local job, authorize owner, proxy upstream artifact on success
- [x] Refactor `src/skriptoteket/web/api/v1/apps_conversion_hub.py` so its public contract uses
  local job ids rather than raw upstream ids.
- [x] Extend the Sir Convert client/config shape to support a same-host Unix-socket path:
  - optional `SIR_CONVERT_A_LOT_V2_UNIX_SOCKET_PATH`
  - if present, the http client uses the socket transport
  - otherwise keep `SIR_CONVERT_A_LOT_V2_BASE_URL`
- [x] Update DI/config/docs/runbooks to reflect the local-ledger + Unix-socket contract.
- [x] Update any affected frontend/OpenAPI types so the bespoke UI can target the local job
  identity cleanly.

## Verification Evidence

- `pdm run db-upgrade`
- `pdm run pytest tests/unit/application/curated_apps/handlers/test_conversion_hub_jobs.py tests/unit/web/conversion_hub/test_apps_conversion_hub_api.py tests/unit/web/conversion_hub/test_apps_conversion_hub_job_spec.py tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_client_v2.py`
- `pdm run pytest -o addopts='' 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[2b6c4d8e1f9a]'`
- `pdm run mypy src/skriptoteket/application/curated_apps/conversion_hub.py src/skriptoteket/application/curated_apps/handlers/conversion_hub_jobs.py src/skriptoteket/protocols/conversion_hub.py src/skriptoteket/infrastructure/db/models/conversion_hub_job.py src/skriptoteket/infrastructure/repositories/conversion_hub_jobs.py src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/sir_convert_client_v2.py src/skriptoteket/web/api/v1/apps_conversion_hub.py src/skriptoteket/di/curated_apps.py`
- `pdm run ruff check src/skriptoteket/application/curated_apps/conversion_hub.py src/skriptoteket/application/curated_apps/handlers/conversion_hub_jobs.py src/skriptoteket/protocols/conversion_hub.py src/skriptoteket/infrastructure/db/models/conversion_hub_job.py src/skriptoteket/infrastructure/repositories/conversion_hub_jobs.py src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/sir_convert_client_v2.py src/skriptoteket/web/api/v1/apps_conversion_hub.py src/skriptoteket/di/curated_apps.py tests/unit/application/curated_apps/handlers/test_conversion_hub_jobs.py tests/unit/web/conversion_hub/test_apps_conversion_hub_api.py tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_client_v2.py tests/integration/migration_schema_assertions.py`
- `pdm run docs-validate`
- Live proof on `http://127.0.0.1:5173`:
  - malformed `pdf_layout` + `md` request returned `422` before handler-owned job creation
  - submit/status/download succeeded through the local job ledger and owned artifact boundary

## Test shape

Behavioral tests only:

- submit returns local job ids and creates owned job records
- a user can poll/download their own conversion job through Skriptoteket
- a different user cannot poll/download another user's conversion job
- succeeded artifact download returns the correct bytes/media type through Skriptoteket without an
  upstream redirect contract
- when a same-host Unix socket is configured and reachable, submit/poll/download succeed without
  requiring a TCP loopback or internal HTTPS listener
- when the socket is not configured, loopback/base-url fallback still works

## Verification plan

- `pdm run pytest` focused on Conversion Hub application/web/infrastructure behavior
- `pdm run mypy` on the touched Conversion Hub modules
- `pdm run ruff check` on the touched Conversion Hub modules
- `pdm run docs-validate`
- one live proof against the local dev lane showing:
  - submit returns local ids
  - owned polling works
  - owned artifact download works
  - a second user cannot fetch the first user's job

## Rollback plan

- Remove the local Conversion Hub job table/repository and revert the API contract to the current
  passthrough model only if the slice is abandoned before frontend adoption.
