---
type: review
id: REV-PR-0258
title: "Review: PR-0258 realm-aware identity projections and provisioning migration"
status: approved
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

`PR-0258` is approved after remediation. The realm-aware projection migration is implemented,
runtime projection audit events carry request correlation ids, first-login unique conflicts recover
or fail closed under DB-backed concurrency tests, invalid product context stays a generic
auth-context error, and login entry UX opens the HuleEdu ceremony directly.

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
| `.codex/handoff.md` | Current-session blocked state and next action | 5 min |

**Total estimated time:** ~48 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Require legacy HuleEdu projection backfill before dropping `external_id` | Prevents destructive subject-mapping loss | [x] |
| Block provisioning until HuleEdu signs concrete email/email-verification fields | Prevents guessing from unsigned or forbidden context data | [x] |
| Require UoW-owned idempotent provisioning semantics | Prevents duplicate/orphan users and raw unique-conflict `500`s | [x] |
| Require a projection audit/event surface | Makes provisioning and blocked outcomes reviewable and operable | [x] |
| Require full migration/API/frontend/live proof gates | Matches the actual blast radius of this slice | [x] |

## Review Checklist

- [x] Scope is bounded to `ST-28-09` / `PR-0258`
- [x] Destructive data migration risk is named
- [x] Signed provisioning contract gap is named
- [x] Idempotency and concurrent callback risk is named
- [x] Auditability surface gap is named
- [x] Verification plan gaps are named
- [x] Retained review dependency gap is named
- [x] Re-review confirmed the revised PR was implementation-ready once the concrete signed claims
  contract was available

## Review Feedback

**Reviewer:** `Lead developer`
**Date:** `2026-04-12`
**Initial verdict:** `changes_requested`

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
   required `.codex/handoff.md` live-check evidence with an exact Playwright command/artifacts
   path.

6. **P2 - Retained review gate is absent from dependencies**

   Add this retained review record and make `PR-0258` depend on `REV-PR-0258` before anyone treats
   the slice as implementation-ready.

### Resolution Update (2026-04-12)

The docs have been revised to address the review's missing contracts:

- `PR-0258` depended on `REV-PR-0258` before implementation.
- `ST-28-09` remained fail-closed until concrete signed provisioning claims were available;
  retained re-review approval is recorded below.
- The PR now requires backfilling old HuleEdu provider-subject rows into `huleedu_school`
  projections before `users.external_id` is dropped.
- The PR now names required signed context fields: `email`, `email_verified`, optional
  `given_name`, `family_name`, `display_name`, and `locale`.
- The PR now requires UoW idempotency, projection audit events, Docker migration proof,
  OpenAPI/frontend type regeneration, frontend gates, and exact live Playwright evidence.

Re-review confirmed the revised package was implementation-ready once the concrete signed
provisioning-claims dependency was available.

### Re-review (2026-04-12)

**Reviewer:** `Lead developer`
**Verdict:** `approved`

The six required changes are satisfied:

- legacy `auth_provider=huleedu` + `external_id` rows must backfill into `huleedu_school`
  projections before `users.external_id` is dropped
- provisioning is gated on `email`, `email_verified`, and optional profile/locale claims being
  explicit signed `InternalIdentityContextV1` fields
- concurrent first-login callbacks require UoW-owned get-or-create/upsert semantics and regression
  proof
- projection outcomes require a dedicated audit/event surface with realm/subject/context metadata
- the verification plan includes Docker migration proof, OpenAPI/frontend type regeneration,
  frontend gates, live Playwright proof, and handoff evidence
- `PR-0258` now depends on this retained review

This approval cleared the planning review gate. The subsequent implementation resolved the
signed-claims dependency by modeling and verifying the concrete fields in
`InternalIdentityContextV1`, but implementation review below requested remediation before final
closure.

### Implementation Review (2026-04-12)

**Reviewer:** `Lead developer`
**Verdict:** `changes_requested`

Required remediation:

1. Runtime `identity_projection_events` must persist the request correlation id so operators can
   connect projection/provisioning outcomes to headers, logs, and smoke artifacts.
2. First-login provisioning must recover from email/projection unique conflicts with
   repository-owned no-conflict insert/get-or-create behavior and DB-backed concurrent regression
   tests, not only advisory locks.
3. Invalid or unsupported signed product context belongs to generic auth ceremony/context error
   handling, not the provisioning/local-access-required UX.
4. Normal "Logga in" actions must open the HuleEdu login ceremony directly. `/auth/login?next=...`
   may remain as a protected-route transition/fallback, but it must auto-handoff instead of asking
   users for a second login CTA.
5. The focused backend, migration, frontend, docs, and live `pr-0258-auth-projection` proof must be
   rerun before `PR-0254` starts.

### Implementation Review Remediation (2026-04-12)

**Reviewer:** `Lead developer`
**Verdict:** `approved`

The requested remediation is complete:

- runtime `identity_projection_events` persist request correlation ids from the app-continuation
  request metadata
- user/projection creation now uses no-conflict repository inserts and re-read/fail-closed
  recovery rather than relying only on advisory locks
- DB-backed tests cover same-subject concurrent callbacks, same-email competing subjects, and a
  projection unique-conflict recovery path that rolls back orphan user writes
- invalid product context remains a generic auth ceremony/context error; local-access UX remains
  reserved for missing projection, linking-required, and inactive/missing local user outcomes
- public "Logga in" actions link directly to the HuleEdu login ceremony, while `/auth/login` is an
  auto-handoff fallback route
- the live PR-0258 proof now also verifies direct login handoff and writes
  `.artifacts/playwright-pr-0258-auth-projection/login-auto-handoff.png`

### Suggestions (Optional)

- Consider a narrow HuleEdu provider task that only adds signed provisioning claims before
  Skriptoteket starts the user/projection auto-provisioning branch.
- Keep the projection audit event model separate from `login_events` unless `login_events` is also
  migrated away from provider-centric `AuthProvider`.

### Decision Approvals

- [x] Legacy HuleEdu projection backfill before `external_id` removal
- [x] Concrete signed provisioning claims before auto-provisioning
- [x] UoW-owned idempotent provisioning
- [x] Dedicated projection audit/event surface
- [x] Full migration/API/frontend/live proof gates

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-0258` | Added the retained review dependency, expanded migration/provisioning/idempotency/audit/verification contracts, implemented the slice, and closed implementation remediation |
| 2 | `ST-28-09` | Closed after runtime audit correlation, unique-conflict recovery, generic invalid-context handling, and direct login handoff were implemented and proven |
| 3 | `EPIC-28` | Updated sequencing so `PR-0254` follows the completed realm-aware projection implementation |
| 4 | `REF-hule-education-product-identity-realms-and-skriptoteket-standalone-identity` | Recorded the projection migration constraints and direct ceremony login direction |
| 5 | `.codex/handoff.md` | Updated the current lane and next action to the completed `PR-0258` state |
| 6 | `REV-PR-0258` | Approved the revised contract before implementation and approved the implementation remediation after proof |
