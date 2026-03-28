---
type: story
id: ST-28-02
title: "Auth interruption and protected-route handoff on HuleEdu-owned session"
status: ready
owners: "agents"
created: 2026-03-28
epic: "EPIC-28"
acceptance_criteria:
  - "Given an unauthenticated visitor enters a protected Skriptoteket route, when the route guard triggers, then Skriptoteket preserves the intended destination and starts a modal-first auth interruption that can complete through the HuleEdu-owned session flow."
  - "Given a user session expires or is revoked, when Skriptoteket detects the invalid session, then recovery remains modal-first and does not regress into a dedicated `/login` route or route-fragmented fallback flow."
  - "Given the HuleEdu-owned auth ceremony requires a top-level handoff outside the modal, when authentication completes, then the browser returns to Skriptoteket and resumes the intended protected route without degrading the current UX contract."
ui_impact: "Preserves the existing modal-first auth interruption experience while allowing a HuleEdu-owned auth ceremony behind it."
dependencies: ["ADR-0076", "ST-11-22", "ST-28-01"]
---

## Context

Skriptoteket deliberately removed the standalone `/login` route and now treats auth interruption,
expiry, and protected-route entry as one modal-first UX contract. That behavior is part of the
acceptance bar for the cutover and must survive the move to HuleEdu-owned session authority.

The important invariant is the interruption and return behavior, not that every future auth step
must physically remain inside the modal. HuleEdu may eventually need a top-level auth ceremony for
SSO, MFA, passkeys, or consent. Skriptoteket should preserve modal-first interruption and
protected-route handoff while allowing that ceremony to be HuleEdu-owned.

## Notes

- Browser auth ownership moves to HuleEdu Gateway/Identity.
- Skriptoteket keeps a modal-first interruption UX and route-preserving handoff.
- The underlying auth ceremony may be completed by HuleEdu in a top-level flow when needed.
- No route-fragmented fallback or bridge login page should be introduced.
