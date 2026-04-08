---
type: epic
id: EPIC-28
title: "Skriptoteket auth authority cutover to HuleEdu"
status: proposed
owners: "agents"
created: 2026-03-28
updated: 2026-04-08
outcome: "Skriptoteket no longer owns browser auth authority locally; it consumes a HuleEdu-owned cookie-session + CSRF browser contract through the intended launch topology where `hule.education` is the HuleEdu landing page, `api.hule.education` is the shared browser auth/API edge, and `skriptoteket.hule.education` remains the Skriptoteket app host while preserving richer bootstrap and dedicated redirect-preserving auth-entry handoff."
dependencies:
  - "ADR-0009"
  - "ADR-0011"
  - "ADR-0030"
  - "ADR-0076"
  - "REF-huleedu-launch-surface-and-shared-auth-topology-2026-04-08"
---

## Scope

- Cut Skriptoteket browser auth over to a HuleEdu-owned session contract exposed at
  `https://api.hule.education`.
- Freeze the cross-repo launch topology and host ownership assumptions before local cutover work:
  `hule.education` = HuleEdu landing page, `api.hule.education` = shared auth/API edge,
  `skriptoteket.hule.education` = Skriptoteket app host.
- Preserve the stronger existing Skriptoteket browser semantics:
  - cookie-session + CSRF
  - rich bootstrap document
  - dedicated `/auth/login` entry and redirect-preserving auth handoff UX
- Replace browser bootstrap from local `/api/v1/auth/me` with shared
  `/v1/auth/session`.
- Remove Skriptoteket-local browser auth ownership and assumptions once the shared contract is in
  place.
- Add an explicit cross-app smoke lane proving shared login/logout/session behavior across
  Skriptoteket and HuleEdu.

## Out of scope

- OIDC provider integration as the first blocker for the cutover
- a bearer-browser transitional contract
- a permanent app-local auth proxy or bridge in Skriptoteket
- keeping two browser auth contracts alive indefinitely
- implementing the HuleEdu landing page or gateway itself inside this repo

## Risks

- HuleEdu may initially deliver a session document that is too thin to preserve Skriptoteket's
  bootstrap semantics.
- Cross-origin cookie and CORS handling on `.hule.education` can break login/logout or CSRF if
  not treated as one first-class contract.
- WebSocket auth can regress into a second token lifecycle if not explicitly tied to the shared
  browser session authority.
- If local auth ownership is only partially removed, the repo can drift into a hidden dual-mode
  contract.
- If the cross-repo launch topology is not frozen first, later landing, gateway, SSO, and SEO work
  can harden around contradictory host assumptions.

## Stories

- [ST-28-05: Cross-repo launch surface and shared auth dependency freeze](../stories/story-28-05-cross-repo-launch-surface-and-shared-auth-dependency-freeze.md)
- [ST-28-01: Frontend auth store and API client cutover to HuleEdu session contract](../stories/story-28-01-frontend-auth-store-and-api-client-cutover-to-huleedu-session-contract.md)
- [ST-28-02: Auth interruption and protected-route handoff on HuleEdu-owned session](../stories/story-28-02-auth-interruption-and-protected-route-handoff-on-huleedu-owned-session.md)
- [ST-28-03: Remove local auth ownership and regenerate client contracts](../stories/story-28-03-remove-local-auth-ownership-and-regenerate-client-contracts.md)
- [ST-28-04: Cross-app auth cutover smoke and operator runbook proof](../stories/story-28-04-cross-app-auth-cutover-smoke-and-operator-runbook-proof.md)

## Dependencies

- ADR-0009 defines the current local cookie-session baseline.
- ADR-0011 provides the earlier federation foundation but is too permissive for the final browser
  contract.
- ADR-0030 keeps the SPA aligned to cookie-session + CSRF expectations.
- ADR-0076 defines the new hard-break HuleEdu-owned browser auth target.
- Skriptoteket must land the dedicated `/auth/login` route contract through
  `ST-32-10` / `PR-0242` before `ST-28-02` can complete; this epic consumes that
  route contract rather than owning it.
- HuleEdu must deliver the shared browser session authority and rich bootstrap contract before
  this epic can move from planning to implementation.
- The cross-repo launch topology and upstream edge ownership are now recorded in
  [REF-huleedu-launch-surface-and-shared-auth-topology-2026-04-08](../../reference/ref-huleedu-launch-surface-and-shared-auth-topology-2026-04-08.md).

## Planning note (2026-04-08)

The old modal-first auth-entry language is now superseded for new work by the dedicated `/auth/login`
direction planned in `ST-32-10` / `PR-0242`. This epic should be read with that updated
page-based handoff contract, not with the older modal-only assumption from `ST-11-22`.

## Sequencing note (2026-04-08)

`ST-28-05` is now the cross-repo gating story for this epic. The paced order is:

1. freeze launch topology and shared-edge ownership
2. land the dedicated `/auth/login` route contract through `ST-32-10` / `PR-0242`
3. consume the shared browser session contract in Skriptoteket
4. preserve `/auth/login` interruption and return-to-origin behavior on the HuleEdu-owned session
5. remove local browser auth ownership
6. prove the cutover cross-app and operator-side
