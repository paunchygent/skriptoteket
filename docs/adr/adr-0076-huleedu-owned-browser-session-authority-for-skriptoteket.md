---
type: adr
id: ADR-0076
title: "HuleEdu-owned browser session authority for Skriptoteket"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2026-03-28
---

## Context

Skriptoteket already has the stronger browser-session model that the future shared SaaS surface
needs:

- secure cookie-based browser auth
- CSRF protection for non-GET requests
- rich bootstrap state through `GET /api/v1/auth/me`
- modal-first login and expiry handling in the SPA

HuleEdu already has the right long-term ownership split emerging on its side:

- Gateway is the intended browser auth edge
- Identity is the intended auth authority
- public runtime work is moving toward one shared auth/session surface

The current future-integration direction in [ADR-0011](./adr-0011-huleedu-identity-federation.md)
is now too loose for a real cutover. In particular, the old future options still leave room for:

- a browser bearer-token model
- a local Skriptoteket auth bridge
- multiple browser auth contracts coexisting across apps

That is the wrong long-term shape. The cutover target must preserve Skriptoteket-grade browser
semantics while moving auth ownership upward into HuleEdu-owned Gateway and Identity.

## Decision

### 1. Browser auth ownership

Skriptoteket SHALL adopt a hard-break browser auth contract owned by HuleEdu:

- HuleEdu Identity is the sole browser session authority
- HuleEdu Gateway is the only browser-facing auth/API edge
- the browser does not talk directly to Identity or downstream services

### 2. Browser transport

The shared browser auth contract SHALL use:

- secure cookies on `.hule.education`
- CSRF protection for non-GET browser requests

The browser SHALL NOT use bearer or refresh tokens stored in frontend-accessible storage as the
primary session model.

### 3. Canonical bootstrap route

The canonical browser bootstrap route SHALL be:

- `GET https://api.hule.education/v1/auth/session`

Browser use of `/v1/auth/me` as the primary bootstrap document SHALL be retired in favor of the
new explicit session contract.

The shared bootstrap document must be rich enough to replace the current Skriptoteket bootstrap,
including at minimum:

- `authenticated`
- `user`
- `profile`
- current org / tenant / context information as applicable
- roles / grants / access policy
- app-relevant bootstrap policy such as AI/session-critical flags

### 4. Browser auth origin

Both the Skriptoteket SPA and the HuleEdu SPA SHALL use `https://api.hule.education` as the
browser auth/API origin for session bootstrap, login, logout, refresh, and CSRF.

Skriptoteket SHALL NOT keep an app-local browser auth proxy surface as a transition bridge.

### 5. Modal-first UX preservation

Skriptoteket SHALL preserve its modal-first browser UX during the cutover:

- protected-route entry stays modal-first
- auth-expiry handling stays modal-first
- logout and session invalidation stay modal-first

The auth authority moves; the UX contract does not regress.

### 6. Internal service identity

Browser cookies terminate at HuleEdu Gateway. Downstream services, including Skriptoteket, SHALL
receive signed internal identity context from the gateway rather than raw browser cookies or
ad hoc per-app auth logic.

### 7. WebSocket alignment

WebSocket auth SHALL be session-derived. If an explicit token is needed for the handshake, it must
be short-lived and minted from the active browser session authority, not managed as a second
long-lived browser token lifecycle.

### 8. Rejected options

The following options are explicitly rejected:

- bearer-token browser auth as the end-state browser contract
- dual browser contracts, where Skriptoteket keeps its local cookie model while HuleEdu keeps a
  separate bearer-browser model
- an app-local Skriptoteket auth bridge that keeps browser auth ownership outside HuleEdu Gateway

## Consequences

- This is a hard break, not a compatibility bridge.
- HuleEdu must move upward to the stronger cookie-session + CSRF model before Skriptoteket can cut
  over cleanly.
- Skriptoteket frontend work should target the final `api.hule.education` session contract, not a
  temporary bearer-browser intermediary.
- Existing modal-first and rich-bootstrap behavior in Skriptoteket becomes an acceptance floor for
  the shared HuleEdu-owned contract.
- If this ADR is accepted, it narrows and supersedes ADR-0011's open future browser-auth options:
  the future path is no longer "local session bridge vs browser JWT vs both", but one
  HuleEdu-owned browser session authority with one canonical browser bootstrap contract.
