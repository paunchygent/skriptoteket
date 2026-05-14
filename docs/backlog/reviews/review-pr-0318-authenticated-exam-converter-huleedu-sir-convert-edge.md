---
type: review
id: REV-PR-0318
title: "Review: PR-0318 authenticated Exam Converter HuleEdu Sir Convert edge adapter"
status: approved
owners: "agents"
created: 2026-05-13
updated: 2026-05-13
reviewer: "codex"
prs:
  - PR-0318
links:
  - EPIC-21
  - ST-21-03
---

## TL;DR

`PR-0318` is approved after re-review. The retained blockers now have focused
code and test coverage: configured browser bases fail closed unless they target
the HuleEdu Gateway route family, local `/sir-convert` development traffic uses
a dedicated Gateway proxy target, and blocked/failed/not-implemented artifact
entries require `blocker_code`.

## Problem Statement

This review checks whether the authenticated `documents.conversion_hub`
DigiExam migration adapter really uses the HuleEdu Gateway
`/sir-convert/v2/convert/...` browser edge and preserves Sir Convert bundle
metadata without direct service hosts, browser service credentials, or hidden
manual-follow-up states.

## Proposed Solution

The implementation adds `frontend/apps/skriptoteket/src/api/sirConvertGateway/`
as a small browser adapter package split by URL resolution, JobSpec
construction, request-context hashing, transport, response parsing, typed
contracts, errors, and save-to-user-files metadata. It also proxies
`/sir-convert` in Vite dev and records the governed `ST-21-03` / `PR-0318`
backlog surfaces.

## Artifacts to Review

| File | Focus |
|------|-------|
| `docs/backlog/prs/pr-0318-st-21-03-authenticated-exam-converter-huleedu-sir-convert-edge.md` | Scope, acceptance criteria, verification |
| `docs/backlog/stories/story-21-03-exam-converter-public-and-authenticated-artifact-lanes.md` | Parent story and route-boundary ordering |
| `docs/backlog/epics/epic-21-curated-app-conversion-hub.md` | Epic ownership and status summary |
| `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/tasks/task-0561-cut-skriptoteket-artifact-bundle-adapter-to-huleedu-sir-convert-edge.md` | HuleEdu Gateway cutover contract |
| `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/converters/digiexam-migration-service-api-artifact-contract.md` | Downstream artifact-bundle contract |
| `frontend/apps/skriptoteket/src/api/sirConvertGateway/urls.ts` | Browser base URL resolution |
| `frontend/apps/skriptoteket/vite.config.ts` | Local `/sir-convert` proxy target |
| `frontend/apps/skriptoteket/src/api/sirConvertGateway/jobSpec.ts` | Multipart JobSpec shape |
| `frontend/apps/skriptoteket/src/api/sirConvertGateway/requestContext.ts` | Idempotency and correlation construction |
| `frontend/apps/skriptoteket/src/api/sirConvertGateway/client.ts` | Submit/read/list/download transport |
| `frontend/apps/skriptoteket/src/api/sirConvertGateway/parsers.ts` | Result and artifact-manifest validation |
| `frontend/apps/skriptoteket/src/api/sirConvertGateway/client.spec.ts` | Consumer proof coverage |
| `frontend/apps/skriptoteket/src/api/sirConvertGateway/requestContext.spec.ts` | Request-context proof coverage |

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Use browser `/sir-convert/v2/convert/...` instead of direct Sir Convert hosts | Matches HuleEdu-owned product edge and keeps service credentials server-side | [x] |
| Build only the governed `digiexam_dxe -> examnet_migration_bundle` multipart request | Prevents Skriptoteket from parsing `.dxe` or inventing conversion semantics | [x] |
| Preserve one correlation ID across submit/read/download/save metadata | Required for teacher-action traceability and cross-service debugging | [x] |
| Treat blocked/manual-follow-up artifact metadata as contract data | UI must not flatten blocked bundle outcomes into vague transport failures | [x] |

## Review Checklist

- [x] Scope is bounded to the authenticated adapter slice.
- [x] Multipart part names and JobSpec route key match the Sir Convert
      contract.
- [x] Browser requests do not send `X-API-Key` in the focused tests.
- [x] Focused request-context and transport tests pass.
- [x] Production bundle grep found no direct service credential or reserved
      service-host strings.
- [x] Configured browser base URLs fail closed for direct service hosts.
- [x] Local dev `/sir-convert` proof uses the HuleEdu Gateway equivalent by
      default.
- [x] Parser validation requires `blocker_code` for blocked/failed/not
      implemented artifact entries.

## Review Feedback

**Reviewer:** `codex`
**Date:** `2026-05-13`
**Verdict:** `approved`

### Required Changes

1. **High:** `frontend/apps/skriptoteket/src/api/sirConvertGateway/urls.ts`
   accepts any `VITE_HULEEDU_SIR_CONVERT_BASE_URL` and returns it as the
   browser base URL. That allows a production build to be configured to call
   `convert.hule.education`, a direct Sir Convert host, or a local service port,
   violating the PR's Gateway-only criterion and the Sir Convert cutover
   boundary. Fix by validating configured bases and failing closed unless the
   URL is the HuleEdu Gateway `/sir-convert/v2/convert` edge, a governed local
   Gateway equivalent, or an explicit test-only host. Add rejection tests and
   keep the production bundle grep.

2. **High:** `frontend/apps/skriptoteket/vite.config.ts` proxies
   `/sir-convert` through `devProxyTarget`, which defaults to the Skriptoteket
   backend proxy target. HuleEdu `TASK-0561` requires production
   `api.hule.education` and the local Gateway equivalent, not the app backend by
   default. Add a dedicated Sir Convert Gateway dev proxy target, document it in
   the PR/handoff surface, and prove that `/sir-convert/v2/convert/...` reaches
   the local HuleEdu Gateway path.

3. **Medium:** `frontend/apps/skriptoteket/src/api/sirConvertGateway/parsers.ts`
   accepts `blocked`, `failed`, and `not_implemented` artifact entries without
   `blocker_code`, even though the Sir Convert artifact contract requires that
   field for those states. Tighten `parseArtifactEntry` so those states require
   a non-empty `blocker_code`, while `not_requested` remains allowed without
   one. Add negative parser tests.

### Suggestions

None.

### Remediation Update

1. `urls.ts` now validates configured browser bases against the HuleEdu Gateway
   `/sir-convert/v2/convert` route family, the local Gateway equivalent on port
   `8080`, and the explicit Vitest host only. Direct service hosts, local direct
   service ports, app-backend proxy ports, and non-Gateway paths fail closed
   before `fetch`.
2. `vite.config.ts` now uses `VITE_DEV_SIR_CONVERT_GATEWAY_PROXY_TARGET` for
   `/sir-convert`, defaulting to `http://localhost:8080`, so local development
   proves the HuleEdu Gateway equivalent instead of reusing the app backend
   proxy target.
3. `parsers.ts` now rejects `blocked`, `failed`, and `not_implemented`
   artifact entries without a non-empty `blocker_code`, while
   `not_requested` remains accepted without one.

### Re-review Status

Approved on 2026-05-13. The original three findings are resolved in the current
implementation and covered by focused tests plus the Vite config/default proxy
proof.

### Passing Checks Observed

- `pdm run fe-test -- --run src/api/sirConvertGateway/requestContext.spec.ts src/api/sirConvertGateway/client.spec.ts`
  passed with 20 tests.
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `node --input-type=module -e "import { loadConfigFromFile } from 'vite'; const loaded = await loadConfigFromFile({ command: 'serve', mode: 'development' }, './vite.config.ts'); console.log(loaded.config.server.proxy['/sir-convert'].target);"`
  from `frontend/apps/skriptoteket` printed `http://localhost:8080`.
- `pdm run docs-validate`
- `git diff --check`
- `rg -n "convert\\.hule\\.education|X-API-Key|SIR_CONVERT_A_LOT_V2_API_KEY|127\\.0\\.0\\.1:9010" src/skriptoteket/web/static/spa`
  returned no matches.

## Changes Made

1. Recorded the retained review outcome for `PR-0318` as
   `changes_requested`.
2. Re-reviewed the remediation and approved `PR-0318` after verifying the URL
   allowlist, dedicated local Gateway proxy target, strict artifact
   `blocker_code` parsing, and focused validation gates.
