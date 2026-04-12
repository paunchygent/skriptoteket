---
type: pr
id: PR-0257
title: "ST-28-08 standalone registration/password lifecycle provider contract"
status: blocked
owners: "agents"
created: 2026-04-12
updated: 2026-04-12
stories:
  - "ST-28-08"
adrs:
  - "ADR-0083"
dependencies:
  - "ST-28-06"
  - "ST-28-07"
  - "PR-0253"
  - "PR-0256"
  - "REV-PR-0256"
  - "HuleEdu standalone lifecycle provider contract"
tags: ["auth", "frontend", "huleedu", "identity"]
acceptance_criteria:
  - "Given `ADR-0083` keeps Skriptoteket standalone identity as a product realm, when HuleEdu publishes the provider contract, then registration, password reset, and email verification are available through browser-navigable Hule Education surfaces that accept `app=skriptoteket`, `product_identity_realm`, an allowed `return_to`, and safe route-level `next` continuation."
  - "Given a new user needs only a Skriptoteket standalone account, when registration completes, then the resulting identity is scoped to `skriptoteket_standalone` and does not require HuleEdu school organization registration."
  - "Given password reset or email verification is initiated from Skriptoteket, when the user follows email/token links, then the flow preserves Skriptoteket product copy, app/realm context, and return behavior without handing the browser to direct Identity Service API endpoints."
  - "Given old `/register`, `/forgot-password`, `/reset-password`, and `/verify-email` links are opened in Skriptoteket, when this PR eventually implements the consumer side, then those links hand off to the provider-approved lifecycle ceremony targets and never post to local `/api/v1/auth/*` browser endpoints."
  - "Given implementation is complete, when verification runs, then focused frontend/router tests, backend contract scans, and a live browser proof confirm safe lifecycle handoff, no local register/reset/verify browser endpoint revival, and realm-aware continuation into app bootstrap."
---

## Problem

`ST-28-08` is the next natural lane after the approved `ST-28-07` login ceremony. It should restore
Skriptoteket standalone account self-service after `PR-0253` retired local browser registration,
verification, and password routes.

The lane is not ready for consumer implementation yet. HuleEdu now retains and proves the login
ceremony, but the same retained browser contract does not yet cover standalone registration,
password reset, or email verification as app/realm-aware product ceremonies.

Current provider evidence:

- HuleEdu `docs/reference/ref-shared-browser-session-consumer-conformance-v1.md` lists
  `GET /auth/login`, login/logout/refresh/session/csrf, and websocket-ticket as browser endpoints;
  it does not define registration, password reset, or email verification ceremonies.
- HuleEdu API Gateway `services/api_gateway_service/routers/auth_routes.py` proxies
  `/v1/auth/login`, `/v1/auth/logout`, `/v1/auth/refresh`, `/v1/auth/session`, `/v1/auth/csrf`,
  and `/v1/auth/websocket-ticket`; it does not expose browser lifecycle handoff routes for
  `/register`, `/forgot-password`, `/reset-password`, or `/verify-email`.
- HuleEdu Identity Service has direct `POST /v1/auth/register`,
  `POST /v1/auth/request-password-reset`, `POST /v1/auth/reset-password`,
  `POST /v1/auth/request-email-verification`, and `POST /v1/auth/verify-email` routes, but those
  are service API surfaces, not retained browser ceremony targets for a Skriptoteket consumer.
- The current HuleEdu `RegisterRequest` requires `organization_name` and has no app, product realm,
  return target, or route continuation field. That does not satisfy standalone
  `skriptoteket_standalone` registration without HuleEdu school registration.
- The reset and verification request schemas lack app, product realm, return target, and route
  continuation fields. The current notification reset link targets a generic HuleEdu reset path,
  not a retained Skriptoteket product-realm return contract.

If Skriptoteket implements only local redirects to those direct API shapes, it will recreate the
same contract hole `PR-0256` avoided: the UI would look restored while the provider could still be
school-registration-centric, route users away from Skriptoteket, or lose realm context before
projection provisioning.

## Goal

Prepare `ST-28-08` as a provider-contract gate and define the exact consumer package to implement
after HuleEdu publishes the missing lifecycle ceremony.

The eventual consumer implementation must:

1. Add safe browser handoff targets for standalone registration, password reset request, reset-token
   completion, email verification request, and verification-token completion.
2. Preserve app/realm/return semantics consistent with `ADR-0083` and `PR-0256`.
3. Keep old Skriptoteket lifecycle URLs deliberate and tested as handoff surfaces.
4. Avoid reviving local browser auth APIs, local password handling, local token verification, local
   CSRF authority, or bearer-browser storage.
5. Prove that standalone lifecycle outcomes either produce sufficient signed claims for
   `ST-28-09` projection provisioning or fail closed into the deliberate local-access flow.

## Non-goals

- Implementing HuleEdu Gateway, Identity Service, or frontend lifecycle ceremony routes in this
  repository.
- Calling HuleEdu Identity Service directly from the Skriptoteket browser.
- Reintroducing local `/api/v1/auth/register`, `/api/v1/auth/request-password-reset`,
  `/api/v1/auth/reset-password`, `/api/v1/auth/request-email-verification`, or
  `/api/v1/auth/verify-email` browser endpoints.
- Creating realm-aware projection storage or provisioning. That belongs to `ST-28-09`.
- Running the final cross-app Docker/operator smoke. That belongs to `ST-28-04` / `PR-0254`.

## Required Provider Contract

HuleEdu must publish and prove a retained browser contract before this PR can move from blocked to
implementation.

Required minimum:

| Concern | Required Contract |
|---------|-------------------|
| Registration entry | Browser-navigable HuleEdu route for `app=skriptoteket` standalone registration |
| Password reset entry | Browser-navigable route for reset request plus reset-token completion |
| Email verification entry | Browser-navigable route for verification request plus verification-token completion |
| App input | `app=skriptoteket` or equivalent signed/app-registered parameter |
| Realm input | selected/defaulted `product_identity_realm`, including `skriptoteket_standalone` |
| Return target | absolute allowlisted Skriptoteket callback/return URL plus safe route-level `next` |
| Product copy | user-facing copy clearly says Skriptoteket account/access, not HuleEdu school enrollment |
| Standalone semantics | standalone registration does not require `organization_name`, `org_id`, or HuleEdu school membership |
| Token links | email/reset links preserve or recover app, realm, and return context |
| Session output | successful lifecycle completion can establish the shared browser session or return to login with preserved app/realm context |
| Downstream context | successful login after lifecycle completion signs active app, active product identity realm, and realm subject fields |
| Abuse controls | registration/reset/verification have provider-owned rate limits and token replay/expiry semantics |

## Implementation Plan

This PR stays blocked until the provider contract exists. Once HuleEdu closes the blocker:

1. Replace old Skriptoteket lifecycle links with provider-approved browser ceremony URLs.
2. Add or restore top-level Skriptoteket compatibility routes only as transition/handoff surfaces.
3. Share the safe route-level `next` sanitizer used by the login ceremony helper.
4. Add focused Vitest coverage for register/reset/verify handoff URLs, hostile `next`, token-link
   continuation, and no local form/API revival.
5. Add backend route/OpenAPI contract scans proving local register/reset/verify browser endpoints
   remain absent.
6. Add a live browser proof that exercises at least one lifecycle path through the provider-approved
   ceremony and returns to Skriptoteket with the expected app/realm continuation.
7. Update `ST-28-09` only after lifecycle outputs provide sufficient signed claims for projection
   provisioning.

## Test Plan

Provider contract review while blocked:

- `pdm run docs-validate`
- `git diff --check`

Implementation close-out after provider clearance:

- focused frontend lifecycle handoff specs
- focused backend retired-local-auth contract scans
- `pdm run fe-type-check`
- `pdm run typecheck`
- `pdm run fe-lint`
- `pdm run lint`
- live browser lifecycle proof against the approved HuleEdu ceremony
- `pdm run docs-validate`
- `git diff --check`

## Rollback Plan

If HuleEdu publishes a different lifecycle shape, keep `ST-28-08` blocked and update this PR plus
`REV-PR-0257` with the new provider decision before implementing any Skriptoteket redirects.
