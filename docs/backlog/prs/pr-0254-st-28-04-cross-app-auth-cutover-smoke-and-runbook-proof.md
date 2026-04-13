---
type: pr
id: PR-0254
title: "ST-28-04 cross-app auth cutover smoke and runbook proof"
status: done
owners: "agents"
created: 2026-04-10
updated: 2026-04-13
stories:
  - "ST-28-04"
adrs:
  - "ADR-0083"
dependencies:
  - "REV-PR-0253"
  - "PR-0253"
  - "ST-28-06"
  - "ST-28-07"
  - "ST-28-08"
  - "ST-28-09"
  - "HuleEdu TASK-0325"
  - "HuleEdu TASK-0326"
  - "HuleEdu TASK-0327"
  - "PR-0260"
  - "PR-0261"
  - "PR-0262"
  - "REV-PR-0260"
  - "REV-PR-0261"
  - "REV-PR-0262"
tags: ["auth", "playwright", "runbook", "smoke"]
acceptance_criteria:
  - "Given the prerequisite provider and consumer proof lanes are complete, when `pdm run pr-0254-auth-cutover` starts, then it first validates retained artifacts for HuleEdu `TASK-0326`, HuleEdu `TASK-0327`, Skriptoteket `PR-0261`, and Skriptoteket `PR-0262` before opening a browser."
  - "Given `ADR-0083` and the realm-aware login/projection stories are complete, when the retained smoke runs against the target environment, then a browser can authenticate through the Hule Education `app=skriptoteket` ceremony and open Skriptoteket from the returned shared session."
  - "Given Skriptoteket standalone identity is supported, when the smoke uses that realm, then protected Skriptoteket reads and writes succeed through gateway-signed context and local RBAC without HuleEdu school registration."
  - "Given HuleEdu school identity is supported for Skriptoteket, when the smoke uses that realm, then the proof distinguishes school identity, Skriptoteket projection, and local authorization."
  - "Given HuleEdu bootstrap identities and the Skriptoteket role matrix are accepted, when the smoke runs by role, then required local roles authenticate through shared-session context and resolve local `User.role` without local password ownership."
  - "Given the real standalone lifecycle proof is accepted, when final proof is reviewed, then create account, verify email, login, forgot-password, reset, callback continuation, projection, and local RBAC are covered by sanitized retained evidence."
  - "Given a user clicks login, create account, forgot password, verification, or reset links, when final proof observes the first interactive page, then it is the requested action page with no generic HuleEdu stopover except documented fallback recovery."
  - "Given the local proof runs against loopback origins, when the smoke starts, then it uses the HuleEdu `TASK-0325` local/non-production Gateway lane with HuleEdu login UI on `5174`, exact local return origins, Gateway-proxied protected APIs, and local-only Gateway public-key verification."
  - "Given protected browser `/api` traffic is in scope, when the smoke reads app continuation or writes profile AI settings, then it proves those calls travel through the HuleEdu Gateway proxy rather than a direct backend shortcut."
  - "Given CSRF is owned by HuleEdu, when the smoke performs the low-blast-radius profile AI settings write, then the same unsafe write without CSRF is rejected before or at Gateway and succeeds only after fetching shared CSRF."
  - "Given logout is session-authority behavior, when the user logs out from either app, then both Skriptoteket and HuleEdu become unauthenticated after refresh without recreating local Skriptoteket browser sessions."
  - "Given operators need repeatable proof, when this PR completes, then the retained artifact is `manifest.redacted.json` with sanitized route/assertion summaries, no raw URLs, no `body_prefix`, no cookies, no CSRF token, no signed headers, no signature/JWT material, no raw subject, and no raw email."
---

## Problem

Unit and component tests cannot prove the cross-app browser contract. The cutover needs one retained
smoke and operator runbook proof that spans Skriptoteket and HuleEdu.

After the remediated `PR-0258` realm-aware projection implementation, this PR is the next proof
lane. It must not certify a HuleEdu-school-only login as final Skriptoteket login, and it must
exercise the runtime correlation, projection, and local RBAC behavior that `PR-0258` now provides.

The local proof must consume HuleEdu `TASK-0325`, validate retained artifacts from HuleEdu
`TASK-0326` and `TASK-0327`, and validate retained Skriptoteket artifacts from `PR-0261` and
`PR-0262` before running the live browser smoke. `PR-0260` is consumed through the role/projection
evidence already retained in `PR-0262`. Public production rejecting
`return_to=http://localhost:5173/...` is correct fail-closed behavior; `PR-0254` should not weaken
public allowlists, replace Gateway with a local identity-header shortcut, or bulk import fake
alpha users as a substitute for proof accounts.

## Goal

Add the final Playwright and runbook proof lane for the shared browser-session cutover, including
the Skriptoteket product identity realm behavior defined by `ADR-0083`.

## Non-goals

- Implementing earlier bootstrap, handoff, or deletion work.
- Certifying the superseded modal-first auth-entry surface.
- Implementing the Hule Education-hosted Skriptoteket login ceremony.
- Implementing standalone registration/password lifecycle.
- Implementing realm-aware projection provisioning.
- Implementing the HuleEdu-owned local shared-auth Gateway lane; that belongs to HuleEdu
  `TASK-0325`.
- Creating HuleEdu bootstrap identities; that belongs to HuleEdu `TASK-0326`.
- Implementing Skriptoteket proof role bootstrap; that belongs to `PR-0260`.
- Implementing auth-entry UI/lifecycle proof; that belongs to `PR-0261` and `PR-0262`.
- Bulk importing old alpha education-domain users.
- Treating the smoke as a replacement for focused tests in `PR-0251` through `PR-0253`.

## Implementation Plan

1. Treat `PR-0254` as the final cross-process certification for this chain:
   `Skriptoteket SPA -> HuleEdu Gateway auth entry -> HuleEdu login UI/session ->`
   `Gateway-proxied /api request -> Gateway-signed InternalIdentityContextV1 ->`
   `Skriptoteket app-continuation -> local identity_projection -> local User.role/RBAC ->`
   `CSRF-protected write -> shared logout invalidation`.
2. Add an artifact preflight before browser launch. Validate the retained artifacts are present,
   `status=ok`, aligned on `app=skriptoteket` and
   `product_identity_realm=skriptoteket_standalone`, and safe to summarize without retaining raw
   subject, email, token, cookie, CSRF, signed-header, JWT, or signature material:
   - HuleEdu `TASK-0326` subject export proof
   - HuleEdu `TASK-0327` lifecycle proof
   - Skriptoteket `PR-0261` direct-action/probe manifest
   - Skriptoteket `PR-0262` lifecycle/projection/role manifest
3. Consume accepted `ADR-0083`, the completed `ST-28-07` through remediated `ST-28-09`
   login/projection contracts, HuleEdu `TASK-0325` local shared-auth Gateway semantics,
   HuleEdu `TASK-0326` proof identity subject export, HuleEdu `TASK-0327` real lifecycle proof,
   and Skriptoteket `PR-0261`/`PR-0262` retained evidence.
4. Configure local proof so Skriptoteket uses:
   - `VITE_HULEEDU_AUTH_BASE_URL=http://localhost:8080`
   - `VITE_HULEEDU_AUTH_ENTRY_URL=http://localhost:8080/auth/login`
   - host-run Vite: `VITE_DEV_PROXY_TARGET=http://localhost:8080`
   - normal Docker frontend service: `VITE_DEV_PROXY_TARGET=http://huleedu_api_gateway_service:8080`
     on `hule-network`, so existing Vite `/api` proxy traffic enters the HuleEdu Gateway
     local-only `ANY /api/{path:path}` proxy
   - normal Docker frontend service:
     `VITE_DEV_BACKEND_PROXY_TARGET=http://skriptoteket_web:8000`, so public
     `/api/v1/public/...` and backend static assets remain directly served by Skriptoteket
     without a HuleEdu browser session
   - 127 proof equivalents:
     `VITE_HULEEDU_AUTH_BASE_URL=http://127.0.0.1:8080`,
     `VITE_HULEEDU_AUTH_ENTRY_URL=http://127.0.0.1:8080/auth/login`, and
     `VITE_DEV_PROXY_TARGET=http://127.0.0.1:8080`
   - HuleEdu provider config from `TASK-0325`:
     `API_GATEWAY_SKRIPTOTEKET_PROXY_ENABLED=true`,
     `API_GATEWAY_SKRIPTOTEKET_PROXY_PREFIX=/api`, and
     `API_GATEWAY_SKRIPTOTEKET_BACKEND_URL=http://skriptoteket-web:8000`
   - a local-only Gateway public signing key mounted or exported for backend verification
5. Update the existing Skriptoteket realm-aware auth-cutover Playwright smoke:
   `pdm run pr-0254-auth-cutover`.
6. Prove public Klassrumskartan remains public before login: public bootstrap returns `200` and no
   auth/session error appears.
7. Prove auth entry is browser-navigable and points to Gateway `/auth/login`, never
   `/v1/auth/login`, with `app=skriptoteket`,
   `product_identity_realm=skriptoteket_standalone`, allowed `return_to`, and safe `next`.
8. Prove HuleEdu login/session is the browser authority: the browser lands on HuleEdu login UI
   `:5174`, submits controlled proof credentials, receives HuleEdu-owned session/CSRF state, and
   does not create a local Skriptoteket browser session cookie.
9. Prove callback resumes the intended protected route, using `/editor` so the proof observes local
   contributor authorization rather than only authentication.
10. Prove protected `/api/v1/profile/app-continuation` and `/api/v1/profile/ai-settings` travel
   through Gateway `/api`, with retained evidence limited to route names, statuses, and sanitized
   accepted-context summaries.
11. Prove local projection and RBAC are observed: app-continuation returns a local user, the local
   role matches the `PR-0260` role matrix as retained by `PR-0262`, provider roles/grants remain
   metadata, and contributor access opens `/editor`. Admin/superuser coverage is either explicit
   in the same smoke or recorded as a matrix extension/blocker.
12. Prove CSRF-protected write semantics through Gateway with a safe profile AI-settings update:
   missing CSRF is rejected before or at Gateway, then shared CSRF is fetched and the write
   succeeds. Retain only status summaries and route names.
13. Prove shared logout invalidation: logout from Skriptoteket, refresh the protected route, confirm
   signed-out/auth-entry behavior, confirm HuleEdu `/v1/auth/session` is unauthenticated, and
   confirm no old Skriptoteket local session revives the user.
14. Prove both the canonical `localhost` lane and the separate `127.0.0.1` lane, because browser
   cookies and origins are host-scoped and close-out requires both loopback lanes green.
15. Write `manifest.redacted.json` instead of `proof.json`; do not retain `body_prefix` or raw
   observed URLs.
16. Update the operator runbook with exact commands, required hosts, expected artifacts, identity
   realm coverage, metrics/logs to inspect, and failure triage.
17. Record the HuleEdu teacher smoke evidence that pairs with the Skriptoteket proof.

## Test Plan

- Run `pdm run pr-0254-auth-cutover` against the intended local or Hemma target.
- Plain `pdm run pr-0254-auth-cutover` must prefer the controlled Skriptoteket lifecycle proof
  credentials from the HuleEdu dotenv before falling back to bootstrap superuser credentials, so the
  retained `/editor` continuation proves contributor RBAC instead of stopping on a local `user`
  role.
- Run the local smoke through the HuleEdu `TASK-0325` Gateway lane, not through public
  `https://api.hule.education` with loopback `return_to`.
- Verify HuleEdu `TASK-0326`, HuleEdu `TASK-0327`, Skriptoteket `PR-0261`, and Skriptoteket
  `PR-0262` retained artifacts are accepted before final proof.
- Inspect `manifest.redacted.json` and confirm the final artifact contains sanitized
  route/assertion summaries only.
- Run focused auth tests affected by the smoke helper changes.
- Run `pdm run docs-validate`.
- Run `pdm run pr-0254-auth-cutover --include-127-lane --require-127-lane` and verify both loopback
  lane summaries are retained as `status=ok`.

## Dependency State (2026-04-13)

- HuleEdu `TASK-0326` is done and deployed at merge commit `92419293`; production
  bootstrap/export proof verified the three approved proof accounts on Hemma.
- Skriptoteket `PR-0260` is done and created the local projection/role matrix
  consumed by the lifecycle proof chain.
- HuleEdu `TASK-0327` is done after the final live apply against the
  Skriptoteket `PR-0261` diagnostics route.
- Skriptoteket `PR-0261` and `PR-0262` are done. The retained PR-0262 manifest
  is
  `.artifacts/playwright-pr-0262-real-lifecycle/local-nonprod/20260413T132801Z/manifest.redacted.json`.
- `PR-0254` is now the final live cutover proof. It should consume the retained
  upstream artifacts above and make the live browser smoke prove only the
  still-unproven cross-process runtime path: public route, auth entry, HuleEdu
  login/session, Gateway-proxied protected read/write, app continuation, local
  role/RBAC, CSRF, and logout invalidation.

## Retained Manifest Contract

The final retained artifact is:

```text
.artifacts/playwright-pr-0254-auth-cutover/<environment>/<run-id>/manifest.redacted.json
```

Required top-level sections:

- `status`
- `environment`
- `app`
- `product_identity_realm`
- `validated_prerequisite_artifacts`
- `public_route_assertions`
- `auth_entry_assertions`
- `gateway_proxy_assertions`
- `callback_assertions`
- `projection_assertions`
- `local_role_assertions`
- `csrf_write_assertions`
- `logout_assertions`
- `redaction_checks`

Forbidden retained evidence:

- raw signed headers or signed context payloads
- JWTs, signatures, reset tokens, verification tokens, cookies, or CSRF tokens
- raw subject identifiers or raw email addresses
- `body_prefix`
- raw observed URLs that could carry sensitive query values

## Implementation Summary (as of 2026-04-13)

`PR-0254` is complete on both required local loopback lanes. The final proof command validates the
retained HuleEdu `TASK-0326` subject export, HuleEdu `TASK-0327` lifecycle artifact,
Skriptoteket `PR-0261` action/probe manifest, and Skriptoteket `PR-0262`
lifecycle/projection/role manifest before opening the browser. The live smoke then proves public
Klassrumskartan remains public, auth entry targets the Gateway browser route, HuleEdu owns login
session and CSRF, callback continuation resumes `/editor`, protected app-continuation and AI
settings writes travel through the Gateway-proxied `/api` path, local projection/RBAC resolves the
expected contributor role, missing CSRF is rejected, fetched shared CSRF allows the write, and
Skriptoteket logout invalidates the shared HuleEdu session. `PR-0263` closed the follow-up
loopback-origin parity gap so the 127 lane now proves the same contract instead of being recorded as
blocked.

The retained canonical artifact is:

```text
.artifacts/playwright-pr-0254-auth-cutover/local-nonprod/20260413T160856Z/manifest.redacted.json
```

The successful closeout command was:

```text
pdm run pr-0254-auth-cutover --include-127-lane --require-127-lane
```

The retained manifest records both `localhost` and `127` lane summaries as `status=ok`; public
bootstrap is `200`, callback final path is `/editor`, missing-CSRF write is `403`, CSRF-protected
write is `200`, logout session status is `200`, and all redaction checks pass.

## Rollback Plan

Revert the smoke/runbook additions if they encode an incorrect contract, then keep `ST-28-04`
open until the cross-app proof path is corrected.
