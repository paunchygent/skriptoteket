---
type: review
id: REV-PR-0255
title: "Review: PR-0255 HuleEdu context and local authorization remediation"
status: approved
owners: "agents"
created: 2026-04-11
updated: 2026-04-11
reviewer: "lead-developer"
prs:
  - PR-0255
adrs:
  - ADR-0076
  - ADR-0082
links:
  - EPIC-28
  - ST-28-01
  - PR-0251
  - REV-PR-0251
---

## TL;DR

`PR-0255` now targets the two `REV-PR-0251` fault lines with an implementation-ready contract:
app continuation must be HuleEdu-context-derived, and Skriptoteket-local user identity and
authorization must come from the local projection rather than HuleEdu provider roles.

## Problem Statement

`PR-0251` cannot close while `GET /api/v1/profile/app-continuation` still depends on the old local
session-cookie path or while the SPA derives local RBAC from HuleEdu shared-session roles.
`PR-0255` proposes the remediation slice that should make those boundaries concrete.

## Proposed Solution

Add a protocol-first HuleEdu request-context verifier, resolve or provision the Skriptoteket-local
user/profile projection from that verified context, return that projection through app-local
continuation, and update the SPA so local role/app authorization comes from the continuation rather
than `policy.roles`.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0255-st-28-01-pr-0251-remediation-huleedu-context-and-local-authorization-projection.md` | Remediation scope, acceptance criteria, proof plan | 15 min |
| `docs/backlog/reviews/review-pr-0251-app-local-bootstrap-continuation.md` | Original findings and proof requirements | 8 min |
| `docs/adr/adr-0076-huleedu-owned-browser-session-authority-for-skriptoteket.md` | Gateway-owned browser auth boundary | 5 min |
| `docs/adr/adr-0082-app-local-bootstrap-continuation-on-huleedu-session.md` | App-local continuation boundary | 5 min |
| `frontend/apps/skriptoteket/src/stores/auth.ts` and `frontend/apps/skriptoteket/src/api/sharedAuth.ts` | Current local role/user id consumers | 8 min |

**Total estimated time:** ~41 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Remediate `PR-0251` through a dedicated `PR-0255` slice | Keeps the original cutover lane focused while making the review blockers explicit | [x] |
| Require HuleEdu request context instead of local session-cookie auth for app continuation | Matches ADR-0076 and ADR-0082 | [x] |
| Move local RBAC off HuleEdu provider roles | Preserves Skriptoteket-local authorization ownership | [x] |
| Freeze the continuation projection as `local_user` plus matching `profile` | Preserves local user id, role, profile identity, and ownership comparisons | [x] |
| Consume concrete `InternalIdentityContextV1` headers and verification rules | Makes the gateway trust boundary implementable and fail-closed | [x] |

## Review Checklist

- [x] Scope is bounded to `REV-PR-0251` remediation
- [x] Non-goals keep login/logout and full local-auth retirement out of this slice
- [x] Tests include positive and negative HuleEdu-only continuation paths
- [x] Gateway context verification contract is concrete enough to implement safely
- [x] App-local projection response shape preserves local `User.id`, role, and profile identity
- [x] Verification plan includes the required live route/UI check

## Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-04-11`
**Verdict:** `approved`

### Required Changes

1. **blocker - local projection response only names role, not local user identity**

   File reference:
   `docs/backlog/prs/pr-0255-st-28-01-pr-0251-remediation-huleedu-context-and-local-authorization-projection.md:105`

   The plan says the continuation response should include the local `user.role` "at minimum". That
   is not enough for behavioral parity. The SPA currently uses `auth.user.id` for app-local behavior
   such as editor current-user ownership, recent editor tools, profile linkage, and user-specific
   UI state. If the HuleEdu session subject remains `auth.user.id` while the backend/tool owner ids
   remain Skriptoteket-local UUIDs, role-aware checks can pass while owner/user comparisons still
   fail.

   Concrete fix: require the continuation response to carry an explicit Skriptoteket-local user
   projection, not just role. At minimum, freeze fields equivalent to local `User.id`, `role`,
   `auth_provider`, `external_id`, `email`, `email_verified`, and the matching `UserProfile.user_id`
   / profile fields needed by the auth store. The frontend should merge shared HuleEdu browser
   session metadata with this local app identity so `auth.user.id` remains the Skriptoteket-local
   user id used by existing app APIs and ownership comparisons.

   Proof requirement: add a frontend test where HuleEdu `user.user_id` differs from the local
   Skriptoteket UUID returned by app continuation; assert `auth.user.id` becomes the local UUID,
   `hasAtLeastRole("contributor")` is true, and shared `grants` / `featureFlags` are still
   preserved. Add a backend test proving the projection resolves an existing local user by
   `(auth_provider=huleedu, external_id=<huleedu-subject>)`.

2. **high - gateway identity verification contract is still underspecified**

   File reference:
   `docs/backlog/prs/pr-0255-st-28-01-pr-0251-remediation-huleedu-context-and-local-authorization-projection.md:89`

   The plan calls for a typed model and resolver for "signed HuleEdu gateway payload", but it does
   not name the payload fields, forwarding headers, trust boundary, issuer/audience checks,
   signature/key selection, or expiry/replay semantics. That leaves the implementer free to invent
   an ad hoc header shape and still appear to satisfy the slice.

   Concrete fix: either link the exact provider conformance artifact that defines the downstream
   gateway identity context, or freeze a local interim contract in this PR before implementation.
   The contract should name the header(s), payload fields (`subject`, `email`, `email_verified`,
   issuer, audience/service, issued/expiry timestamps, key id/signature or equivalent), allowed
   clock skew, and fail-closed behavior. If that contract is not available, keep `PR-0255` blocked
   and record a HuleEdu provider follow-up instead of implementing a guessed verifier.

   Proof requirement: add unit tests for valid context, missing context, invalid signature/key,
   wrong audience/issuer, and expired context. Run
   `pdm run pytest -q tests/unit/web/test_profile_app_continuation_api.py` plus `pdm run typecheck`.

3. **medium - verification plan omits the required live functional check**

   File reference:
   `docs/backlog/prs/pr-0255-st-28-01-pr-0251-remediation-huleedu-context-and-local-authorization-projection.md:153`

   This slice changes an API route and the SPA bootstrap path, so the session rule requires a live
   functional check and handoff evidence. The test plan lists unit/type/lint/docs gates, but no live
   route or browser/bootstrap probe.

   Concrete fix: add a live verification step that starts the local API/SPA as appropriate and
   proves app continuation returns `200` for a valid HuleEdu context without a Skriptoteket session
   cookie, returns `401` without that context, and the SPA bootstraps through HuleEdu session plus
   app continuation with local RBAC hydrated. Record the check in `.agents/handoff.md`.

   Proof requirement: run the live probe after implementation and include the exact command and
   result in `PR-0255`, `REV-PR-0251`, and `.agents/handoff.md`.

### Suggestions (Optional)

- Add a repository protocol method for lookup by `(auth_provider, external_id)` rather than
  searching by email; the database already has `uq_users_auth_provider_external_id`, so the
  protocol should expose that invariant directly.
- Name the continuation response field as `local_user` or `app_user` rather than overloading
  shared-session identity language.

### Decision Approvals

- [x] Dedicated remediation PR
- [x] HuleEdu request-context-derived app continuation
- [x] Local RBAC source moved out of provider roles
- [x] Exact local projection response shape
- [x] Exact gateway identity verification contract

### Verification

- `pdm run docs-validate` (pass on 2026-04-11 after retaining `REV-PR-0255`)
- `pdm run docs-validate` (pass on 2026-04-11 after approving revised `PR-0255`)

### Revision Response (2026-04-11)

`PR-0255` was revised after this review. The revision:

- freezes the local continuation response shape around `local_user`, matching `profile`,
  `ai_policy`, `allow_remote_fallback`, and `inline_completion_provider`
- requires `auth.user.id` in the SPA to come from the Skriptoteket-local `local_user.id`, not the
  HuleEdu shared-session subject
- consumes the concrete HuleEdu `InternalIdentityContextV1` contract from
  `REF-shared-browser-session-consumer-conformance-v1` /
  `REF-internal-identity-context-v1-contract`
- names required `X-Huledu-Identity-*` headers, payload fields, issuer/audience checks, key-id and
  RS256 signature verification, TTL/skew checks, and fail-closed cases
- blocks local user auto-provisioning from `sub` alone because the current signed context does not
  carry email or email-verification claims
- adds the required live route/bootstrap verification expectation

### Retained Re-review (2026-04-11)

**Reviewer:** `lead-developer`
**Verdict:** `approved`

The revised `PR-0255` resolves the retained review concerns:

- `local_user` plus matching `profile` now carries the Skriptoteket-local identity needed by
  existing app APIs, ownership comparisons, profile linkage, and role-aware getters.
- HuleEdu gateway context verification is pinned to concrete `InternalIdentityContextV1` transport
  headers, payload fields, RS256 detached signature validation, issuer/audience checks, key id,
  TTL, clock skew, and fail-closed cases.
- Auto-provisioning is explicitly blocked for this slice because the current signed context lacks
  email and email-verification claims; missing local projections fail closed instead.
- The test plan now includes focused negative/positive verifier cases, local projection lookup
  proof, frontend local-id/RBAC proof, and required live route/bootstrap verification.

#### Required Changes

None. `PR-0255` is approved for implementation.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0255` | Reviewed the proposed remediation response against `REV-PR-0251`, `ADR-0076`, and `ADR-0082` |
| 2 | `PR-0255` | Requested clarification before implementation for local user projection shape, gateway context verification, and live proof |
| 3 | `PR-0255` | Revised remediation plan to freeze local projection shape, gateway verification contract, and live proof expectations |
| 4 | `REV-PR-0255` | Approved the revised remediation plan for implementation |
