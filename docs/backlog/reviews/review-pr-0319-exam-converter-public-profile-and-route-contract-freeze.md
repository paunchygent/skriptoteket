---
type: review
id: REV-PR-0319
title: "Review: PR-0319 Exam Converter public profile and route-contract freeze"
status: approved
owners: "agents"
created: 2026-05-13
updated: 2026-05-13
reviewer: "codex"
prs:
  - PR-0319
adrs:
  - ADR-0085
links:
  - EPIC-21
  - ST-21-03
  - ADR-0079
---

## TL;DR

`PR-0319` is approved. The implementation keeps
`documents.conversion_hub` app-wide `authenticated_only`, exposes only the
scoped `exam_converter` public capability, returns contract-only metadata from
the dedicated public namespace, and does not ship runtime public conversion,
artifact download, Sir Convert credential forwarding, or direct
`convert.hule.education` browser traffic.

## Problem Statement

This review checks whether the bounded public Exam Converter exception from
`ADR-0085` is represented as scoped public capability metadata without opening
general Conversion Hub, authenticated route discovery, owner-scoped recovery,
Vault/MyFiles, or public runtime conversion behavior.

## Proposed Solution

The implementation adds `CuratedAppPublicCapability` to the curated-app domain
model, registers only `exam_converter` with profile `public_browser_runtime`
for `documents.conversion_hub`, keeps app-wide `public_access_profile` as
`authenticated_only`, adds a scoped bootstrap endpoint at
`/api/v1/public/apps/documents.conversion_hub/exam-converter`, and adds the
matching SPA route shell at
`/public/apps/documents.conversion_hub/exam-converter`.

## Artifacts to Review

| File | Focus |
|------|-------|
| `docs/backlog/prs/pr-0319-st-21-03-exam-converter-public-profile-and-route-contract-freeze.md` | Scope, non-goals, acceptance criteria, verification |
| `docs/backlog/stories/story-21-03-exam-converter-public-and-authenticated-artifact-lanes.md` | Public/authenticated lane split and PR ordering |
| `docs/adr/adr-0085-exam-converter-public-conversion-exception-for-conversion-hub.md` | Scoped public exception authority |
| `docs/adr/adr-0079-public-curated-app-access-profiles-and-guest-state-boundaries.md` | Accepted public app boundary being amended |
| `src/skriptoteket/domain/curated_apps/models.py` | Scoped capability contract and helper semantics |
| `src/skriptoteket/infrastructure/curated_apps/registry.py` | Conversion Hub registry profile |
| `src/skriptoteket/web/api/v1/public_apps.py` | Public bootstrap and scoped capability response |
| `src/skriptoteket/web/api/v1/public_apps_support.py` | Fail-closed public helper checks |
| `frontend/apps/skriptoteket/src/router/routes.ts` | Scoped public SPA namespace |
| `frontend/apps/skriptoteket/src/views/PublicAppHostView.vue` | Public bootstrap loading and credential-omitting client |
| `frontend/apps/skriptoteket/src/api/client.ts` | Public API credential behavior |
| `tests/unit/domain/curated_apps/test_models.py` | Domain capability proof |
| `tests/unit/infrastructure/curated_apps/test_registry.py` | Registry profile proof |
| `tests/unit/web/test_public_apps_api_routes.py` | Scoped bootstrap and fail-closed proof |
| `frontend/apps/skriptoteket/src/api/client.spec.ts` | Public fetch credential proof |
| `frontend/apps/skriptoteket/src/router/routes.spec.ts` | Scoped SPA route proof |
| `frontend/apps/skriptoteket/src/views/PublicAppHostView.spec.ts` | Public host shell proof |

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Add scoped public capabilities instead of changing the app-wide profile | Prevents all Conversion Hub surfaces from becoming public | [x] |
| Keep `/api/v1/public/apps/documents.conversion_hub` fail-closed | Avoids general public route discovery for authenticated Conversion Hub | [x] |
| Return contract-only metadata for `/exam-converter` | Freezes the public runtime taxonomy without shipping upload/poll/download behavior | [x] |
| Use credential-omitting public bootstrap fetches | Keeps public helper namespaces cookie-agnostic even with ambient account cookies | [x] |
| Leave actual public conversion runtime to a later slice | Keeps abuse controls and transient artifact state reviewable before compute opens | [x] |

## Review Checklist

- [x] Scope is bounded to profile/route-contract freeze.
- [x] `documents.conversion_hub.supports_public_access` remains false.
- [x] Only `exam_converter` is registered as a scoped public capability.
- [x] General Conversion Hub public bootstrap returns `404`.
- [x] Scoped Exam Converter bootstrap returns only public-safe contract metadata.
- [x] The scoped public API route has no auth, session, or CSRF dependency.
- [x] Public SPA bootstrap uses `credentials: "omit"`.
- [x] No runtime public conversion submission, polling, artifact generation, or
      artifact download route shipped in this slice.
- [x] Frontend and backend route ordering does not shadow existing public
      Klassrumskartan helper routes.
- [x] Current FastAPI and Vue Router docs were checked for route-order and
      dynamic-segment behavior while reviewing the route shape.

## Review Feedback

**Reviewer:** `codex`
**Date:** `2026-05-13`
**Verdict:** `approved`

### Required Changes

None.

### Suggestions

For the next public-runtime slice, keep the current metadata as a contract and
add implementation tests that prove field-specific MIME validation, anonymous
rate limiting, transient TTL cleanup, no Vault/MyFiles writes, and cookie parity
at the actual upload/poll/download routes.

### Passing Checks Observed

- `pdm run pytest tests/unit/domain/curated_apps/test_models.py tests/unit/infrastructure/curated_apps/test_registry.py tests/unit/web/test_public_apps_api_routes.py -q`
  passed with 12 tests.
- `pdm run fe-test -- --run src/api/client.spec.ts src/router/routes.spec.ts src/views/PublicAppHostView.spec.ts`
  passed with 37 tests.
- `curl -sS -i http://127.0.0.1:8000/api/v1/public/apps/documents.conversion_hub`
  returned `404`.
- `curl -sS -i -H 'Cookie: huleedu_session=ambient-test' http://127.0.0.1:8000/api/v1/public/apps/documents.conversion_hub/exam-converter`
  returned `200` with app-wide `authenticated_only`, scoped
  `exam_converter` metadata, and no runtime route list.
- Browser check at
  `http://127.0.0.1:5173/public/apps/documents.conversion_hub/exam-converter`
  rendered the contract-only missing-runtime fallback.
- `pdm run typecheck`
- `pdm run lint`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `rg -n "convert\\.hule\\.education|X-API-Key|SIR_CONVERT_A_LOT_V2_API_KEY|127\\.0\\.0\\.1:9010" src/skriptoteket/web/static/spa`
  returned no matches.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-0319` | Approved the scoped public profile and route-contract freeze after verifying code, docs, tests, route behavior, and live public route probes. |
