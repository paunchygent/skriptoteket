---
type: pr
id: PR-0320
title: "ST-21-03 Exam Converter public one-time runtime lane"
status: done
owners: "agents"
created: 2026-05-13
updated: 2026-05-13
stories:
  - "ST-21-03"
tags:
  - backend
  - frontend
  - public-access
  - conversion-hub
  - sir-convert
acceptance_criteria:
  - "Given PR-0319 froze the scoped public capability, when the public Exam Converter runtime is implemented, then all browser traffic stays under `/public/apps/documents.conversion_hub/exam-converter` and `/api/v1/public/apps/documents.conversion_hub/exam-converter/...` and uses the PR-0319 metadata as the contract."
  - "Given the public lane is anonymous, when a browser submits work, polls status, reads the artifact manifest, or downloads an artifact, then the public API ignores ambient authenticated cookies and returns the same guest semantics with or without a session."
  - "Given public conversion accepts teacher uploads, when submit is called, then it requires one `.dxe` source file, optionally accepts one sanitized graded-result PDF, validates field-specific filenames, MIME/content types, size caps, target vocabulary, and empty payloads before any upstream call, and returns structured reason codes on rejection."
  - "Given anonymous compute can be abused, when public submit/poll/download routes are exercised, then they enforce anonymous rate limits, concurrency limits, request-time budgets, short artifact TTLs, privacy-safe telemetry, and correlation-id display."
  - "Given public artifacts are not account owned, when conversion succeeds or partially succeeds, then artifacts are direct-download only and no Vault/MyFiles records, owner-scoped job rows, recoverable guest jobs, or account history entries are created before login."
  - "Given Sir Convert credentials and direct service hosts are forbidden in the browser, when the runtime is reviewed, then browser code never calls `convert.hule.education`, never embeds service credentials, and every upstream conversion call is server-mediated through an approved Skriptoteket/HuleEdu route."
---

# PR-0320: ST-21-03 Exam Converter Public One-Time Runtime Lane

## Problem

`PR-0319` froze the public Exam Converter capability and route contract, but it
intentionally returned metadata only. The public teacher workflow still cannot
submit a `.dxe`, poll job progress, read an artifact manifest, or download the
generated files.

## Review Status

Retained review `REV-PR-0320` is `approved` for runtime implementation. The
upstream HuleEdu/Sir Convert public grant authority now exists in HuleEdu
`TASK-0563` and Sir Convert `TASK-291`, and approved `PR-0321` has landed the
Skriptoteket metadata/grant bridge: `runtime_status` can now represent
`contract_only`, `grant_contract_ready`, and `active`, with active action
affordances and server-side grant/read-lease adapter semantics.

## Goal

Implement the first real public runtime lane behind the frozen
`exam_converter` scoped capability: transient upload, submit, poll/result,
artifact manifest, and direct artifact download. Keep the UI wiring minimal and
functional so the runtime contract can be reviewed before product polish.

## Implementation Summary

Implemented the scoped public runtime under the frozen PR-0319 namespace:
`/api/v1/public/apps/documents.conversion_hub/exam-converter/...`. The backend
now supports submit, status, result, artifact manifest, and named artifact
download routes with active-runtime metadata, anonymous rate limiting on every
public action, request-time budgets, per-field and aggregate upload validation,
short TTL transient state, and cookie-agnostic request handling.

The runtime keeps upstream authority server-side. Skriptoteket mints a HuleEdu
public conversion grant through the configured server-to-server authority,
passes `X-Public-Conversion-Grant` for submit/status/result, passes
`X-Public-Artifact-Read-Lease` for artifact reads, and only returns opaque
Skriptoteket public job ids plus local download URLs to the browser. No
Vault/MyFiles records, owner-scoped conversion job rows, guest recovery rows, or
account history writes are introduced.

The minimal public SPA host at
`/public/apps/documents.conversion_hub/exam-converter` provides `.dxe` upload,
optional graded-result PDF upload, target selection, submit/status refresh,
artifact listing, and direct downloads through credential-omitting public API
helpers. The authenticated Conversion Hub host is deliberately left unmapped to
this public view so the later authenticated product lane can keep its own
Gateway/save-to-files authority.

Quality remediation on 2026-05-13 split the public SPA host into a small route
shell, a public Exam Converter API boundary, a runtime composable, focused
upload/result panels, and a browser download helper. The view no longer owns
transport calls, backend contract types, runtime state orchestration, DOM
download mechanics, or hardcoded scoped color CSS; user-facing errors are now
mapped to stable Swedish copy instead of rendering raw backend exception
messages.

## Verification

- `pdm run ruff check src/skriptoteket/web/api/v1/public_apps_exam_converter.py tests/unit/infrastructure/curated_apps/test_registry.py`
- `pdm run pytest tests/unit/web/test_public_apps_exam_converter_runtime.py tests/unit/web/test_public_apps_api_routes.py tests/unit/infrastructure/curated_apps/test_registry.py -q`
  (14 passed)
- `pdm run fe-test -- --run src/views/apps/ExamConverterPublicView.spec.ts src/views/PublicAppHostView.spec.ts src/views/AppHostView.spec.ts`
  (7 passed)
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`
- Browser smoke at
  `http://127.0.0.1:5173/public/apps/documents.conversion_hub/exam-converter`
  confirmed the heading, file input, submit button, empty state, and clean
  console.

Full lint/type/build/docs validation is recorded in `.codex/handoff.md` at
closeout. Live upstream conversion with real HuleEdu grant-authority credentials
remains the governed `PR-0322` end-to-end proof slice.

## Non-goals

- A polished public Exam Converter product UI beyond the smallest functional
  upload/progress/download surface needed to prove the runtime.
- Authenticated Conversion Hub UI integration or save-to-user-files work.
- Vault/MyFiles persistence, owner-scoped job recovery, account history, or
  guest-to-account import.
- General public Conversion Hub route discovery or arbitrary file conversion.
- Changing `ADR-0085`, `ADR-0079`, or the PR-0319 scoped metadata contract
  except to consume it.
- Direct browser calls to `convert.hule.education`, browser service
  credentials, or browser-minted HuleEdu/Sir Convert identity context.

## Implementation Plan

1. Add a public Exam Converter backend route module under the frozen namespace:
   `/api/v1/public/apps/documents.conversion_hub/exam-converter/...`.
2. Add public runtime endpoints for:
   - submit/upload;
   - status/result polling;
   - artifact manifest retrieval;
   - named direct artifact download.
3. Reuse the PR-0319 metadata as the source of truth for public target
   vocabulary, upload limits, TTL, reason codes, and blocked affordances, as
   amended by `PR-0321` for active-runtime state and action affordances.
4. Add a transient public job/artifact state boundary that is TTL-bound and not
   owner scoped. It may use a dedicated transient table/store or filesystem
   temp storage, but it must not write Vault/MyFiles records, normal Conversion
   Hub owner job rows, or account history.
5. Apply field-specific validation before any upstream work:
   - required `source_dxe` file ending in `.dxe`;
   - optional `graded_result_pdf` file ending in `.pdf`;
   - content-type allowlist per field;
   - per-field and total payload size caps;
   - allowed targets: `examnet_pdf`, `qti_package`;
   - explicit empty/missing/unsupported reason codes.
6. Apply anonymous abuse controls at the public boundary: rate limit,
   concurrency limit, request-time budget, short artifact TTL, redacted logs,
   privacy-safe telemetry, and correlation-id propagation/display.
7. Call Sir Convert only through the approved HuleEdu/Sir Convert public grant
   lane consumed by `PR-0321`. Carry `PublicConversionGrantV1` and
   `PublicArtifactReadLeaseV1` semantics server-side and return only opaque
   Skriptoteket public job/artifact handles to the browser.
8. Add minimal public host wiring under
   `/public/apps/documents.conversion_hub/exam-converter`:
   upload fields, target selection, submit/progress state, terminal manifest,
   direct download actions, structured rejection display, and correlation id.

## Test Plan

- Focused backend tests for submit validation:
  `.dxe` required, optional PDF only, unsupported content type, empty payload,
  oversized payload, invalid target, and pre-upstream rejection.
- Focused backend tests for anonymous limits:
  rate-limit rejection, concurrency rejection or serialization, time-budget
  handling, TTL expiry/cleanup, and structured reason codes.
- Focused backend tests proving cookie parity: submit/poll/manifest/download
  behave the same with and without ambient authenticated cookies.
- Focused persistence tests proving no Vault/MyFiles records, owner-scoped
  conversion job rows, recoverable guest jobs, or account history writes.
- Focused upstream adapter tests proving server-mediated conversion calls,
  correlation/idempotency behavior, artifact manifest mapping, blocked/partial
  outcomes, and no browser-exposed credentials.
- Focused frontend tests for the minimal public host:
  public bootstrap metadata consumption, credential-omitting API calls,
  upload/target form, progress state, structured errors, terminal manifest,
  direct-download actions, and correlation-id display.
- Live public proof:
  `/api/v1/public/apps/documents.conversion_hub` remains `404`;
  `/api/v1/public/apps/documents.conversion_hub/exam-converter` remains `200`;
  actual submit/poll/download routes behave the same with and without ambient
  cookies.
- `pdm run lint`
- `pdm run typecheck`
- `pdm run fe-test` with touched frontend specs
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`
- Production bundle grep for forbidden direct-service/credential strings.

## Stop Conditions

- Stop if the implementation requires changing
  `documents.conversion_hub.public_access_profile` from `authenticated_only` to
  an unqualified public profile.
- Stop if the public lane needs to expose authenticated route discovery,
  arbitrary conversion routes, Vault/MyFiles, owner job recovery, or account
  history.
- Stop if there is no approved server-mediated upstream conversion path for
  anonymous Exam Converter work or if `PR-0321` has not landed the local
  metadata/grant adapter contract.
- Stop if a public route relies on ambient authenticated account/session
  authority or behaves differently when a session cookie is present.
- Stop if browser code would need to call `convert.hule.education` directly or
  receive Sir Convert service credentials.
- Stop if browser code would need raw `PublicConversionGrantV1`,
  `PublicArtifactReadLeaseV1`, HuleEdu signing material, or upstream route
  authority instead of opaque Skriptoteket public handles.

## Rollback Plan

Remove the public runtime route module, transient public job/artifact store,
minimal public host wiring, and tests added in this slice. The PR-0319 scoped
metadata remains in place as contract-only capability metadata, and
`documents.conversion_hub` remains authenticated-only for general conversion.
