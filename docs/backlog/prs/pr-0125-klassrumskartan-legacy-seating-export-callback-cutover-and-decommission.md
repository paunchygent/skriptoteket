---
type: pr
id: PR-0125
title: "Klassrumskartan: legacy seating export callback cutover and decommission"
status: done
owners: "agents"
created: 2026-03-24
updated: 2026-03-24
stories:
  - "ST-26-01"
tags: ["backend", "ops", "klassrumskartan", "export", "webhooks", "sir-convert-a-lot", "remediation"]
acceptance_criteria:
  - "Given the shared callback route is canonical, when operators inventory the current Sir Convert-a-Lot webhook state, then they can classify every Skriptoteket-owned subscription as canonical shared, stale shared, or invalid legacy per-job state."
  - "Given non-canonical Skriptoteket webhook subscriptions exist upstream, when operators execute the cutover, then those subscriptions are updated or deleted in the same coordinated change so exactly one canonical shared subscription remains."
  - "Given the clean cutover is complete, when Skriptoteket is deployed, then the per-job `/seating-export-jobs/{job_id}` callback route and all runtime compatibility plumbing are removed rather than retained behind a migration window."
  - "Given Sir Convert-a-Lot owns webhook subscriptions upstream, when the cutover procedure is documented, then it uses the supported Sir Convert webhook onboarding API surfaces explicitly instead of treating legacy subscription cleanup as passive aging or hidden state."
  - "Given post-cutover verification runs, when operators execute the canonical smoke and re-inventory subscriptions, then they can prove only the canonical shared callback remains and callback-capable seating export still succeeds."
---

## Problem

`PR-0121` introduced the canonical shared seating export callback route, but the
old per-job callback route still exists as a compatibility path:

- canonical: `/api/v1/internal/sir-convert-a-lot/classroom-planner/seating-export-jobs`
- temporary legacy path:
  `/api/v1/internal/sir-convert-a-lot/classroom-planner/seating-export-jobs/{job_id}`

The reason is operational, not architectural: Sir Convert-a-Lot persists webhook
subscription records upstream. Those subscriptions keep posting conversion
events to the callback URL they were created with until they are updated,
disabled, or deleted. That means old upstream subscriptions can continue to hit
the legacy route even after Skriptoteket ships the shared callback path.

Leaving the compatibility route in place is the wrong endpoint state:

- it keeps a runtime shim that should not exist after cutover
- it allows stale upstream state to masquerade as supported behavior
- it blocks a clean inventory -> update/delete -> remove sequence across repos

## Goal

Define and implement one explicit clean cutover/decommission plan for the
legacy per-job callback route, including upstream Sir Convert-a-Lot
subscription inventory, coordinated mutation of all call sites, and same-slice
removal of the compatibility shim from Skriptoteket.

## Non-goals

- Changing the public seating export API or teacher-facing export UX.
- Replacing polling fallback.
- Reworking the shared callback dispatcher introduced in `PR-0121` beyond
  removing the compatibility shim.
- Building a general-purpose multi-consumer webhook migration framework beyond
  what seating export needs.

## Locked design decisions

- The shared callback route is the only canonical target going forward:
  `/api/v1/internal/sir-convert-a-lot/classroom-planner/seating-export-jobs`
- The legacy `{job_id}` callback route is invalid end-state behavior and must
  be removed in the same coordinated cutover once upstream subscriptions are
  corrected.
- "Upstream subscriptions" are Sir Convert-a-Lot-managed webhook subscription
  records, not Skriptoteket database rows. Cutover is incomplete until those
  upstream records are reconciled.
- Cutover must be explicit:
  - inventory old subscriptions
  - repair, patch, or replace canonical subscription state
  - delete obsolete legacy subscriptions
  - remove the compatibility route immediately after upstream state is clean
- Sir Convert-a-Lot must be part of the operator flow. Do not frame this as a
  passive waiting game where old subscriptions simply "age out" without an
  owner-controlled procedure.
- No quiet-period or compatibility-window model should be introduced for this
  slice. The cutover is inventory-first, then all-at-once update/delete, then
  route removal.

## Inventory Summary

### Skriptoteket surfaces to update

- Route definition:
  - `src/skriptoteket/web/api/v1/internal_sir_convert_callbacks.py`
- Canonical callback URL + legacy helpers:
  - `src/skriptoteket/application/curated_apps/classroom_planner/exports/webhook_contract.py`
- Canonical shared subscription attach/reuse:
  - `src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_export_jobs.py`
- Reconciliation and invalid-upstream-state cleanup:
  - `src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_export_webhook_reconciliation.py`
- Legacy hint completion plumbing:
  - `src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_export_job_completion.py`
- Operator flow / docs:
  - `scripts/hemma_deploy_and_verify_seating_export.sh`
  - `docs/runbooks/runbook-home-server.md`
- Tests:
  - `tests/unit/web/apps/classroom_planner/test_internal_sir_convert_callbacks.py`
  - `tests/unit/application/apps/classroom_planner/test_seating_export_webhook_dispatch.py`
  - `tests/unit/application/apps/classroom_planner/test_seating_export_jobs.py`
  - `tests/unit/application/apps/classroom_planner/test_seating_export_webhook_reconciliation.py`

### Sir Convert-a-Lot surfaces to use

- Supported generic webhook onboarding/mutation routes:
  - `scripts/sir_convert_a_lot/interfaces/http_routes_webhooks_v2.py`
- Runtime mutation semantics:
  - `scripts/sir_convert_a_lot/infrastructure/runtime_webhook_service_v2.py`
- Published operator/API contract:
  - `docs/converters/multi_format_conversion_service_api_v2_async_push.md`
- Contract tests proving `PATCH` and `DELETE` support:
  - `tests/sir_convert_a_lot/test_api_contract_v2_webhook_onboarding.py`

### Cross-repo inventory conclusion

- No exact seating-export callback path references were found outside
  Skriptoteket in the locally checked-out repos.
- Sir Convert-a-Lot does not carry consumer-specific legacy support for this
  callback path; the cutover uses its generic subscription APIs.

## Recommended operator model

### Skriptoteket responsibilities

- Verify the shared callback binding points to the canonical route.
- Detect stale local binding state versus actual upstream Sir Convert
  subscription state.
- Refuse to treat export readiness as complete when any non-canonical
  subscription state remains.
- Remove the runtime compatibility route and hint plumbing in the same slice
  once upstream state is corrected.

### Sir Convert-a-Lot responsibilities

- Provide one supported operator workflow to:
  - list webhook subscriptions
  - identify Skriptoteket legacy per-job callback URLs
  - patch callback URLs where appropriate
  - delete obsolete legacy subscriptions once the shared route is confirmed
- Confirm delivery backlog/DLQ is healthy before and after cutover.

## Canonical cutover phases

### Phase 1: Inventory

- List current Sir Convert webhook subscriptions for the Skriptoteket consumer
  and save the full response as cutover evidence.
- Classify each subscription as:
  - canonical shared callback
  - stale shared callback
  - legacy per-job callback
  - unrelated/non-Skriptoteket consumer

### Phase 2: Reconcile canonical shared binding

- Ensure Skriptoteket local binding state matches the canonical callback URL.
- Ensure Sir Convert has one healthy canonical shared subscription for
  Skriptoteket with the expected event types.
- Repair or recreate the shared binding when:
  - the subscription is missing
  - the callback URL is stale
  - the subscription is disabled or otherwise invalid
- Use Sir Convert's supported mutation surfaces explicitly:
  - `PATCH /v2/push/webhooks/subscriptions/{subscription_id}` for in-place
    callback URL updates when appropriate
  - `DELETE` + `POST` when replacing duplicate or otherwise bad subscriptions is
    cleaner than patching

### Phase 3: Clean up legacy upstream subscriptions

- Delete legacy per-job Skriptoteket subscriptions from Sir Convert once the
  canonical shared route is confirmed healthy.
- Do not treat "wait and see" or quiet-period observation as part of the
  intended model for this slice.

### Phase 4: Remove the compatibility route

Removal gate must require all of:

- no legacy upstream Skriptoteket subscriptions remain
- export-capable callback smoke still passes on the canonical route

Only after that gate should the `{job_id}` route, legacy helper plumbing, and
legacy-hint completion behavior be removed from Skriptoteket.

## Recommended implementation plan

- Capture an explicit upstream inventory artifact before mutation.
- Add or document the exact Sir Convert commands/API calls for:
  - inventory
  - patch-in-place when a single good shared subscription exists
  - delete + recreate when duplicate or otherwise invalid subscriptions exist
- Keep the existing Skriptoteket-side readiness/reconciliation step for export
  webhook state, but reframe it as canonical-only enforcement.
- Extend the canonical Hemma deploy/bring-up flow to include:
  - upstream subscription inventory
  - shared binding verification
  - non-canonical-state repair or explicit failure
  - post-repair callback-capable export smoke
- Delete the runtime compatibility route and legacy hint plumbing in the same
  change once upstream state is corrected.
- Rewrite this PR slice doc and the operator docs to describe a single
  coordinated cutover instead of a migration window.

## Test plan

- Focused tests for local shared-binding reconciliation logic.
- Operator verification on Hemma:
  - capture the Sir Convert subscription inventory before mutation
  - verify canonical shared subscription exists after cutover
  - verify legacy per-job subscriptions are gone after cutover
  - verify export smoke succeeds on the shared route
- Focused tests proving no legacy route or hint behavior remains in
  Skriptoteket.

## Rollback plan

- If upstream subscription mutation cannot be completed safely, stop before
  removing the runtime compatibility route.
- If the canonical smoke fails after mutation but before shim removal, restore
  the upstream subscription state first; do not introduce a new long-lived
  compatibility window as the rollback strategy.

## Implementation Status (2026-03-24)

- Skriptoteket now exposes only the canonical shared Sir Convert callback route
  for Klassrumskartan seating exports.
- The per-job `/seating-export-jobs/{job_id}` compatibility webhook route and
  `callback_job_id_hint` runtime plumbing are removed.
- Reconciliation now treats duplicate canonical, stale shared, and legacy
  per-job subscriptions as invalid upstream state to delete while preserving a
  valid canonical binding when possible.
- The Hemma operator flow now captures pre/post subscription inventories plus
  reconciliation/smoke JSON artifacts and fails closed if non-canonical seating
  export subscriptions remain after reconciliation or after the callback smoke.
- Focused unit coverage, static checks, docs validation, and a live backend
  route proof were run locally for this slice.
