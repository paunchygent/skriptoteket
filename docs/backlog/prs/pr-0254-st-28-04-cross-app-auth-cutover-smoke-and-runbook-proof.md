---
type: pr
id: PR-0254
title: "ST-28-04 cross-app auth cutover smoke and runbook proof"
status: ready
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
  - "Given `ADR-0083` and the realm-aware login/projection stories are complete, when the retained smoke runs against the target environment, then a browser can authenticate through the Hule Education `app=skriptoteket` ceremony and open Skriptoteket from the returned shared session."
  - "Given Skriptoteket standalone identity is supported, when the smoke uses that realm, then protected Skriptoteket reads and writes succeed through gateway-signed context and local RBAC without HuleEdu school registration."
  - "Given HuleEdu school identity is supported for Skriptoteket, when the smoke uses that realm, then the proof distinguishes school identity, Skriptoteket projection, and local authorization."
  - "Given HuleEdu bootstrap identities and the Skriptoteket role matrix are accepted, when the smoke runs by role, then required local roles authenticate through shared-session context and resolve local `User.role` without local password ownership."
  - "Given the real standalone lifecycle proof is accepted, when final proof is reviewed, then create account, verify email, login, forgot-password, reset, callback continuation, projection, and local RBAC are covered by sanitized retained evidence."
  - "Given a user clicks login, create account, forgot password, verification, or reset links, when final proof observes the first interactive page, then it is the requested action page with no generic HuleEdu stopover except documented fallback recovery."
  - "Given the local proof runs against loopback origins, when the smoke starts, then it uses the HuleEdu `TASK-0325` local/non-production Gateway lane with HuleEdu login UI on `5174`, exact local return origins, Gateway-proxied protected APIs, and local-only Gateway public-key verification."
  - "Given logout is session-authority behavior, when the user logs out from either app, then both Skriptoteket and HuleEdu become unauthenticated after refresh without recreating local Skriptoteket browser sessions."
  - "Given operators need repeatable proof, when this PR completes, then the runbook records commands, environment assumptions, artifacts, identity realm coverage, failure interpretation, and links to the HuleEdu teacher-dashboard smoke evidence."
---

## Problem

Unit and component tests cannot prove the cross-app browser contract. The cutover needs one retained
smoke and operator runbook proof that spans Skriptoteket and HuleEdu.

After the remediated `PR-0258` realm-aware projection implementation, this PR is the next proof
lane. It must not certify a HuleEdu-school-only login as final Skriptoteket login, and it must
exercise the runtime correlation, projection, and local RBAC behavior that `PR-0258` now provides.

The local proof must first consume HuleEdu `TASK-0325`, `TASK-0326`, and `TASK-0327`, plus
Skriptoteket `PR-0260` through `PR-0262`. Public production rejecting
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

1. Consume accepted `ADR-0083`, the completed `ST-28-07` through remediated `ST-28-09`
   login/projection contracts, HuleEdu `TASK-0325` local shared-auth Gateway semantics,
   HuleEdu `TASK-0326` proof identity subject export, HuleEdu `TASK-0327` real lifecycle proof,
   and Skriptoteket `PR-0260` through `PR-0262`.
2. Configure local proof so Skriptoteket uses:
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
3. Add or update the dedicated Skriptoteket realm-aware auth-cutover Playwright smoke:
   `pdm run pr-0254-auth-cutover`.
4. Prove browser ceremony entry, protected-route recovery, signed downstream context, projection
   resolution, CSRF write, websocket/session admission if applicable, and logout invalidation.
5. Prove both the canonical `localhost` lane and the separate `127.0.0.1` lane where feasible,
   because browser cookies and origins are host-scoped.
6. Cover the proof role matrix from `PR-0260` and verify local `User.role` behavior for the
   required roles.
7. Cover Skriptoteket standalone identity and HuleEdu school identity according to the implemented
   realm matrix; explicitly record any unsupported realm as blocked rather than silently passing.
8. Confirm the real-account lifecycle artifacts from `PR-0262` are present and sanitized before
   declaring the final smoke complete.
9. Confirm direct-action landing evidence for login, create account, forgot password,
   verification, and reset links.
10. Update the operator runbook with exact commands, required hosts, expected artifacts, identity
   realm coverage, metrics/logs to inspect, and failure triage.
11. Record the HuleEdu teacher smoke evidence that pairs with the Skriptoteket proof.

## Test Plan

- Run `pdm run pr-0254-auth-cutover` against the intended local or Hemma target.
- Run the local smoke through the HuleEdu `TASK-0325` Gateway lane, not through public
  `https://api.hule.education` with loopback `return_to`.
- Verify HuleEdu `TASK-0326`, HuleEdu `TASK-0327`, and Skriptoteket `PR-0260` through `PR-0262`
  are accepted before final proof.
- Run focused auth tests affected by the smoke helper changes.
- Run `pdm run docs-validate`.

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
- The separate per-account public browser ceremony/Gateway profile proof has
  not run yet; it must be covered by the lifecycle/final proof chain before
  `PR-0254` closes.

## Rollback Plan

Revert the smoke/runbook additions if they encode an incorrect contract, then keep `ST-28-04`
open until the cross-app proof path is corrected.
