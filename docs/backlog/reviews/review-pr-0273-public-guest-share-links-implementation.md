---
type: review
id: REV-PR-0273
title: "Review: PR-0273 public guest share links implementation"
status: approved
owners: "agents"
created: 2026-04-30
updated: 2026-05-01
reviewer: "lead-developer"
prs:
  - PR-0273
adrs:
  - ADR-0079
  - ADR-0080
  - ADR-0084
links:
  - EPIC-26
  - ST-26-06
  - REV-ST-26-06
  - PR-0274
---

## TL;DR

`PR-0273` is implementation-approved after re-review. The original four
blockers around race-safe share creation, previous-link supersede after edits,
frontend retry idempotency, and public guest provenance validation are
remediated, and the PostgreSQL advisory-lock path now has accepted
independent-session integration proof.

## Problem Statement

`PR-0273` implements the public guest side of `ST-26-06`: anonymous
Klassrumskartan users can create 60-day share links from browser-owned grouping
and seating snapshots. The governing contract requires cookie-agnostic helper
routes, strict expected-revision validation, hashed browser-held revoke secrets,
active-share ceilings, supersede semantics, idempotent replay, and no
owner-scoped authority for public guest artifacts.

The implementation review checks whether the current diff satisfies those
runtime guarantees, not whether the planning surface was approved.

## Proposed Solution

Keep the public guest helper/read model. The required remediation is accepted:

- make create-or-reuse, active-limit enforcement, and previous-link supersede a
  single race-safe persistence operation
- key browser-held previous-link metadata by stable snapshot identity plus draft
  kind, not snapshot content hash
- keep pending client operation ids and revoke secrets across retryable failures
- reject all owner/source provenance ids for `PUBLIC_GUEST` share artifact
  commands

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0273-st-26-06-public-guest-klassrumskartan-share-links-with-ttl-and-supersede.md` | Scope, acceptance criteria, and verification claims | 10 min |
| `src/skriptoteket/application/curated_apps/classroom_planner/handlers/public_shares.py` | Public guest create/reuse/supersede transaction semantics | 18 min |
| `src/skriptoteket/application/curated_apps/classroom_planner/handlers/share_artifacts.py` | Public guest artifact validation boundary | 8 min |
| `src/skriptoteket/infrastructure/repositories/classroom_planner_share_artifacts.py` | Repository-level idempotency, active-count, and revoke behavior | 12 min |
| `migrations/versions/e2f4a6b8c9d0_add_public_guest_share_controls.py` | Public guest metadata/index support | 6 min |
| `src/skriptoteket/web/api/v1/public_apps_classroom_planner_shares.py` | Cookie-agnostic public helper route and response contract | 8 min |
| `frontend/apps/skriptoteket/src/views/apps/classroomPlannerPublicShareFlow.ts` | Browser-held revoke metadata, idempotency, retry behavior | 15 min |
| `frontend/apps/skriptoteket/src/views/apps/classroomPlannerPublicShareApi.ts` | Public helper API client path and credentials behavior | 5 min |
| `tests/unit/application/apps/classroom_planner/test_public_shares.py` | Backend proof coverage and missing race cases | 8 min |
| `tests/unit/web/test_public_apps_classroom_planner_shares.py` | Route proof coverage | 5 min |
| `frontend/apps/skriptoteket/src/views/apps/*Public*Share*.ts` | Frontend proof coverage gaps | 8 min |

**Total estimated time:** ~103 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Accept remediated backend create/reuse/supersede transaction shape | It now performs create-or-reuse, active-limit enforcement, and previous supersede through one repository operation inside one Unit of Work with transaction-scoped advisory locking. | [x] |
| Accept stable previous-link metadata identity | Latest browser-held metadata is keyed by stable snapshot id plus draft kind, while content hash stays in the value. | [x] |
| Accept pending operation id generation as retry-safe | Pending operation metadata preserves client operation id and revoke secret across retryable create failures for the same snapshot/draft/revision. | [x] |
| Accept remediated public guest artifact validation | `PUBLIC_GUEST` commands reject owner, draft, roster, and template provenance ids. | [x] |
| Keep the public helper route family as the right boundary | Dedicated public helper routes are the correct route family for this slice | [x] |
| Keep the 60-day TTL and hashed revoke-secret model | The model matches the accepted `ADR-0084` exception when fixed | [x] |
| Accept PostgreSQL advisory-lock proof coverage | The implementation depends on `pg_advisory_xact_lock(...)`; independent-session PostgreSQL proof now covers replay, supersede, and active-limit enforcement. | [x] |

## Review Checklist

- [x] Scope is bounded to `PR-0273` implementation review
- [x] Governing `REV-ST-26-06` planning approval was read as context
- [x] Public helper routes stay outside owner-scoped APIs
- [x] Ambient browser credentials are not needed for frontend public helper calls
- [x] Share creation and supersede are atomic and race-safe
- [x] Browser-held previous-link metadata survives snapshot edits
- [x] Retry/double-click behavior replays the same client operation where required
- [x] Public guest artifacts cannot persist owner-scoped or source provenance ids
- [x] Tests cover the race/retry/supersede failure modes found in this review
- [x] PostgreSQL integration tests prove the advisory-lock transaction path

## Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-04-30`
**Verdict:** `changes_requested`

### Required Changes

1. **P1: Share creation is not race-safe or atomic.**

   `src/skriptoteket/application/curated_apps/classroom_planner/handlers/public_shares.py:238`
   reads the existing client operation, resolves the previous share, and counts
   active links inside one Unit of Work, then creates the new artifact through
   another handler/Unit of Work, then revokes the previous link in a third Unit
   of Work.

   Failure modes:

   - concurrent requests with the same `client_operation_id` can hit the unique
     index and surface an infrastructure failure instead of returning the
     existing share
   - two tabs with the same previous revoke secret can both create new links
   - active-link ceilings can be bypassed between count and insert

   Required fix: move create-or-reuse, active-limit enforcement, and conditional
   supersede into one repository transaction with explicit conflict handling,
   row locking, advisory locking, or equivalent PostgreSQL-safe behavior. The
   result must return the existing artifact for replayed client operations and
   must not create contradictory newest-link state.

   Proof required:

   - backend concurrency test for same `client_operation_id`
   - backend concurrency test for two-tab supersede with the same previous
     token/revoke secret
   - backend test proving active-share ceilings hold under concurrent create
     attempts
   - focused command: `pdm run pytest -q tests/unit/application/apps/classroom_planner/test_public_shares.py`

2. **P1: Previous guest links are not superseded after edits.**

   `frontend/apps/skriptoteket/src/views/apps/classroomPlannerPublicShareFlow.ts:78`
   includes `snapshot.snapshot_content_hash` in the localStorage key. That hash
   changes whenever the browser-owned snapshot is edited or flushed. A teacher
   who creates a link, changes the same guest snapshot, and clicks `Dela länk`
   again still has the previous revoke secret in the browser, but the flow looks
   under a different key and sends no `previous_public_path` or
   `previous_revoke_secret`.

   Required fix: key latest public guest share metadata by stable
   `snapshot_id` plus `draft_kind`; keep the content hash out of the lookup key.
   If content hash needs to be retained for diagnostics, store it inside the
   value rather than making it part of the identity.

   Proof required:

   - frontend test that creates metadata for a snapshot, changes only
     `snapshot_content_hash`, and verifies the next share sends the previous
     public path and revoke secret
   - focused command for the new test plus existing guest share flow tests

3. **P2: Client operation id is not reused for real retries.**

   `frontend/apps/skriptoteket/src/views/apps/classroomPlannerPublicShareFlow.ts:192`
   generates a fresh `clientOperationId` and `revokeSecret` on every
   `startShare()` call. If the server creates the share but the browser sees a
   network failure before metadata is stored, the next click is not a replay of
   the same client operation. It can create a second guest artifact and cannot
   supersede the first one.

   Required fix: keep a pending operation id and revoke secret for the relevant
   snapshot, draft kind, and revision until the request definitively succeeds or
   is intentionally abandoned. A retry after a transport failure must replay the
   same operation and secret.

   Proof required:

   - frontend test for retry after a rejected/transport-failed create call
   - assertion that the second call reuses the same `clientOperationId` and
     `revokeSecret`
   - assertion that successful completion clears or converts pending metadata
     into latest-share metadata

4. **P2: Public-guest validation still allows owner-scoped provenance ids.**

   `src/skriptoteket/application/curated_apps/classroom_planner/handlers/share_artifacts.py:306`
   rejects `owner_user_id` and `draft_id` for public guest artifacts, but does
   not reject `roster_id` or `template_id`. The current public route does not
   expose those fields, but this handler is the application boundary for share
   artifact creation, and `PR-0273` explicitly requires public guest rows to
   store no owner, draft, roster, or template authority.

   Required fix: reject `roster_id` and `template_id` for
   `ClassroomPlannerShareArtifactSource.PUBLIC_GUEST`.

   Proof required:

   - unit test proving public guest commands with `roster_id` or `template_id`
     are rejected
   - focused command: `pdm run pytest -q tests/unit/application/apps/classroom_planner/test_share_artifacts.py`

### Suggestions (Optional)

- Keep the eventual repository API honest by naming the operation after the
  public guest semantics, for example `create_or_reuse_public_guest_share`,
  rather than exposing a grab-bag of low-level calls.
- Retained after re-review: PostgreSQL advisory-lock integration coverage is a
  required blocker, not an optional suggestion.
- Consider recording a short re-review checklist in this same document after
  remediation, instead of creating another review record.

### Decision Approvals

- [x] Accept remediated backend create/reuse/supersede transaction shape
- [x] Accept stable previous-link metadata identity
- [x] Accept pending operation id generation as retry-safe
- [x] Accept remediated public guest artifact validation
- [x] Keep the public helper route family as the right boundary
- [x] Keep the 60-day TTL and hashed revoke-secret model
- [x] Accept PostgreSQL advisory-lock proof coverage

### Verification Run During Review

- `pdm run pytest -q tests/unit/application/apps/classroom_planner/test_public_shares.py tests/unit/web/test_public_apps_classroom_planner_shares.py tests/unit/web/apps/classroom_planner/test_share_pages.py tests/unit/application/apps/classroom_planner/test_share_artifacts.py`
  - passed, but did not cover the race/retry/supersede-after-edit failure modes
- `pdm run fe-test -- --run src/views/apps/components/PlannerExportActionGroup.spec.ts src/views/apps/usePublicGroupingExportFlow.spec.ts src/views/apps/usePublicSeatingExportFlow.spec.ts`
  - passed, but did not include public guest share-flow retry or metadata-key
    tests
- `git diff --check`
  - passed

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0273` | Created retained implementation review record with `changes_requested` verdict. |
| 2 | `PR-0273` | Linked the retained implementation review as a dependency so the done-state does not hide the blocker. |
| 3 | `docs/index.md` | Added the new review record to the backlog review index. |

## Remediation Applied

**Date:** `2026-04-30`
**Status:** implemented, including PostgreSQL integration proof; pending independent re-review

| Finding | Remediation | Proof |
|---------|-------------|-------|
| P1 atomic/race-safe share creation | Added a single public guest repository operation for create-or-reuse, active-limit enforcement, and previous-link supersede inside one Unit of Work. The PostgreSQL implementation serializes relevant client-operation, snapshot, and previous-token keys with transaction-scoped advisory locks. | `tests/unit/application/apps/classroom_planner/test_public_shares.py` now covers same-client-operation concurrency, two-tab supersede, and concurrent active-limit enforcement. |
| P1 PostgreSQL advisory-lock proof | Added repository integration tests that run public guest create/reuse/supersede through independent `AsyncSession` transactions against the migrated PostgreSQL test fixture. | `tests/integration/infrastructure/repositories/test_classroom_planner_public_guest_share_concurrency.py` covers same-client-operation replay, two-tab supersede, and active-limit enforcement under concurrent repository calls. |
| P1 previous links after edits | Changed browser latest-share metadata lookup to stable `snapshot_id + draft_kind`; snapshot content hash is retained in the value, not the lookup identity. | `frontend/apps/skriptoteket/src/views/apps/classroomPlannerPublicShareFlow.spec.ts` covers supersede metadata after `snapshot_content_hash` changes. |
| P2 retry idempotency | Added pending public guest share operation metadata keyed by `snapshot_id + draft_kind + revision`; retryable failures reuse the same client operation id and revoke secret until success. | `frontend/apps/skriptoteket/src/views/apps/classroomPlannerPublicShareFlow.spec.ts` covers retry after a failed create call and pending cleanup after success. |
| P2 source provenance ids | Tightened `PUBLIC_GUEST` artifact validation to reject `owner_user_id`, `draft_id`, `roster_id`, and `template_id`. | `tests/unit/application/apps/classroom_planner/test_share_artifacts.py` covers roster/template rejection. |

### Remediation Verification

- `pdm run pytest -q tests/unit/application/apps/classroom_planner/test_public_shares.py tests/unit/application/apps/classroom_planner/test_share_artifacts.py tests/unit/web/test_public_apps_classroom_planner_shares.py`
- `pdm run pytest -q tests/integration/infrastructure/repositories/test_classroom_planner_share_artifacts.py tests/integration/infrastructure/repositories/test_classroom_planner_public_guest_share_concurrency.py`
- `pdm run fe-test -- --run src/views/apps/classroomPlannerPublicShareFlow.spec.ts src/views/apps/components/PlannerExportActionGroup.spec.ts src/views/apps/usePublicGroupingExportFlow.spec.ts src/views/apps/usePublicSeatingExportFlow.spec.ts`
- `pdm run typecheck`
- `pdm run fe-type-check`
- `pdm run fe-lint`

## Re-Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-04-30`
**Verdict:** `changes_requested`

### Findings

1. **P1: PostgreSQL advisory-lock path lacks integration proof.**

   `src/skriptoteket/infrastructure/repositories/classroom_planner_share_artifacts.py:261`
   implements public guest create/reuse/supersede in the PostgreSQL repository,
   and `src/skriptoteket/infrastructure/repositories/classroom_planner_share_artifacts.py:490`
   serializes the critical lanes with
   `pg_advisory_xact_lock(hashtextextended(:lock_key, 0))`. The current proof is
   still limited to unit tests with an in-memory fake lock and frontend flow
   tests; it does not execute the actual SQL advisory lock, unique constraints,
   flush ordering, or concurrent sessions against PostgreSQL.

   Why this blocks: the race-safety contract depends on database-specific lock
   semantics. Without an integration test using separate PostgreSQL sessions,
   a broken lock key, dialect incompatibility, transaction boundary mistake, or
   flush/constraint behavior can pass the fake test suite while failing under
   real concurrency.

   Required fix: add integration repository tests, preferably under
   `tests/integration/infrastructure/repositories/test_classroom_planner_share_artifacts.py`,
   that run against the existing PostgreSQL test fixture with independent
   sessions and prove:

   - concurrent calls with the same `client_operation_id` return one created
     artifact and one replayed artifact, not an integrity error
   - concurrent supersede calls with the same previous token/revoke secret do
     not create contradictory newest-link state
   - concurrent active-limit checks for the same guest snapshot fingerprint
     cannot bypass the ceiling

   Proof required:

   - focused command for the new integration tests, for example
     `pdm run pytest -q tests/integration/infrastructure/repositories/test_classroom_planner_share_artifacts.py`
   - keep the existing unit and frontend remediation tests green

### Closure Notes

- The original four retained findings are closed at the unit/flow-test level.
- Backend share creation now builds the unsaved artifact, then resolves replay,
  active ceiling, and previous supersede through
  `create_or_reuse_public_guest_share(...)` inside a single Unit of Work.
- The PostgreSQL repository serializes client-operation, snapshot-fingerprint,
  and previous-token lanes with transaction-scoped advisory locks before it
  checks replay, locks the previous share candidate, counts active shares, and
  inserts/revokes.
- The public guest artifact command validator rejects owner, draft, roster, and
  template ids.
- Browser latest-share metadata is stable across content edits, and pending
  operation metadata reuses the same client operation id and revoke secret after
  a rejected create call until success.
- PostgreSQL advisory-lock behavior now has independent-session integration
  proof, and remains pending independent review approval.

### Re-Review Verification

- `pdm run pytest -q tests/unit/application/apps/classroom_planner/test_public_shares.py tests/unit/application/apps/classroom_planner/test_share_artifacts.py tests/unit/web/test_public_apps_classroom_planner_shares.py`
  - passed, 18 tests
- `pdm run fe-test -- --run src/views/apps/classroomPlannerPublicShareFlow.spec.ts src/views/apps/components/PlannerExportActionGroup.spec.ts src/views/apps/usePublicGroupingExportFlow.spec.ts src/views/apps/usePublicSeatingExportFlow.spec.ts`
  - passed, 14 tests
- `pdm run typecheck`
  - passed
- `pdm run fe-type-check`
  - passed
- `pdm run fe-lint`
  - passed

## P1 Integration Proof Response

**Implementer:** `codex`
**Date:** `2026-04-30`
**Status:** ready for re-review

Added
`tests/integration/infrastructure/repositories/test_classroom_planner_public_guest_share_concurrency.py`
with migrated PostgreSQL/testcontainers coverage that opens independent
`AsyncSession` transactions for concurrent repository calls. The tests prove:

- same `client_operation_id` creates one row and returns one replayed artifact
- two-tab supersede with the same previous token/revoke secret creates one
  newest link and marks the other attempt as stale
- active-share ceilings for the same guest snapshot fingerprint cannot be
  bypassed by concurrent creates

Verification:

- `pdm run pytest -q tests/integration/infrastructure/repositories/test_classroom_planner_share_artifacts.py tests/integration/infrastructure/repositories/test_classroom_planner_public_guest_share_concurrency.py`
  - passed, 5 tests

## Final Re-Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-04-30`
**Verdict:** `approved`

### Findings

None. The PostgreSQL advisory-lock proof blocker is closed.

### Closure Notes

- `tests/integration/infrastructure/repositories/test_classroom_planner_public_guest_share_concurrency.py`
  uses the migrated PostgreSQL test fixture and independent `AsyncSession`
  transactions for concurrent repository calls.
- The integration proof covers same-client-operation replay, two-tab supersede
  with the same previous token/revoke secret, and active-limit enforcement for
  the same guest snapshot fingerprint.
- The earlier unit and frontend flow proofs remain green.

### Final Verification

- `pdm run pytest -q tests/integration/infrastructure/repositories/test_classroom_planner_share_artifacts.py tests/integration/infrastructure/repositories/test_classroom_planner_public_guest_share_concurrency.py`
  - passed, 5 tests
- `pdm run pytest -q tests/unit/application/apps/classroom_planner/test_public_shares.py tests/unit/application/apps/classroom_planner/test_share_artifacts.py tests/unit/web/test_public_apps_classroom_planner_shares.py`
  - passed, 18 tests
- `pdm run fe-test -- --run src/views/apps/classroomPlannerPublicShareFlow.spec.ts src/views/apps/components/PlannerExportActionGroup.spec.ts src/views/apps/usePublicGroupingExportFlow.spec.ts src/views/apps/usePublicSeatingExportFlow.spec.ts`
  - passed, 14 tests
- `pdm run typecheck`
  - passed
- `pdm run fe-type-check`
  - passed
- `pdm run fe-lint`
  - passed

## Current-Link Re-Review Gap Closure

**Implementer:** `codex`
**Date:** `2026-05-01`
**Verdict:** `remediated; pending independent re-review`

The later current-link review identified two follow-up gaps after the warm
same-session revoke path:

- The public share flow now persists the active display row in browser-held
  metadata, hydrates it into a fresh flow after reload for the same
  snapshot/draft kind, and can revoke it with the retained secret.
- The public revoke route keeps the capped raw-body helper but advertises an
  explicit OpenAPI request body for `public_path` and `revoke_secret`; generated
  TypeScript no longer emits `requestBody?: never` for this operation.

Verification:

- `pdm run fe-test -- --run src/views/apps/classroomPlannerPublicShareFlow.spec.ts`
  - passed, 4 tests
- `pdm run pytest -q tests/unit/web/test_public_apps_classroom_planner_shares.py`
  - passed, 4 tests
- `pdm run fe-gen-api-types`
  - passed; regenerated revoke operation exports `public_path` and
    `revoke_secret` request-body fields
- `pdm run fe-type-check`
  - passed
- `pdm run fe-lint`
  - passed
- `pdm run typecheck`
  - passed
- `pdm run lint`
  - passed
