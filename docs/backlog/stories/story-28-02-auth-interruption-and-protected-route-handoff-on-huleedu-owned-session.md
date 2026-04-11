---
type: story
id: ST-28-02
title: "Auth interruption and protected-route handoff on HuleEdu-owned session"
status: done
owners: "agents"
created: 2026-03-28
updated: 2026-04-11
epic: "EPIC-28"
acceptance_criteria:
  - "Given the dedicated `/auth/login` auth-entry contract already exists through `ST-32-10`, when an unauthenticated visitor enters a protected Skriptoteket route under the HuleEdu-owned session model, then Skriptoteket preserves the intended destination and routes through that canonical auth-entry page so the shared session flow can resume the intended protected route afterward."
  - "Given a user session expires or is revoked, when Skriptoteket detects the invalid session, then recovery remains redirect-preserving and page-based rather than falling back into app-local modal state or the old legacy `/login` behavior."
  - "Given the HuleEdu-owned auth ceremony requires a top-level handoff outside Skriptoteket, when authentication completes, then the browser returns to Skriptoteket and resumes the intended protected route without degrading the explicit auth-entry contract."
ui_impact: "Preserves redirect-preserving auth interruption and protected-route handoff while aligning the entry surface to the dedicated `/auth/login` page."
dependencies: ["ADR-0076", "ST-28-05", "ST-28-01", "ST-32-10"]
---

## Context

Skriptoteket deliberately removed the standalone legacy `/login` route, but the newer planned
direction is no longer modal-first auth entry. The acceptance bar for the cutover is now explicit
destination preservation through one dedicated auth-entry page contract.

The important invariant is the interruption and return behavior, not that every future auth step
must physically remain inside a modal. HuleEdu may eventually need a top-level auth ceremony for
SSO, MFA, passkeys, or consent. Skriptoteket should preserve explicit interruption and
protected-route handoff through the already-landed `/auth/login` contract while allowing that
ceremony to be HuleEdu-owned.

## Notes

- Browser auth ownership moves to HuleEdu Gateway/Identity.
- `ST-32-10` / `PR-0242` own the `/auth/login` route contract; this story consumes that contract
  under the shared-session cutover.
- Skriptoteket keeps a route-preserving interruption UX through the dedicated `/auth/login` page.
- The underlying auth ceremony may be completed by HuleEdu in a top-level flow when needed.
- No route-fragmented fallback or app-local modal bridge should be introduced.

## Implementation Summary (as of 2026-04-11)

`PR-0252` shipped the HuleEdu-session-era return-to-origin proof while keeping the scope narrow:
protected-route interruption, app-local `401` recovery, and top-level `/auth/login?next=...`
return all preserve the dedicated auth-entry contract. The live proof exercises the real backend
app-continuation route and signed HuleEdu request context, but does not retire the remaining local
browser-auth authority surfaces; that remains owned by `PR-0253`.
