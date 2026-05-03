---
type: story
id: ST-28-04
title: "Cross-app auth cutover smoke and operator runbook proof"
status: done
owners: "agents"
created: 2026-03-28
updated: 2026-05-02
epic: "EPIC-28"
acceptance_criteria:
  - "Given `ADR-0083` is accepted and the realm-aware login stories are implemented, when a user starts auth from Skriptoteket, then the proof uses the browser-navigable Hule Education `app=skriptoteket` ceremony and never a POST-only `/v1/auth/login` API link."
  - "Given a Skriptoteket standalone identity is supported, when the smoke logs in with that realm, then the browser returns to Skriptoteket, opens a protected route, and receives gateway-signed downstream context for the Skriptoteket product realm."
  - "Given a HuleEdu school identity is supported for Skriptoteket, when the smoke logs in with that realm, then the proof distinguishes school identity from Skriptoteket projection and local RBAC."
  - "Given the shared browser session is active, when Skriptoteket performs a protected read and write, then the requests succeed through the shared session, CSRF, gateway, projection, and local RBAC contracts."
  - "Given a user logs out from either app, when the browser state refreshes, then both Skriptoteket and HuleEdu become unauthenticated without reviving local Skriptoteket browser sessions."
  - "Given local Docker proof uses loopback origins, when the smoke runs locally, then it targets the HuleEdu `TASK-0325` local/non-production Gateway lane with exact dev origins, HuleEdu login UI on `5174`, Gateway-proxied Skriptoteket APIs, and a local-only Gateway public signing key."
  - "Given HuleEdu proof identities are bootstrapped, when the smoke runs by role, then Skriptoteket resolves each required local role through `identity_projections` and local `User.role` without local password ownership."
  - "Given real standalone lifecycle proof is complete, when final cutover proof is reviewed, then account creation, email verification, login, forgot-password, reset, callback continuation, projection, and local RBAC have already been proven through sanitized artifacts."
  - "Given a deliberate auth or lifecycle link is clicked, when the browser leaves Skriptoteket or opens from email, then the canonical route lands directly on the requested action page; generic HuleEdu pages are allowed only for fallback or interruption recovery."
  - "Given the shared browser session cutover ships, when operator proof is reviewed, then HuleEdu teacher smoke and a dedicated Skriptoteket realm-aware Playwright auth-cutover smoke are both green and documented in the runbook."
ui_impact: "Adds explicit cross-app auth proof and operator verification guidance."
dependencies: ["ADR-0076", "ADR-0083", "ST-28-05", "ST-28-01", "ST-28-02", "ST-28-03", "ST-28-06", "ST-28-07", "ST-28-08", "ST-28-09", "ST-28-11", "ST-28-12", "HuleEdu TASK-0325", "HuleEdu TASK-0326", "HuleEdu TASK-0327", "HuleEdu TASK-0380"]
---

## Context

This cutover is not complete when unit tests pass. Now that `PR-0258` review remediation is closed,
this story is the final realm-aware proof lane for the product identity realm ADR, login ceremony,
lifecycle handoff, and projection provisioning contracts.

Local proof now has explicit provider prerequisites: HuleEdu `TASK-0325` must provide the
local/non-production shared-auth Gateway lane, `TASK-0326` must provide the proof identity subject
export, and `TASK-0327` must prove the real standalone lifecycle with controlled accounts.
`PR-0254` consumes those lanes instead of pointing loopback callbacks at public production, adding
a Skriptoteket-only identity-header injector, or turning fake alpha users into a launch blocker.

The proof must cover:

- auth entry via the browser-navigable Hule Education `app=skriptoteket` ceremony
- Skriptoteket standalone identity where supported
- HuleEdu school identity where supported, without collapsing it into standalone identity
- protected-route bootstrap
- CSRF-protected write behavior through Gateway
- signed downstream context and local projection resolution
- logout invalidation across both apps
- proof-role coverage through local `User.role`
- prior real-account lifecycle proof for create account, verify email, login, forgot password,
  reset password, and continuation
- direct-action landing for login, registration, forgot password, verification, and reset links

## Notes

- Add one dedicated Playwright auth-cutover smoke for Skriptoteket.
- Update the operator runbook with the exact public proof steps and failure interpretation.
- Do not certify the superseded modal-first auth-entry seam as the target contract for this lane.
- Do not certify a HuleEdu-school-only login path as final Skriptoteket login.
- `ST-28-06` through `ST-28-09` are complete; this story is ready to prove the full
  realm-aware cross-app behavior through Docker/operator smoke evidence.
- Local `localhost` and `127.0.0.1` proof must use a local or non-production Gateway configured
  with exact dev origins. Public `https://api.hule.education` rejecting those loopback return
  targets remains correct behavior, not a Skriptoteket defect.
- HuleEdu `TASK-0325` freezes the local proxy contract consumed here:
  browser-visible auth URLs use `http://localhost:8080`; host-run Vite may set
  `VITE_DEV_PROXY_TARGET=http://localhost:8080`, while the normal Docker frontend service sets
  `VITE_DEV_PROXY_TARGET=http://huleedu_api_gateway_service:8080` on `hule-network` and
  `VITE_DEV_BACKEND_PROXY_TARGET=http://skriptoteket_web:8000`; protected browser
  `/api/...` traffic enters Gateway before forwarding to
  `API_GATEWAY_SKRIPTOTEKET_BACKEND_URL=http://skriptoteket-web:8000`, while public
  `/api/v1/public/...` remains directly served by Skriptoteket.
- `PR-0254` persists the auditable live proof as `pdm run pr-0254-auth-cutover`; the
  proof asserts public Klassrumskartan bootstrap stays `200` before login, then verifies
  HuleEdu Gateway `:8080`, HuleEdu login UI `:5174`, and app-continuation `200`.
- `ST-28-11` / `PR-0260` now own the Skriptoteket projection and local role matrix bootstrap
  that consumes HuleEdu `TASK-0326`.
- `ST-28-12` / `PR-0261` / `PR-0262` now own the user-facing auth entry and real lifecycle proof
  that consumes HuleEdu `TASK-0327`.

## Implementation Summary (as of 2026-04-13)

`ST-28-04` is complete through `PR-0254` and `PR-0263` on both required local loopback lanes. The
retained proof
first validates HuleEdu `TASK-0326`, HuleEdu `TASK-0327`, Skriptoteket `PR-0261`, and Skriptoteket
`PR-0262` artifacts, then runs the final cross-process smoke through Skriptoteket SPA, HuleEdu
Gateway auth entry, HuleEdu login UI/session, Gateway-proxied protected `/api` calls, signed
app-continuation, local identity projection, local `User.role` RBAC, CSRF-protected write, and
shared logout invalidation.

Latest retained canonical artifact:

```text
.artifacts/playwright-pr-0254-auth-cutover/local-nonprod/20260413T154741Z/manifest.redacted.json
```

Final two-lane retained artifact after `PR-0263` loopback-origin parity:

```text
.artifacts/playwright-pr-0254-auth-cutover/local-nonprod/20260413T160856Z/manifest.redacted.json
```

The final manifest records both `localhost` and `127` lane summaries as `status=ok`.

## Production Regression Follow-up (2026-04-25)

`PR-0272` is a post-closeout remediation slice for a signed internal identity
transport spelling drift found in production after HuleEdu corrected its header
names from `X-Huledu-Identity-*` to `X-HuleEdu-Identity-*`. The follow-up is
scoped to Skriptoteket's verifier, proof helpers, tests, and docs inventory. It
must not change projection keys, local RBAC, provisioning policy, CSRF/logout
ownership, or production protected API host policy.

## Hemma Reboot Readiness Follow-up (2026-05-02)

`PR-0280` is a done post-closeout operational follow-up for Hemma reboot
behavior. It consumes completed HuleEdu `TASK-0509` evidence that Tier 0
auto-recovers, runtime lanes stay manual after restart-policy normalization,
and `hemma-start-hostwide` restores Skriptoteket before retaining HuleEdu
`api.hule.education` TLS/SNI, Gateway health, auth ceremony, and protected API
proof. The story now distinguishes Skriptoteket self-health, public
Klassrumskartan/share availability, and HuleEdu-auth readiness. No separate
host/systemd task is needed unless future evidence contradicts the
wrapper/restart-policy contract.

## Local Bootstrap/Auth-Edge Follow-up (2026-05-03)

`PR-0283` is a ready post-closeout local-dev follow-up for the `.env`
bootstrap account and authenticated live-proof entrypoint. It keeps the retired
Skriptoteket-local password login endpoint retired, splits credential truth
from app-local authorization truth, and requires proof that HuleEdu accepts the
`.env` credentials while Skriptoteket resolves the resulting Gateway-signed
context to a projected local `superuser`. HuleEdu `TASK-0380` now owns and
retains evidence for the `browser-bootstrap` Identity seed scope, so
Skriptoteket can consume those credentials in authenticated browser proof.
PR-0283 also pins the local-only durable account target to
`superuser@local.dev` / `superuser-password` across the HuleEdu provider and
Skriptoteket consumer `.env` surfaces, and requires a deterministic local proof
matrix for every active Skriptoteket RBAC tier (`user`, `contributor`, `admin`,
`superuser`). Public and share-route proof remains direct to Skriptoteket and
must not be made dependent on the HuleEdu auth edge.
