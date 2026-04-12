---
type: reference
id: REF-hule-education-product-identity-realms-and-skriptoteket-standalone-identity
title: "Reference: Hule Education product identity realms and Skriptoteket standalone identity"
status: active
owners: "agents"
created: 2026-04-11
updated: 2026-04-12
topic: "hule-education-product-identity-realms"
links:
  - ADR-0083
  - ADR-0076
  - ADR-0082
  - EPIC-28
  - PR-0253
  - PR-0254
  - PR-0256
  - PR-0257
  - PR-0258
  - REV-PR-0253
  - REV-PR-0256
---

## Purpose

This reference records a critical architecture correction for `EPIC-28`: retiring
Skriptoteket-local browser-session authority must not erase Skriptoteket's standalone product
identity.

The intended direction is unity at the Hule Education browser edge without forcing all users into a
single HuleEdu school-registration identity. Skriptoteket remains a product with its own identity
meaning, onboarding path, and local authorization model, even when the browser session and gateway
contract are served by Hule Education infrastructure.

This began as a reference direction and is now implemented through the main realm-auth consumer
slices: `ADR-0083` froze the product-realm contract, HuleEdu `TASK-0313` / `TASK-0314` published and
publicly proved the provider ceremony/context, Skriptoteket `PR-0256` consumes the login ceremony,
`PR-0257` consumes the standalone lifecycle handoff, and `PR-0258` implements realm-aware
projection provisioning.

## Core Concept: Product Identity Realm

A **product identity realm** is a distinct product account namespace authenticated through the
shared Hule Education identity platform.

Under this model:

- Hule Education owns the browser session, CSRF, gateway, login ceremony, and signed downstream
  context.
- Hule Education Identity may authenticate more than one product realm.
- Skriptoteket may have a standalone identity realm, separate from a HuleEdu school identity.
- A user may log in only to Skriptoteket without completing a HuleEdu school-registration process.
- A user may later link or upgrade between realms, but linking must be explicit.
- Skriptoteket continues to own app-local profile, RBAC, AI preferences, and product-specific
  authorization.

Useful mental model: Hule Education can provide a shared umbrella login platform while preserving
product identity separation, similar to how related products can share infrastructure without
collapsing their account semantics into one product identity.

## Required Separation Of Concerns

| Concern | Owner | Notes |
|---|---|---|
| Browser session cookies | Hule Education Gateway / Identity | One browser session authority for the umbrella, not per-app cookies |
| CSRF for browser writes | Hule Education Gateway / Identity | Shared browser safety contract |
| Browser login ceremony | Hule Education Identity surface | Must be a browser-navigable ceremony, not a POST-only API route |
| Product identity realm choice | Hule Education Identity surface, with product input from Skriptoteket | Login can offer HuleEdu school identity, Skriptoteket standalone identity, or account linking |
| Skriptoteket projection | Skriptoteket | Resolves the signed identity context into local app user/profile state |
| Skriptoteket RBAC | Skriptoteket | Contributor/admin/superuser remain app-local decisions |
| Skriptoteket registration meaning | Skriptoteket product + Hule Education Identity implementation | Signup can be hosted by the shared identity platform while still creating a Skriptoteket identity |

## What PR-0253 Must Not Imply

`PR-0253` may remove Skriptoteket-owned browser-session infrastructure:

- local browser session table/model/repository
- local browser-auth API routes
- local CSRF authority tied to Skriptoteket session cookies
- local login/logout/current-user browser authority

`PR-0253` must not imply:

- Skriptoteket no longer has standalone accounts
- every Skriptoteket user must register for the HuleEdu school product
- `auth_provider = huleedu` is the only future identity source for Skriptoteket
- missing projections should permanently strand standalone Skriptoteket users
- registration/password lifecycle no longer exists as a Skriptoteket product concern

The corrected reading is:

> Skriptoteket does not own browser session authority, but it still owns a product identity realm
> and app-local authorization. Hule Education provides the shared edge where those identities are
> authenticated.

## Login UX Direction

The current `/auth/login` handoff is useful as a redirect-preserving technical route, but it is poor
UX if it becomes a second login page that asks users to click onward to another login page.

Target direction:

- User-facing login actions should begin one clear Hule Education-hosted login ceremony.
- The ceremony is product-aware: `GET https://api.hule.education/auth/login` with
  `app=skriptoteket`.
- The ceremony should allow the user to choose or use an existing identity realm:
  - HuleEdu school identity
  - Skriptoteket standalone identity
  - future explicit account-linking path
- Skriptoteket `/auth/login?next=...` may remain as an app-local interruption/fallback route, but
  it should behave like a transition page or auto-handoff, not a second login form/page.
- Skriptoteket uses `/auth/callback` as the HuleEdu return route; the ceremony sends that callback
  as `return_to` and keeps the route continuation in safe same-origin `next`.
- Auth success returns normal continuation targets as route strings so Vue Router preserves query
  and hash details.
- The browser handoff URL must be a browser-navigable Hule Education ceremony URL. It must not be a
  POST-only JSON/API route that returns `405 Method Not Allowed` when opened by an anchor.
- In `PR-0253`, the SPA must keep API endpoint helpers and browser ceremony helpers separate:
  `/v1/auth/session`, `/v1/auth/csrf`, and `/v1/auth/logout` remain API surfaces, while login
  anchors use `VITE_HULEEDU_AUTH_ENTRY_URL` or the documented browser ceremony default.

## Signed Context Direction

Downstream signed identity context distinguishes the umbrella session from the product realm.
The accepted additive fields are:

- stable subject id
- `active_product_identity_realm`, such as `huleedu_school` or `skriptoteket_standalone`
- optional `linked_identity_ids`
- `active_app`, such as `skriptoteket`
- `realm_subject_id`
- optional current tenant/org context when the user is operating in a school-owned HuleEdu context
- claims that are trusted enough to create or activate a Skriptoteket projection, if signup is part
  of the shared identity ceremony

Skriptoteket should then resolve local projection by a stable product-aware identity key, not by a
realm-ambiguous `sub` alone.

Current `PR-0258` state: app continuation fails closed unless the signed context carries
`active_app=skriptoteket`, `active_product_identity_realm` in the accepted set, and
`realm_subject_id`. Projection lookup now uses the realm-aware key
`(product_identity_realm, realm_subject_id)`.

## Locked Projection Direction

The core ceremony/context contract is frozen, the login and lifecycle consumer slices are done, and
`ST-28-09` / `PR-0258` shipped the clean projection migration:

- Use a dedicated local projection table keyed by `(product_identity_realm, realm_subject_id)`.
- Backfill existing HuleEdu-linked `(auth_provider=huleedu, external_id=...)` rows into
  `huleedu_school` projections before dropping the old field, and fail on ambiguous data.
- Remove `users.external_id` rather than renaming, repurposing, or leaving it as legacy provider
  metadata.
- Provision first-time Skriptoteket projections only when signed HuleEdu context includes
  `active_app=skriptoteket`, accepted realm, realm subject, email, and verified email state.
- Keep provisioning fail-closed unless those email and verification claims are explicit signed
  fields in `InternalIdentityContextV1`.
- Default newly provisioned local users to `user`; contributor/admin/superuser remain local
  promotions.
- Treat matching email as insufficient for account linking; linking must be explicit.
- Prove local Docker auth ceremonies against a local or non-production HuleEdu Gateway with exact
  dev-origin allowlisting.

The remaining open question belongs to `ST-28-10`: which metrics should distinguish gateway auth
success, identity realm selected, projection resolved, projection missing, provisioning blocked,
and local RBAC denial?

## Planning Consequences

- `REV-PR-0253` is approved; local browser-session retirement must continue to preserve this
  architectural direction and avoid documenting a HuleEdu-only identity future.
- `PR-0253` can still retire local browser-session authority, but it should leave follow-up work
  explicit for product identity realms and standalone Skriptoteket identity.
- `PR-0254` should not treat cross-app auth proof as proof that all Skriptoteket users are HuleEdu
  school identities.
- `ADR-0083` is accepted as the product-identity-realm contract for the implemented consumer path.
- Follow-up stories now scaffold the sequence:
  - `ST-28-06` accepted the ADR and froze the contract through `REV-ST-28-06`.
  - `ST-28-07` implemented the Hule Education-hosted Skriptoteket login ceremony through `PR-0256`.
  - `ST-28-08` shipped standalone registration/password lifecycle handoffs through `PR-0257`.
  - `ST-28-09` shipped realm-aware projection provisioning and local RBAC preservation through
    `PR-0258`.
  - `ST-28-04` / `PR-0254` becomes the final realm-aware cross-app proof after those stories.
  - `ST-28-10` reintroduces auth outcome observability without local session gauges.
