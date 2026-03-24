---
type: pr
id: PR-0125
title: "Klassrumskartan: legacy seating export callback cutover and decommission"
status: ready
owners: "agents"
created: 2026-03-24
updated: 2026-03-24
stories:
  - "ST-26-01"
tags: ["backend", "ops", "klassrumskartan", "export", "webhooks", "sir-convert-a-lot", "remediation"]
acceptance_criteria:
  - "Given the shared callback route is canonical, when Skriptoteket deploys or verifies seating export readiness, then it explicitly detects and reconciles stale Sir Convert-a-Lot webhook subscription state instead of relying on the temporary per-job callback route indefinitely."
  - "Given old per-job Sir Convert webhook subscriptions still exist, when operators run the cutover procedure, then legacy `/seating-export-jobs/{job_id}` subscriptions are inventoried, migrated or removed deliberately, and not left to age out implicitly."
  - "Given the temporary cutover callback route remains during the migration window, when it is hit, then Skriptoteket records observable evidence so operators can prove when the route is no longer in use."
  - "Given the migration window completes, when no legacy upstream subscriptions remain and no old-route traffic is observed for the agreed quiet period, then the compatibility callback route can be removed with a documented gate."
  - "Given Sir Convert-a-Lot owns webhook subscriptions upstream, when this cutover is documented, then the operator path includes explicit Sir Convert-a-Lot coordination rather than treating the migration as Skriptoteket-only."
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

Leaving the compatibility route in place forever is the wrong endpoint state:

- it hides whether the migration is actually complete
- it leaves route cleanup dependent on guesswork
- it keeps Skriptoteket carrying legacy callback semantics that are supposed to
  be temporary

## Goal

Define and implement one explicit cutover/decommission plan for the legacy
per-job callback route, including upstream Sir Convert-a-Lot subscription
inventory, reconciliation, observability, and a hard removal gate.

## Non-goals

- Changing the public seating export API or teacher-facing export UX.
- Replacing polling fallback.
- Reworking the shared callback dispatcher introduced in `PR-0121`.
- Building a general-purpose multi-consumer webhook migration framework beyond
  what seating export needs.

## Locked design decisions

- The shared callback route is the only canonical target going forward:
  `/api/v1/internal/sir-convert-a-lot/classroom-planner/seating-export-jobs`
- The legacy `{job_id}` callback route is temporary and must be removable.
- "Upstream subscriptions" are Sir Convert-a-Lot-managed webhook subscription
  records, not Skriptoteket database rows. Cutover is incomplete until those
  upstream records are reconciled.
- Migration must be explicit:
  - inventory old subscriptions
  - repair or replace canonical subscription state
  - delete obsolete legacy subscriptions
  - prove the old route is quiet before removal
- Sir Convert-a-Lot must be part of the operator flow. Do not frame this as a
  passive waiting game where old subscriptions simply "age out" without an
  owner-controlled procedure.

## Recommended operator model

### Skriptoteket responsibilities

- Verify the shared callback binding points to the canonical route.
- Detect stale local binding state versus actual upstream Sir Convert
  subscription state.
- Record observable evidence for hits on the legacy `{job_id}` callback route.
- Refuse to treat export readiness as complete when only legacy callback wiring
  exists.

### Sir Convert-a-Lot responsibilities

- Provide one supported operator workflow to:
  - list webhook subscriptions
  - identify Skriptoteket legacy per-job callback URLs
  - patch callback URLs where appropriate
  - delete obsolete legacy subscriptions once the shared route is confirmed
- Confirm delivery backlog/DLQ is healthy before and after migration.

## Canonical migration phases

### Phase 1: Inventory

- List current Sir Convert webhook subscriptions for the Skriptoteket consumer.
- Classify each subscription as:
  - canonical shared callback
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

### Phase 3: Observe legacy traffic

- Add explicit telemetry or structured logs for requests hitting the legacy
  `{job_id}` route.
- Record route usage during the migration window so operators know whether old
  upstream subscriptions are still active.

### Phase 4: Clean up legacy upstream subscriptions

- Delete legacy per-job Skriptoteket subscriptions from Sir Convert once the
  canonical shared route is confirmed healthy.
- Treat "wait and see" as a fallback only if deletion/update capability is
  unavailable; it is not the preferred migration strategy.

### Phase 5: Remove the compatibility route

Removal gate must require all of:

- no legacy upstream Skriptoteket subscriptions remain
- no legacy-route hits are observed during the agreed quiet window
- export-capable callback smoke still passes on the canonical route

Only after that gate should the `{job_id}` route be removed from
`internal_sir_convert_callbacks.py`.

## Recommended implementation plan

- Add one dedicated Skriptoteket-side readiness/reconciliation step for export
  webhook state.
- Add structured logging and/or metrics for legacy callback-route hits.
- Document the Sir Convert subscription inventory + cleanup commands/runbook
  that operators should use during cutover.
- Extend the canonical Hemma deploy/bring-up flow to include:
  - shared binding verification
  - upstream subscription inventory
  - stale-state repair or explicit failure
  - post-repair callback-capable export smoke
- Document the quiet-window removal gate and the exact evidence required before
  deleting the old route.

## Test plan

- Focused tests for local shared-binding reconciliation logic.
- Focused tests proving legacy-route hits emit the expected structured evidence.
- Operator verification on Hemma:
  - list Sir Convert subscriptions
  - verify canonical shared subscription exists
  - verify legacy per-job subscriptions can be identified deterministically
  - verify export smoke succeeds on the shared route
- Pre-removal verification:
  - prove no legacy subscriptions remain
  - prove no legacy-route hits in the defined quiet window

## Rollback plan

- Keep the compatibility route in place and suspend decommission while retaining
  the shared route as canonical if migration evidence is incomplete or Sir
  Convert cleanup cannot be completed safely.
