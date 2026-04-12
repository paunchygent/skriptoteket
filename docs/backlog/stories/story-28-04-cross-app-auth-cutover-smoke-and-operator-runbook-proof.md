---
type: story
id: ST-28-04
title: "Cross-app auth cutover smoke and operator runbook proof"
status: ready
owners: "agents"
created: 2026-03-28
updated: 2026-04-12
epic: "EPIC-28"
acceptance_criteria:
  - "Given `ADR-0083` is accepted and the realm-aware login stories are implemented, when a user starts auth from Skriptoteket, then the proof uses the browser-navigable Hule Education `app=skriptoteket` ceremony and never a POST-only `/v1/auth/login` API link."
  - "Given a Skriptoteket standalone identity is supported, when the smoke logs in with that realm, then the browser returns to Skriptoteket, opens a protected route, and receives gateway-signed downstream context for the Skriptoteket product realm."
  - "Given a HuleEdu school identity is supported for Skriptoteket, when the smoke logs in with that realm, then the proof distinguishes school identity from Skriptoteket projection and local RBAC."
  - "Given the shared browser session is active, when Skriptoteket performs a protected read and write, then the requests succeed through the shared session, CSRF, gateway, projection, and local RBAC contracts."
  - "Given a user logs out from either app, when the browser state refreshes, then both Skriptoteket and HuleEdu become unauthenticated without reviving local Skriptoteket browser sessions."
  - "Given local Docker proof uses loopback origins, when the smoke runs locally, then it targets the HuleEdu `TASK-0325` local/non-production Gateway lane with exact dev origins, HuleEdu login UI on `5174`, Gateway-proxied Skriptoteket APIs, and a local-only Gateway public signing key."
  - "Given the shared browser session cutover ships, when operator proof is reviewed, then HuleEdu teacher smoke and a dedicated Skriptoteket realm-aware Playwright auth-cutover smoke are both green and documented in the runbook."
ui_impact: "Adds explicit cross-app auth proof and operator verification guidance."
dependencies: ["ADR-0076", "ADR-0083", "ST-28-05", "ST-28-01", "ST-28-02", "ST-28-03", "ST-28-06", "ST-28-07", "ST-28-08", "ST-28-09", "HuleEdu TASK-0325"]
---

## Context

This cutover is not complete when unit tests pass. Now that `PR-0258` review remediation is closed,
this story is the final realm-aware proof lane for the product identity realm ADR, login ceremony,
lifecycle handoff, and projection provisioning contracts.

Local proof now has an explicit provider prerequisite: HuleEdu `TASK-0325` must provide the
local/non-production shared-auth Gateway lane. `PR-0254` consumes that lane instead of pointing
loopback callbacks at public production or adding a Skriptoteket-only identity-header injector.

The proof must cover:

- auth entry via the browser-navigable Hule Education `app=skriptoteket` ceremony
- Skriptoteket standalone identity where supported
- HuleEdu school identity where supported, without collapsing it into standalone identity
- protected-route bootstrap
- CSRF-protected write behavior through Gateway
- signed downstream context and local projection resolution
- logout invalidation across both apps

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
  `VITE_DEV_PROXY_TARGET=http://localhost:8080` for the canonical lane,
  `VITE_DEV_PROXY_TARGET=http://127.0.0.1:8080` for the separate 127 lane, and
  protected browser `/api/...` traffic enters Gateway before forwarding to
  `API_GATEWAY_SKRIPTOTEKET_BACKEND_URL=http://skriptoteket-web:8000`.
