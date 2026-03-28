---
type: epic
id: EPIC-28
title: "Skriptoteket auth authority cutover to HuleEdu"
status: proposed
owners: "agents"
created: 2026-03-28
updated: 2026-03-28
outcome: "Skriptoteket no longer owns browser auth authority locally; it consumes a HuleEdu-owned cookie-session + CSRF browser contract while preserving its richer bootstrap and modal-first UX."
dependencies: ["ADR-0009", "ADR-0011", "ADR-0030", "ADR-0076"]
---

## Scope

- Cut Skriptoteket browser auth over to a HuleEdu-owned session contract exposed at
  `https://api.hule.education`.
- Preserve the stronger existing Skriptoteket browser semantics:
  - cookie-session + CSRF
  - rich bootstrap document
  - modal-first login / expiry / logout UX
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

## Risks

- HuleEdu may initially deliver a session document that is too thin to preserve Skriptoteket's
  bootstrap semantics.
- Cross-origin cookie and CORS handling on `.hule.education` can break login/logout or CSRF if
  not treated as one first-class contract.
- WebSocket auth can regress into a second token lifecycle if not explicitly tied to the shared
  browser session authority.
- If local auth ownership is only partially removed, the repo can drift into a hidden dual-mode
  contract.

## Stories

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
- HuleEdu must deliver the shared browser session authority and rich bootstrap contract before
  this epic can move from planning to implementation.
