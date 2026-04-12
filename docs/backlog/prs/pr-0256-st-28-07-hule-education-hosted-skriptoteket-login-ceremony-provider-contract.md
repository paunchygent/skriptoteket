---
type: pr
id: PR-0256
title: "ST-28-07 Hule Education-hosted Skriptoteket login ceremony provider contract"
status: done
owners: "agents"
created: 2026-04-12
updated: 2026-04-12
stories:
  - "ST-28-07"
adrs:
  - "ADR-0083"
dependencies:
  - "ST-28-06"
  - "REV-ST-28-06"
  - "PR-0253"
  - "HuleEdu TASK-0313"
  - "HuleEdu TASK-0314"
  - "HuleEdu REV-TASK-0313-01"
tags: ["auth", "frontend", "huleedu"]
acceptance_criteria:
  - "Given `ADR-0083` is accepted and HuleEdu provider proof is approved, when this PR is complete, then Skriptoteket links to a browser-navigable HuleEdu `GET /auth/login` ceremony URL that accepts `app=skriptoteket`, an allowed return target, and an explicit/defaulted product identity realm without using POST-only `/v1/auth/login` as an anchor target."
  - "Given HuleEdu `TASK-0313` / `TASK-0314` publish the ceremony contract, when the SPA builds the login href, then it sends `return_to` to `/auth/callback` and preserves only a safe route-level `next` path."
  - "Given the ceremony completes for `skriptoteket_standalone` or `huleedu_school`, when the browser returns to Skriptoteket, then gateway-signed downstream context includes active app, active product identity realm, and realm subject fields required by `ADR-0083`."
  - "Given Skriptoteket keeps `/auth/login?next=...` as an interruption route, when the user reaches it signed out, then it behaves as a transition or handoff surface, preserves only safe Skriptoteket return targets, and never collects local credentials."
  - "Given implementation is complete, when verification runs, then focused Vitest coverage and a live Playwright proof confirm the ceremony URL shape, no local form, safe `next` handling, no `/v1/auth/login` anchor, and returned realm-aware app bootstrap behavior."
---

## Problem

`ST-28-07` is the next lane after accepted `ADR-0083`. It began as a provider-contract gate because
Skriptoteket could not safely implement the ceremony until HuleEdu exposed a retained
browser-navigable product-realm ceremony and realm-aware downstream context.

Initial blocker evidence:

- HuleEdu API Gateway exposes `POST /v1/auth/login` as the login endpoint in
  `services/api_gateway_service/routers/auth_routes.py`.
- HuleEdu's retained consumer conformance reference lists `POST /v1/auth/login`, `POST
  /v1/auth/logout`, `POST /v1/auth/refresh`, `GET /v1/auth/session`, `GET /v1/auth/csrf`, and
  `GET /v1/auth/websocket-ticket`; it does not define a browser-navigable product-realm ceremony
  URL.
- The current `InternalIdentityContextV1` contract carries `sub`, session, org/tenant, roles,
  grants, and optional `source_app`, but not the `active_product_identity_realm` and
  `realm_subject_id` fields frozen by `ADR-0083`.
- Skriptoteket currently defaults `VITE_HULEEDU_AUTH_ENTRY_URL` to
  `https://api.hule.education/auth/login`, which is intentionally separate from `/v1/auth/login`,
  but it is not backed by a retained HuleEdu provider contract yet.

If this PR implemented only a local link or query-string tweak, it could make `ST-28-07` appear
complete while still pointing users at a non-existent or wrong Hule Education ceremony and while
`PR-0254` later certifies a HuleEdu-school-only path.

Provider clearance on 2026-04-12:

- HuleEdu `TASK-0313` implemented and mapped the product-realm ceremony and signed context.
- HuleEdu `TASK-0314` captured public Hemma proof for `GET /auth/login?app=skriptoteket`, default
  `product_identity_realm=skriptoteket_standalone`, explicit `huleedu_school`, allowed return
  targets, hostile return rejection, and session realm context.
- HuleEdu retained review `REV-TASK-0313-01` is approved.

## Goal

Implement the Skriptoteket consumer side of the provider-cleared `ST-28-07` contract.

The completed consumer changes:

1. Update the SPA ceremony helper so the login URL matches the retained HuleEdu browser ceremony
   contract.
2. Preserve safe `next` return handling from `/auth/login?next=...`.
3. Ensure `/auth/login` behaves as a transition/handoff surface rather than a second login page.
4. Keep old local browser-auth endpoints retired.
5. Add focused tests and a live proof for the ceremony handoff.
6. Accept additive realm-aware `InternalIdentityContextV1` fields so the current signed context
   contract does not fail before `ST-28-09` makes projection lookup realm-aware.

## Non-goals

- Implementing HuleEdu Gateway or Identity routes inside this repository.
- Reintroducing a Skriptoteket-local password form, local browser session, local CSRF authority, or
  bearer-token bridge.
- Implementing standalone registration/password lifecycle. That belongs to `ST-28-08`.
- Implementing realm-aware projection storage and provisioning. That belongs to `ST-28-09`.
- Running the final cross-app smoke. That belongs to `ST-28-04` / `PR-0254` after this lane and
  the projection lane are complete.

## Required Provider Contract

HuleEdu has published and publicly proved the retained contract for the browser-navigable
Skriptoteket ceremony.

Required minimum:

| Concern | Required Contract |
|---------|-------------------|
| Ceremony URL | Browser-navigable HuleEdu `GET /auth/login`, distinct from POST-only `/v1/auth/login` |
| App input | `app=skriptoteket` or an equivalent signed/app-registered parameter |
| Realm input | selected/defaulted product identity realm, at least `skriptoteket_standalone` and `huleedu_school` |
| Return target | absolute allowlisted Skriptoteket callback URL plus preserved route-level `next` |
| Account linking | explicit behavior when a browser session has multiple realms available |
| Session output | shared `huleedu_session` / `huleedu_csrf` browser session contract still applies |
| Downstream context | signed context includes active app, active product identity realm, and realm subject |
| Standalone semantics | `skriptoteket_standalone` login does not require HuleEdu school registration |

## Implementation Summary

Implemented on 2026-04-12:

1. Updated `frontend/apps/skriptoteket/src/api/sharedAuth.ts` so `sharedAuthCeremonyUrl()` encodes
   the provider-approved app, realm, and safe return parameters.
2. Added `/auth/callback` as the HuleEdu return route while keeping `/auth/login` as the signed-out
   transition surface with no local credential form.
3. Kept `frontend/apps/skriptoteket/src/composables/auth/authEntryNavigation.ts` as the owner of
   safe same-origin `next` sanitation and auth-entry loop prevention.
4. Updated Vitest coverage in:
   - `frontend/apps/skriptoteket/src/api/sharedAuth.spec.ts`
   - `frontend/apps/skriptoteket/src/components/auth/AuthLoginPanel.spec.ts`
   - `frontend/apps/skriptoteket/src/views/AuthLoginView.spec.ts`
   - `frontend/apps/skriptoteket/src/composables/auth/authEntryNavigation.spec.ts`
   - `frontend/apps/skriptoteket/src/router/index.spec.ts`
5. Added `scripts/playwright_pr_0256_auth_ceremony.py` so `/auth/login` renders no form, points at
   the provider-approved browser ceremony, preserves safe `next`, and `/auth/callback` resumes a
   protected route after a fixture-backed realm-aware return.
6. Updated `src/skriptoteket/domain/identity/internal_identity_context.py` to accept additive
   realm-aware fields and optional standalone org/tenant context without moving projection lookup
   ahead of `ST-28-09`.
7. Resolved retained review findings by returning normal auth-success destinations as route strings
   so query/hash survive Vue Router normalization, sanitizing unsafe `next` values inside the
   exported ceremony helper, and requiring `active_app=skriptoteket`, supported realm, and
   `realm_subject_id` before app continuation projection lookup.
8. Updated `.agents/handoff.md` with the live check result because this PR changes auth UI/route
   behavior.

## Test Plan

- `pdm run fe-test -- --run src/api/sharedAuth.spec.ts src/components/auth/AuthLoginPanel.spec.ts src/views/AuthLoginView.spec.ts src/composables/auth/authEntryNavigation.spec.ts src/router/index.spec.ts` (`40` tests after review fixes)
- `pdm run test tests/unit/web/test_profile_app_continuation_api.py` (`31` tests after review fixes)
- `pdm run fe-type-check`
- `pdm run typecheck`
- `pdm run fe-lint`
- `pdm run python -m scripts.playwright_pr_0256_auth_ceremony --start-backend --start-vite`
- `pdm run docs-validate`
- `git diff --check`

## Rollback Plan

If the provider contract changes, revert the local ceremony URL and transition changes, reopen
`ST-28-07`, and update this PR plus its retained review with the new provider decision.
