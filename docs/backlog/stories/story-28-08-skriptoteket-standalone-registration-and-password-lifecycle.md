---
type: story
id: ST-28-08
title: "Skriptoteket standalone registration and password lifecycle"
status: blocked
owners: "agents"
created: 2026-04-11
updated: 2026-04-12
epic: "EPIC-28"
acceptance_criteria:
  - "Given Skriptoteket no longer serves local browser auth routes, when a user needs a Skriptoteket standalone account, then registration is available through the Hule Education-hosted Skriptoteket realm ceremony without HuleEdu school registration."
  - "Given a standalone Skriptoteket user forgets a password, when recovery starts, then password reset and email verification are handled by the shared identity surface while preserving Skriptoteket product copy and return behavior."
  - "Given old `/register`, `/forgot-password`, `/reset-password`, and `/verify-email` links are opened, when the flow is supported, then those links hand off to the correct shared ceremony target instead of posting to local `/api/v1/auth/*`."
  - "Given the local browser auth API remains retired, when tests scan frontend and OpenAPI surfaces, then no local register/reset/verify browser endpoint is reintroduced."
ui_impact: "Restores user self-service for Skriptoteket standalone identity through the shared identity surface."
dependencies:
  - "ST-28-06"
  - "ST-28-07"
  - "ADR-0083"
  - "PR-0253"
  - "PR-0257"
  - "REV-PR-0257"
  - "HuleEdu standalone lifecycle provider contract"
---

## Context

`PR-0253` intentionally removes Skriptoteket-local browser registration,
verification, and password routes. The product meaning still exists: a user
should be able to create and recover a Skriptoteket standalone identity.

This story moves that lifecycle to the shared Hule Education Identity surface
without merging it into HuleEdu school registration.

## Notes

- Do not re-add local browser-auth endpoints in Skriptoteket.
- Keep old-link behavior deliberate and tested.
- Account creation claims must be trusted enough for projection provisioning or
  explicitly route through admin/import activation.

## Provider Contract Gate (2026-04-12)

`PR-0257` is opened as the governing implementation package, but the retained
review `REV-PR-0257` keeps this story blocked. HuleEdu has proved the
`app=skriptoteket` login ceremony, but the retained shared browser-session
contract does not yet define app/realm-aware registration, password reset, or
email verification ceremonies.

Required unblocker: HuleEdu must publish and prove browser-navigable lifecycle
surfaces that accept `app=skriptoteket`, `product_identity_realm`, allowed
Skriptoteket return targets, and safe route-level continuation. Direct Identity
Service API routes are not enough for this story, and standalone registration
must not require HuleEdu school organization registration.
