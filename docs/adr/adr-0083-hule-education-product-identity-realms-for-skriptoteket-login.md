---
type: adr
id: ADR-0083
title: "Hule Education product identity realms for Skriptoteket login"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2026-04-11
links:
  - "EPIC-28"
  - "ADR-0076"
  - "ADR-0082"
  - "REF-hule-education-product-identity-realms-and-skriptoteket-standalone-identity"
  - "ST-28-06"
  - "ST-28-07"
  - "ST-28-08"
  - "ST-28-09"
---

## Context

`PR-0253` retires Skriptoteket-local browser-session authority: Skriptoteket no
longer owns a browser login form, browser session cookie, local CSRF authority,
or local `/api/v1/auth/*` browser API. That hard break is intentional and keeps
the Hule Education Gateway/Identity layer as the shared browser edge.

The hard break must not collapse Skriptoteket identity into a HuleEdu-school-only
identity. Skriptoteket remains a product with its own account meaning, onboarding
semantics, projection, profile, RBAC, AI preferences, and local authorization.
Users must be able to log in to Skriptoteket without completing HuleEdu school
registration.

`REF-hule-education-product-identity-realms-and-skriptoteket-standalone-identity`
records the reference direction. This ADR is the retained decision package that
should turn that direction into an implementation contract before `ST-28-04` /
`PR-0254` is treated as the final cross-app proof.

## Decision

Hule Education Gateway/Identity will be the browser session and login ceremony
authority for Skriptoteket, but it must support product identity realms.

For Skriptoteket, the target model is:

- `skriptoteket_standalone` is a distinct product identity realm.
- HuleEdu school identity is a separate realm, not the only Skriptoteket login
  identity.
- A user may authenticate through the shared Hule Education ceremony for
  Skriptoteket without completing HuleEdu school registration.
- Account linking between HuleEdu school identity and Skriptoteket standalone
  identity is explicit, not implied by matching email or browser session.
- Browser login anchors target a browser-navigable ceremony URL, not a POST-only
  auth API endpoint.
- Downstream signed identity context distinguishes the shared browser session
  from the active product identity realm and active app.
- Skriptoteket resolves local projection and authorization from the signed
  realm-aware identity context, then applies local `User.role` for RBAC.
- `AuthProvider.LOCAL` and existing Skriptoteket-local identity data remain
  valid product-domain concepts until a later data migration explicitly replaces
  them.

The signed downstream context should define, at minimum:

- stable subject id
- active product identity realm
- active app, such as `skriptoteket`
- optional linked identity ids
- optional tenant/org context when the user operates inside a school context
- claims trusted enough for safe first-time Skriptoteket projection creation, if
  the login ceremony provisions access

## Consequences

`ST-28-04` / `PR-0254` must not certify a HuleEdu-school-only login path as the
final Skriptoteket login proof. It should wait until this ADR is accepted and
the browser ceremony/projection stories below define what is being proved.

Skriptoteket must not reintroduce local browser auth as a bridge. Registration,
password reset, email verification, and account linking remain Skriptoteket
product concerns, but the browser ceremony and session authority live in Hule
Education Gateway/Identity.

Projection and RBAC stay app-local. Hule Education proves browser identity and
active realm; Skriptoteket decides whether that identity has a local projection
and which local role it has.

Observability must move from local browser-session gauges to gateway/session,
identity-realm, projection, and local RBAC outcomes.
