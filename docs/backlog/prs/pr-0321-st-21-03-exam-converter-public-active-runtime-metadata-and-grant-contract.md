---
type: pr
id: PR-0321
title: "ST-21-03 Exam Converter public active-runtime metadata and grant contract"
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
  - huleedu
acceptance_criteria:
  - "Given HuleEdu `TASK-0563` and Sir Convert `TASK-291` now define a public Exam Converter grant lane, when Skriptoteket unblocks the public runtime package, then it consumes those contracts explicitly instead of relying on anonymous Sir Convert access or authenticated browser-session authority."
  - "Given PR-0319 froze `runtime_status: \"contract_only\"`, when public runtime readiness is represented, then the public metadata contract gains governed state values and action affordances that can distinguish contract-only, grant-contract-ready, and active runtime without opening general Conversion Hub public access."
  - "Given public conversion authority is grant-backed, when browser users submit, poll, inspect manifests, or download artifacts, then the browser only talks to Skriptoteket public endpoints and never receives HuleEdu signing material, Sir Convert credentials, raw grant authority, raw artifact-read lease authority, or direct `convert.hule.education` route authority."
  - "Given public Exam Converter jobs are not account-owned, when the contract is implemented, then Skriptoteket validates uploads and target selection before grant use, carries grant and read-lease authority server-side, returns only opaque public job/artifact handles to the browser, and creates no Vault/MyFiles records, owner-scoped job rows, recoverable guest jobs, or account history."
  - "Given PR-0320 remains the runtime implementation slice, when this bridge slice closes, then PR-0320 has explicit dependencies, tests, stop conditions, and metadata semantics for consuming the grant-backed public runtime contract."
---

# PR-0321: ST-21-03 Exam Converter Public Active-Runtime Metadata And Grant Contract

## Problem

`PR-0320` was blocked because it tried to ship anonymous public
submit/poll/manifest/download behavior before HuleEdu and Sir Convert had an
approved upstream public authority model. Those dependency tasks now exist, but
Skriptoteket still cannot safely implement runtime code until its own public
metadata and adapter contract is updated from the `PR-0319` contract-only shell.

The remaining local gap is narrow: represent runtime readiness truthfully and
define how the Skriptoteket backend uses the upstream public grant/read-lease
contracts without exposing authority or widening general Conversion Hub public
access.

## Goal

Create the governed Skriptoteket bridge between the completed upstream public
grant lane and the later `PR-0320` runtime implementation. This slice updates
the public Exam Converter contract so runtime code has a precise metadata
state, action affordance, authority, and proof shape to consume.

## Review Status

Implementation is complete and retained review `REV-PR-0321` is approved.
`PR-0320` may now consume this bridge for runtime implementation, while keeping
the runtime proof burden in its own slice.

No retained Sir Convert review record for `TASK-291` was found during
`REV-PR-0320` re-review. `REV-PR-0321` explicitly accepts completed Sir Convert
`TASK-291` plus the updated converter and authorization-profile contracts as the
upstream Sir Convert approval evidence for this bridge.

## Dependencies

- HuleEdu public grant authority:
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/tasks/task-0563-define-public-exam-converter-grant-authority-for-sir-convert.md`
- HuleEdu ADR/reference authority:
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/decisions/0045-public-exam-converter-grant-authority-for-sir-convert.md`
  and
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/reference/ref-public-exam-converter-grant-v1-contract.md`
- Sir Convert public grant lane:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/tasks/task-291-define-public-exam-converter-grant-lane-for-digiexam-migration-bundles.md`
- Local contract freeze:
  `docs/backlog/prs/pr-0319-st-21-03-exam-converter-public-profile-and-route-contract-freeze.md`
- Blocked runtime slice:
  `docs/backlog/prs/pr-0320-st-21-03-exam-converter-public-one-time-runtime-lane.md`
- Retained blocker:
  `docs/backlog/reviews/review-pr-0320-exam-converter-public-one-time-runtime-lane.md`
- Pending retained bridge review:
  `docs/backlog/reviews/review-pr-0321-exam-converter-public-active-runtime-metadata-and-grant-contract.md`

## Non-goals

- Implementing public submit, poll, result, artifact manifest, or download
  runtime behavior.
- Calling HuleEdu or Sir Convert from browser code.
- Exposing `PublicConversionGrantV1`, `PublicArtifactReadLeaseV1`, HuleEdu
  signing material, Sir Convert credentials, or direct upstream hosts to the
  browser.
- Changing `documents.conversion_hub.public_access_profile` from
  `authenticated_only`.
- Adding public Vault/MyFiles save, owner-scoped job recovery, account history,
  or guest-to-account import.
- Reworking the authenticated PR-0318 HuleEdu Gateway adapter.

## Implementation Plan

1. Extend the public Exam Converter bootstrap metadata contract beyond the
   frozen `runtime_status: "contract_only"` state with governed readiness
   states:
   - `contract_only`: PR-0319 shell; no public runtime actions.
   - `grant_contract_ready`: upstream HuleEdu/Sir Convert grant contracts are
     known and local runtime wiring may be implemented behind this contract.
   - `active`: public runtime routes are available and action affordances may
     be rendered.
2. Add explicit public action affordances to the metadata contract for the
   later runtime:
   `submit`, `poll`, `result`, `artifact_manifest`, and `artifact_download`.
   Keep them absent or disabled while the route is `contract_only`.
3. Define a Skriptoteket backend adapter boundary for public grants:
   - validate `source_dxe`, optional `graded_result_pdf`, targets, content
     types, filenames, size limits, and empty payloads before any grant use;
   - obtain or carry `PublicConversionGrantV1` server-side only;
   - forward public conversion work to the approved HuleEdu/Sir Convert path;
   - consume `PublicArtifactReadLeaseV1` server-side for artifact reads;
   - return only opaque Skriptoteket public job and artifact handles to the
     browser.
4. Preserve cookie parity and guest semantics: public endpoints ignore ambient
   account/session authority and behave the same with or without authenticated
   cookies.
5. Keep general Conversion Hub closed: unsupported
   `/api/v1/public/apps/documents.conversion_hub` and non-`exam_converter`
   scopes continue to fail closed.
6. Update `PR-0320` so its runtime implementation depends on this bridge slice
   and consumes the governed metadata/grant adapter contract.

## Test Plan

- Backend metadata tests proving `contract_only`, `grant_contract_ready`, and
  `active` state serialization and disabled/enabled action affordances.
- Backend public bootstrap tests proving general Conversion Hub stays
  `authenticated_only`, unsupported scopes fail closed, and scoped
  `exam_converter` metadata does not expose authenticated route discovery.
- OpenAPI generation and frontend type checks proving the metadata transition
  is explicit and typed.
- Frontend public host specs proving the route renders contract-only fallback
  before active runtime and consumes active/grant-ready affordances without
  sending credentials.
- Adapter contract tests proving the browser-visible contract contains no raw
  `PublicConversionGrantV1`, `PublicArtifactReadLeaseV1`, signing material,
  Sir Convert credentials, or direct upstream route authority.
- Follow-up `PR-0320` runtime proof must include cross-repo positive and
  negative evidence for submit, poll, result, manifest, named download, TTL
  expiry, rate/concurrency limits, cookie parity, no account persistence, no
  browser `X-API-Key`, and fail-closed direct `convert.hule.education`
  traffic.
- `pdm run lint`
- `pdm run typecheck`
- `pdm run fe-test` with touched frontend specs
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Implementation Summary

- Added `CuratedAppPublicRuntimeStatus` with `contract_only`,
  `grant_contract_ready`, and `active` states.
- Marked the scoped `documents.conversion_hub` `exam_converter` public
  capability as `grant_contract_ready` while keeping the app-wide
  `public_access_profile` as `authenticated_only`.
- Extended the public Exam Converter bootstrap metadata with typed action
  affordances for submit, poll, result, artifact manifest, and artifact
  download. The current grant-ready state exposes those actions as disabled;
  only the future `active` runtime state enables them.
- Added an explicit authority-boundary payload that keeps browser authority to
  opaque public handles and records server-mediated upstream conversion,
  server-mediated artifact reads, ignored account authority, transient public
  persistence, and blocked authority exposure.
- Regenerated OpenAPI and frontend TypeScript types so the SPA sees the
  governed runtime-status enum and new metadata fields.
- Updated public host tests to consume grant-ready Exam Converter metadata
  through the credential-omitting public API lane while still rendering the
  missing-runtime fallback until a public runtime view exists.

## Verification

- `pdm run pytest tests/unit/domain/curated_apps/test_models.py tests/unit/infrastructure/curated_apps/test_registry.py tests/unit/web/test_public_apps_api_routes.py -q`
  (`15 passed`)
- `pdm run fe-gen-api-types`
- `pdm run fe-test -- --run src/views/PublicAppHostView.spec.ts src/api/client.spec.ts`
  (`31 passed`)
- `pdm run lint`
- `pdm run typecheck`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `rg -n "convert\\.hule\\.education|X-API-Key|SIR_CONVERT_A_LOT_V2_API_KEY|127\\.0\\.0\\.1:9010|PublicConversionGrantV1|PublicArtifactReadLeaseV1" src/skriptoteket/web/static/spa`
  (no matches)

## Stop Conditions

- Stop if the local runtime needs to change
  `documents.conversion_hub.public_access_profile` from `authenticated_only`
  to a public app-wide profile.
- Stop if browser code needs direct HuleEdu/Sir Convert authority, raw grants,
  raw read leases, upstream service credentials, `X-API-Key`, or direct
  `convert.hule.education` calls.
- Stop if the public route relies on ambient account/session cookies or
  behaves differently for signed-in users.
- Stop if the upstream HuleEdu/Sir Convert public grant contracts drift from
  the cited task/reference docs.
- Stop if the runtime would need Vault/MyFiles, owner-scoped conversion jobs,
  recoverable guest jobs, or account history before login.

## Rollback Plan

Remove the active-runtime metadata states, action-affordance contract, public
grant adapter contract, and PR-0320 dependency updates added by this slice.
The PR-0319 contract-only metadata remains in place and `PR-0320` returns to
blocked until a replacement governed runtime bridge is approved.
