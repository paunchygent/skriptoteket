---
type: review
id: REV-PR-0257
title: "Review: PR-0257 standalone registration/password lifecycle provider contract"
status: approved
owners: "agents"
created: 2026-04-12
updated: 2026-04-12
reviewer: "Codex ruthless-code-review"
prs:
  - PR-0257
adrs:
  - ADR-0083
links:
  - EPIC-28
  - ST-28-08
  - ST-28-09
  - PR-0253
  - PR-0256
  - REV-PR-0256
  - REF-hule-education-product-identity-realms-and-skriptoteket-standalone-identity
---

## TL;DR

`PR-0257` is approved to enter consumer implementation. HuleEdu `TASK-0318` has published and
publicly proved the retained, browser-navigable, app/realm-aware provider contract for Skriptoteket
standalone registration, password reset, and email verification.

## Problem Statement

`PR-0253` retired Skriptoteket-local browser lifecycle routes, and `ADR-0083` says the product
meaning still exists under `skriptoteket_standalone`. The review question is whether `ST-28-08` can
be implemented on the current HuleEdu provider surface without reviving local browser auth or
collapsing standalone Skriptoteket identity into HuleEdu school registration.

It can now proceed. The retained HuleEdu contract proves login/session ceremony behavior and the
registration/reset/verification lifecycle required by this story.

## Proposed Solution

Implement consumer redirects against the HuleEdu provider contract. HuleEdu `TASK-0318` has
published a retained contract and proof for:

- standalone registration under `app=skriptoteket` and `product_identity_realm=skriptoteket_standalone`
- password reset request and token completion with app/realm/return context
- email verification request and token completion with app/realm/return context
- user-facing copy and data requirements that do not require HuleEdu school enrollment
- signed context/session behavior after lifecycle completion

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0257-st-28-08-standalone-registration-password-lifecycle-provider-contract.md` | New ST-28-08 provider-gate PR package | 15 min |
| `docs/backlog/stories/story-28-08-skriptoteket-standalone-registration-and-password-lifecycle.md` | Story acceptance and blocked status | 8 min |
| `docs/adr/adr-0083-hule-education-product-identity-realms-for-skriptoteket-login.md` | Standalone realm and lifecycle ownership contract | 10 min |
| `docs/backlog/prs/pr-0256-st-28-07-hule-education-hosted-skriptoteket-login-ceremony-provider-contract.md` | Approved login ceremony precedent | 8 min |
| HuleEdu `docs/reference/ref-shared-browser-session-consumer-conformance-v1.md` | Retained provider endpoint list and missing lifecycle ceremony | 8 min |
| HuleEdu `services/api_gateway_service/routers/auth_routes.py` | Gateway browser auth proxy route list | 5 min |
| HuleEdu `services/api_gateway_service/routers/auth_ceremony_routes.py` | Existing login-only browser ceremony | 5 min |
| HuleEdu `services/identity_service/api/schemas.py` | Direct lifecycle API schemas and missing app/realm/return fields | 8 min |

**Total estimated time:** ~67 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Create `PR-0257` as the next `ST-28-08` package | Gives standalone lifecycle work a reviewable owner | [x] |
| Keep the PR blocked until HuleEdu publishes lifecycle ceremonies | Prevents implementing against direct Identity Service APIs | [x] |
| Require app/realm/return semantics for all lifecycle paths | Preserves `ADR-0083` and the `PR-0256` ceremony contract | [x] |
| Reject local browser auth endpoint revival | Preserves `PR-0253` hard-retirement | [x] |
| Defer projection provisioning until lifecycle outputs are sufficient | Keeps `ST-28-09` as the projection owner | [x] |

## Review Checklist

- [x] Scope is bounded to `ST-28-08`
- [x] Provider gap is concrete and evidenced
- [x] PR does not implement provider routes inside Skriptoteket
- [x] PR does not reintroduce local register/reset/verify endpoints
- [x] PR preserves `skriptoteket_standalone` as distinct from HuleEdu school enrollment
- [x] PR keeps projection provisioning in `ST-28-09`
- [x] Verification plan includes docs validation while blocked and live browser proof after provider clearance

## Review Feedback

**Reviewer:** `Codex ruthless-code-review`
**Date:** `2026-04-12`
**Verdict:** `approved`

### Required Changes

1. **provider blocker - publish retained browser lifecycle ceremonies**

   File references:
   HuleEdu `docs/reference/ref-shared-browser-session-consumer-conformance-v1.md`,
   `services/api_gateway_service/routers/auth_routes.py`, and
   `services/api_gateway_service/routers/auth_ceremony_routes.py`.

   The retained provider contract currently covers the login ceremony and shared browser session
   endpoints only. It does not define browser-navigable registration, password reset, or email
   verification ceremonies that accept `app`, `product_identity_realm`, `return_to`, and safe
   route continuation.

   Required resolution: HuleEdu must add a retained contract and proof for the lifecycle ceremony
   family before Skriptoteket implements consumer redirects.

2. **provider blocker - direct Identity Service lifecycle APIs are not enough**

   File references:
   HuleEdu `services/identity_service/api/registration_routes.py`,
   `services/identity_service/api/password_routes.py`,
   `services/identity_service/api/verification_routes.py`, and
   `services/identity_service/api/schemas.py`.

   Direct `POST /v1/auth/register`, request-password-reset, reset-password, request-email-
   verification, and verify-email routes exist in Identity Service, but the browser consumer is
   required to use the Gateway-owned shared identity surface. Those APIs also lack the app/realm
   and return-target fields needed by the Skriptoteket standalone lifecycle.

   Required resolution: expose product-aware browser ceremony or Gateway surfaces, not direct
   Identity Service calls from the Skriptoteket browser.

3. **provider blocker - standalone registration still looks school-registration-shaped**

   File reference:
   HuleEdu `services/identity_service/api/schemas.py`.

   The current registration request requires `organization_name` and has no `app`,
   `product_identity_realm`, `return_to`, or `next` field. That is incompatible with
   `ADR-0083`'s requirement that `skriptoteket_standalone` registration not require HuleEdu school
   enrollment.

   Required resolution: HuleEdu must define how standalone Skriptoteket accounts are created,
   verified, and later signed into the shared browser session without requiring a school org.

4. **provider blocker - token links do not carry Skriptoteket product context**

   File references:
   HuleEdu `services/identity_service/notification_orchestrator.py` and
   `services/identity_service/api/schemas.py`.

   Password reset and email verification token flows currently do not have a retained guarantee
   that app, realm, product copy, or Skriptoteket return behavior survives the email-link hop.

   Required resolution: HuleEdu must publish token-link behavior that preserves or safely
   reconstructs `app=skriptoteket`, `product_identity_realm=skriptoteket_standalone`, and an
   allowlisted Skriptoteket return target.

### Resolution Update (2026-04-12)

HuleEdu `TASK-0318` closed the provider blocker at commit `cff626aa`:

- Gateway-owned browser lifecycle entries are now retained for `GET /auth/register`,
  `GET /auth/password-reset`, and `GET /auth/email-verification`.
- The routes accept `app`, `product_identity_realm`, `return_to`, safe route-level `next`, and
  token continuation for reset/verification completion.
- Standalone Skriptoteket registration is explicitly no-org and no school-membership.
- Reset and verification notification links preserve app/realm/return/next context through
  `https://api.hule.education/auth/password-reset` and
  `https://api.hule.education/auth/email-verification`.
- Public lifecycle proof against `https://api.hule.education` returned `status=ok` for
  `app=skriptoteket` and `product_identity_realm=skriptoteket_standalone`, with rejected
  untrusted return-origin checks.

### Suggestions (Optional)

- Model lifecycle entries as the same ceremony family as `GET /auth/login`, for example
  provider-owned browser routes that validate app, realm, return origin, and `next` before
  redirecting to HuleEdu frontend pages.
- Keep reset and verification completion routes token-aware but not Identity-Service-direct in the
  browser.
- Include a public Hemma proof similar to HuleEdu `TASK-0314` once the lifecycle contract exists.

### Decision Approvals

- [x] Create `PR-0257` as the next `ST-28-08` package
- [x] Move `PR-0257` into consumer implementation after HuleEdu lifecycle provider proof
- [x] Preserve no-local-browser-auth and no-direct-Identity-Service constraints
- [x] Defer projection provisioning to `ST-28-09`

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-0257` | Added the next ST-28-08 PR package as a provider-contract gate |
| 2 | `REV-PR-0257` | Recorded retained `changes_requested` review findings against missing provider lifecycle contract |
| 3 | `ST-28-08` | Kept blocked and added explicit provider-gate dependencies |
| 4 | `EPIC-28` | Updated sequencing so PR-0257 precedes ST-28-09 and PR-0254 |
| 5 | HuleEdu `TASK-0318` | Closed the provider lifecycle blocker with retained public proof |
| 6 | `PR-0257` | Implemented the Skriptoteket consumer lifecycle handoff surfaces |
