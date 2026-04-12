---
type: review
id: REV-PR-0258
title: "Review: PR-0258 realm-aware identity projections and provisioning migration"
status: changes_requested
owners: "agents"
created: 2026-04-12
updated: 2026-04-12
reviewer: "Lead developer"
prs:
  - PR-0258
adrs:
  - ADR-0083
links:
  - EPIC-28
  - ST-28-09
  - PR-0255
  - PR-0256
  - PR-0257
  - PR-0254
---

## TL;DR

`PR-0258` has the right direction but is not implementation-ready. The initial slice would have
removed the only stored legacy HuleEdu subject mapping before defining a backfill/preflight path,
and it relied on signed provisioning claims that the current `InternalIdentityContextV1` does not
yet define. The PR is blocked pending retained re-review.

## Problem Statement

`ST-28-09` is the destructive identity migration slice between the temporary `PR-0255`
provider-subject bridge and the final realm-aware projection model. Because this slice changes
identity lookup, database schema, provisioning, and local authorization entry, its plan must be
safe before implementation begins.

## Proposed Solution

Revise `PR-0258` so implementation cannot strand current HuleEdu-linked users, guess at
provisioning claims, or treat idempotency/auditability as slogans. The reworked PR must specify:

- migration preflight/backfill for existing `auth_provider=huleedu` + `external_id` users
- concrete signed provisioning claim fields and fail-closed verifier tests
- UoW-owned get-or-create/upsert behavior for concurrent first-login callbacks
- an owned projection audit/event surface
- the full repo-required verification gates for migrations, API/client contracts, frontend checks,
  live Playwright proof, and handoff evidence

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0258-st-28-09-realm-aware-identity-projections-and-provisioning-migration.md` | PR scope, migration contract, provisioning contract, verification | 25 min |
| `docs/backlog/stories/story-28-09-realm-aware-projection-provisioning-and-local-rbac.md` | Parent story status, acceptance criteria, dependencies | 10 min |
| `docs/reference/ref-hule-education-product-identity-realms-and-skriptoteket-standalone-identity.md` | Product realm direction and remaining provider obligations | 8 min |
| `.agents/handoff.md` | Current-session blocked state and next action | 5 min |

**Total estimated time:** ~48 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Require legacy HuleEdu projection backfill before dropping `external_id` | Prevents destructive subject-mapping loss | [ ] |
| Block provisioning until HuleEdu signs concrete email/email-verification fields | Prevents guessing from unsigned or forbidden context data | [ ] |
| Require UoW-owned idempotent provisioning semantics | Prevents duplicate/orphan users and raw unique-conflict `500`s | [ ] |
| Require a projection audit/event surface | Makes provisioning and blocked outcomes reviewable and operable | [ ] |
| Require full migration/API/frontend/live proof gates | Matches the actual blast radius of this slice | [ ] |

## Review Checklist

- [x] Scope is bounded to `ST-28-09` / `PR-0258`
- [x] Destructive data migration risk is named
- [x] Signed provisioning contract gap is named
- [x] Idempotency and concurrent callback risk is named
- [x] Auditability surface gap is named
- [x] Verification plan gaps are named
- [x] Retained review dependency gap is named
- [ ] Re-review confirms the revised PR is implementation-ready

## Review Feedback

**Reviewer:** `Lead developer`
**Date:** `2026-04-12`
**Verdict:** `changes_requested`

### Required Changes

1. **P0 - Data migration would strand existing projections**

   Add a preflight/backfill contract before dropping `users.external_id`: copy existing
   `auth_provider=huleedu` + nonblank `external_id` rows into realm-aware projections, define the
   realm for those rows, fail on ambiguous data, and prove app continuation still resolves them
   after upgrade.

2. **P1 - Provisioning claims are not a concrete signed contract**

   Name the signed payload fields, assurance semantics, verifier/model changes, and profile fields
   needed to create a `UserProfile`. Because `InternalIdentityContextV1` forbids extra fields,
   provisioning must fail closed unless HuleEdu supplies those explicit signed claims.

3. **P1 - Idempotency is asserted but not designed**

   Define transaction ordering, conflict handling, and concurrent callback behavior across
   user/profile/projection creation. Require a UoW-owned get-or-create/upsert strategy plus a
   concurrency or unique-conflict regression test.

4. **P2 - Auditability has no owned surface**

   Define the audit sink, event schema, and required outcomes. The surface must record success,
   blocked provisioning, duplicate-email/linking-required, unsupported-realm, and migration
   outcomes with realm and subject metadata.

5. **P2 - Verification plan misses repo-required gates**

   Add Docker migration tests, frontend type/lint gates, OpenAPI/client regeneration proof, and the
   required `.agents/handoff.md` live-check evidence with an exact Playwright command/artifacts
   path.

6. **P2 - Retained review gate is absent from dependencies**

   Add this retained review record and make `PR-0258` depend on `REV-PR-0258` before anyone treats
   the slice as implementation-ready.

### Resolution Update (2026-04-12)

The docs have been revised to address the review's missing contracts:

- `PR-0258` is now `blocked` and depends on `REV-PR-0258`.
- `ST-28-09` is blocked until retained re-review approves the contract and HuleEdu signed
  provisioning claims exist.
- The PR now requires backfilling old HuleEdu provider-subject rows into `huleedu_school`
  projections before `users.external_id` is dropped.
- The PR now names required signed context fields: `email`, `email_verified`, optional
  `given_name`, `family_name`, `display_name`, and `locale`.
- The PR now requires UoW idempotency, projection audit events, Docker migration proof,
  OpenAPI/frontend type regeneration, frontend gates, and exact live Playwright evidence.

The review remains `changes_requested` until re-review confirms the revised package is
implementation-ready.

### Suggestions (Optional)

- Consider a narrow HuleEdu provider task that only adds signed provisioning claims before
  Skriptoteket starts the user/projection auto-provisioning branch.
- Keep the projection audit event model separate from `login_events` unless `login_events` is also
  migrated away from provider-centric `AuthProvider`.

### Decision Approvals

- [ ] Legacy HuleEdu projection backfill before `external_id` removal
- [ ] Concrete signed provisioning claims before auto-provisioning
- [ ] UoW-owned idempotent provisioning
- [ ] Dedicated projection audit/event surface
- [ ] Full migration/API/frontend/live proof gates

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-0258` | Marked blocked, added `REV-PR-0258` dependency, and expanded migration/provisioning/idempotency/audit/verification contracts |
| 2 | `ST-28-09` | Marked blocked pending retained re-review and signed HuleEdu provisioning claims |
| 3 | `EPIC-28` | Updated sequencing so `PR-0258` must pass re-review before implementation and `PR-0254` |
| 4 | `REF-hule-education-product-identity-realms-and-skriptoteket-standalone-identity` | Recorded the sharper projection migration constraints |
| 5 | `.agents/handoff.md` | Updated the current lane and next action to the blocked re-review state |
