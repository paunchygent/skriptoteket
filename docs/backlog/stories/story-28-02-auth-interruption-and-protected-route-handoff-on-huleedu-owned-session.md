---
type: story
id: ST-28-02
title: "Auth interruption and protected-route handoff on HuleEdu-owned session"
status: ready
owners: "agents"
created: 2026-03-28
updated: 2026-04-08
epic: "EPIC-28"
acceptance_criteria:
  - "Given an unauthenticated visitor enters a protected Skriptoteket route, when the route guard triggers, then Skriptoteket preserves the intended destination and routes through the canonical dedicated auth-entry page `/auth/login` so the HuleEdu-owned session flow can resume the intended protected route afterward."
  - "Given a user session expires or is revoked, when Skriptoteket detects the invalid session, then recovery remains redirect-preserving and page-based rather than falling back into app-local modal state or the old legacy `/login` behavior."
  - "Given the HuleEdu-owned auth ceremony requires a top-level handoff outside Skriptoteket, when authentication completes, then the browser returns to Skriptoteket and resumes the intended protected route without degrading the explicit auth-entry contract."
ui_impact: "Preserves redirect-preserving auth interruption and protected-route handoff while aligning the entry surface to the dedicated `/auth/login` page."
dependencies: ["ADR-0076", "ST-11-22", "ST-28-01"]
---

## Context

Skriptoteket deliberately removed the standalone legacy `/login` route, but the newer planned
direction is no longer modal-first auth entry. The acceptance bar for the cutover is now explicit
destination preservation through one dedicated auth-entry page contract.

The important invariant is the interruption and return behavior, not that every future auth step
must physically remain inside a modal. HuleEdu may eventually need a top-level auth ceremony for
SSO, MFA, passkeys, or consent. Skriptoteket should preserve explicit interruption and
protected-route handoff through `/auth/login` while allowing that ceremony to be HuleEdu-owned.

## Notes

- Browser auth ownership moves to HuleEdu Gateway/Identity.
- Skriptoteket keeps a route-preserving interruption UX through the dedicated `/auth/login` page.
- The underlying auth ceremony may be completed by HuleEdu in a top-level flow when needed.
- No route-fragmented fallback or app-local modal bridge should be introduced.
