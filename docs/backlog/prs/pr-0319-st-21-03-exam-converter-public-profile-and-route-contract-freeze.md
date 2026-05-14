---
type: pr
id: PR-0319
title: "ST-21-03 Exam Converter public profile and route-contract freeze"
status: done
owners: "agents"
created: 2026-05-13
updated: 2026-05-13
stories:
  - "ST-21-03"
tags:
  - backend
  - frontend
  - docs
  - public-access
  - conversion-hub
  - sir-convert
acceptance_criteria:
  - "Given `ADR-0085` authorizes only the bounded Exam Converter exception, when `documents.conversion_hub` is read from the curated-app registry, then general Conversion Hub remains `authenticated_only` while the app declares `public_capabilities: [{ scope: \"exam_converter\", profile: \"public_browser_runtime\" }]`."
  - "Given a public bootstrap request targets `documents.conversion_hub`, when the request is for the Exam Converter public scope, then the response exposes only the scoped `exam_converter` capability metadata and never exposes authenticated route discovery, arbitrary conversion routes, Vault/MyFiles affordances, owner-scoped job recovery, or account history."
  - "Given public helper namespaces must stay cookie-agnostic, when the Exam Converter public route contract is frozen, then the documented namespace ignores ambient account authority and carries explicit MIME/type validation, upload-size caps, request-time budgets, concurrency limits, rate limits, structured reason codes, short artifact TTLs, correlation-id display, and privacy-safe telemetry requirements."
  - "Given this slice is only a contract/profile freeze, when implementation is reviewed, then no runtime public conversion submission, polling, artifact generation/download, Sir Convert credential forwarding, or direct `convert.hule.education` browser path has shipped."
---

# PR-0319: ST-21-03 Exam Converter Public Profile And Route-Contract Freeze

## Problem

`ADR-0085` now authorizes a narrow public Exam Converter exception for
`documents.conversion_hub`, but the current registry and public bootstrap
contract still have only one app-wide `public_access_profile`. If that field is
simply changed to `public_browser_runtime`, the whole Conversion Hub can look
public even though `ADR-0085` keeps general conversion authenticated-only.

## Goal

Freeze the scoped public capability contract before public runtime conversion
implementation starts. `documents.conversion_hub` must remain authenticated for
general conversion workloads while declaring only one public capability:
`exam_converter` with profile `public_browser_runtime`.

## Non-goals

- Runtime public conversion submission, polling, result, artifact manifest, or
  download implementation.
- Authenticated Conversion Hub UI integration for the approved `PR-0318`
  adapter.
- Public Vault/MyFiles save, recoverable guest jobs, account history, or
  owner-scoped job rows.
- Arbitrary public Conversion Hub route discovery or general file conversion.
- HuleEdu Gateway or Sir Convert runtime changes.

## Implementation Plan

1. Add a scoped public-capability model to the curated-app domain registry
   contract, for example:

   ```yaml
   public_capabilities:
     - scope: exam_converter
       profile: public_browser_runtime
   ```

2. Keep `documents.conversion_hub.public_access_profile` as
   `authenticated_only` and add only the `exam_converter` scoped capability.
3. Add registry/domain helpers that distinguish app-wide public access from
   scoped public capabilities, such as `supports_public_capability(scope)`, so
   `supports_public_access` does not silently become true for all Conversion Hub
   surfaces.
4. Update public bootstrap/support contracts so `documents.conversion_hub`
   can be exposed only for the `exam_converter` scope and only with public-safe
   capability metadata.
5. Freeze the route namespace for the later runtime slice:
   - frontend public lane:
     `/public/apps/documents.conversion_hub/exam-converter`
   - backend public namespace:
     `/api/v1/public/apps/documents.conversion_hub/exam-converter/...`
6. Document the public helper taxonomy for the later runtime slice:
   MIME/type validation, upload-size caps, request-time budgets, concurrency
   limits, rate limits, structured reason codes, short artifact TTLs,
   correlation-id display, and privacy-safe telemetry.
7. Add focused tests proving:
   - general Conversion Hub remains authenticated-only;
   - `exam_converter` is the only public capability exposed for
     `documents.conversion_hub`;
   - public bootstrap/support does not expose authenticated route discovery,
     Vault/MyFiles, arbitrary conversion routes, or job recovery;
   - unsupported app/scope combinations fail closed;
   - public scope helpers ignore ambient sessions where route-level testing is
     in scope.

## Test Plan

- Focused registry/domain tests for `CuratedAppDefinition` scoped capability
  validation and helper behavior.
- Focused public bootstrap/support route tests for scoped
  `documents.conversion_hub` public metadata and fail-closed unsupported
  scopes.
- Focused frontend route/host tests if the public Exam Converter route shell is
  introduced in this freeze slice.
- `pdm run lint`
- `pdm run typecheck`
- `pdm run fe-test` with the touched frontend specs if frontend route metadata
  changes.
- `pdm run fe-type-check` if frontend types change.
- `pdm run fe-lint` if frontend files change.
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Implementation Summary

- Added `CuratedAppPublicCapability` plus scoped helpers on
  `CuratedAppDefinition`, while keeping `supports_public_access` tied only to
  the app-wide `public_access_profile`.
- Updated the registry so `documents.conversion_hub` remains
  `authenticated_only` for general access and declares only
  `public_capabilities: [{ scope: "exam_converter", profile:
  "public_browser_runtime" }]`.
- Added the scoped public bootstrap endpoint
  `/api/v1/public/apps/documents.conversion_hub/exam-converter`; it returns
  contract metadata only: public route/API namespace, upload MIME/suffix caps,
  size limits, time budget, concurrency/rate limit, short artifact TTL, target
  vocabulary, artifact-manifest keys, reason codes, blocked authenticated
  affordances, and privacy-safe telemetry fields.
- Kept `/api/v1/public/apps/documents.conversion_hub` fail-closed so the
  general Conversion Hub public surface is not opened.
- Added the frontend route namespace
  `/public/apps/documents.conversion_hub/exam-converter` and made the public
  host call public bootstrap with credential-omitting fetch semantics.
- Shipped no public conversion submission, polling, artifact generation,
  artifact download, Sir Convert credential forwarding, or direct
  `convert.hule.education` browser path.

## Verification

- `pdm run pytest tests/unit/domain/curated_apps/test_models.py tests/unit/infrastructure/curated_apps/test_registry.py tests/unit/web/test_public_apps_api_routes.py -q`
  (`12 passed`)
- `pdm run fe-test -- --run src/api/client.spec.ts src/router/routes.spec.ts src/views/PublicAppHostView.spec.ts`
  (`37 passed`)
- `pdm run fe-gen-api-types`
- `pdm run lint`
- `pdm run typecheck`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `rg -n "convert\\.hule\\.education|X-API-Key|SIR_CONVERT_A_LOT_V2_API_KEY|127\\.0\\.0\\.1:9010" src/skriptoteket/web/static/spa`
  (no matches)
- Live backend HTTP check against `http://127.0.0.1:8000`:
  `/api/v1/public/apps/documents.conversion_hub` returned `404`, while
  `/api/v1/public/apps/documents.conversion_hub/exam-converter` returned
  `200` with app-wide `authenticated_only` plus scoped `exam_converter`
  metadata.
- Live Playwright route check against
  `http://127.0.0.1:5173/public/apps/documents.conversion_hub/exam-converter`
  with an ambient cookie set: the scoped bootstrap request was observed once,
  sent no cookie header, and rendered the contract-only missing-runtime
  fallback.
- Retained review `REV-PR-0319` approved the scoped public profile and
  route-contract freeze with no required changes.
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Stop Conditions

- Stop if the implementation requires changing `documents.conversion_hub` to an
  unqualified app-wide public profile.
- Stop if public bootstrap needs to expose the authenticated Conversion Hub
  route list or general conversion route options.
- Stop if runtime conversion submission/download behavior is needed to prove the
  profile contract; that belongs to a later implementation slice.
- Stop if a public route would rely on ambient account/session authority.

## Rollback Plan

Remove the scoped public-capability fields/helpers, route namespace docs, and
tests added in this slice. `documents.conversion_hub` remains authenticated-only
and no public runtime conversion state is introduced.
