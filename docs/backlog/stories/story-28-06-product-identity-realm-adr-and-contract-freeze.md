---
type: story
id: ST-28-06
title: "Product identity realm ADR and contract freeze"
status: done
owners: "agents"
created: 2026-04-11
updated: 2026-04-12
epic: "EPIC-28"
acceptance_criteria:
  - "Given `REV-PR-0253` accepts the local browser-auth retirement boundary, when this story completes, then `ADR-0083` is reviewed and accepted as the governing product identity realm contract for Skriptoteket login."
  - "Given Hule Education owns browser session authority, when the ADR is accepted, then it distinguishes browser session, product identity realm, Skriptoteket projection, and Skriptoteket RBAC without reintroducing a local browser auth bridge."
  - "Given `ST-28-04` / `PR-0254` is the cross-app proof lane, when this story completes, then its dependencies and wording make clear that final login proof waits for the accepted realm contract."
dependencies:
  - "REV-PR-0253"
  - "PR-0253"
  - "ADR-0083"
  - "REV-ST-28-06"
  - "REF-hule-education-product-identity-realms-and-skriptoteket-standalone-identity"
---

## Context

`PR-0253` removes local browser-session authority, but follow-up implementation
needs an accepted contract for how Skriptoteket standalone identity works under
the shared Hule Education browser edge.

This story owns the decision package. It must happen after `PR-0253` is accepted
and before `ST-28-04` / `PR-0254` is treated as the final cross-app login proof.

## Notes

- Do not implement login flows in this story.
- The output is an accepted `ADR-0083` plus updated backlog wording.
- `PR-0255` is already complete and remains the signed-context/projection
  foundation consumed by this story.
- `PR-0254` was blocked until this contract and the downstream login/projection
  stories landed.

## Implementation Summary (as of 2026-04-12)

`ST-28-06` is complete through retained review `REV-ST-28-06`. `ADR-0083` is accepted as the
product identity realm contract for Skriptoteket login: Hule Education owns the browser session,
CSRF, gateway, and browser-navigable ceremony, while Skriptoteket retains standalone product
identity meaning, local projection, profile, AI preferences, and local RBAC.

The contract freezes `skriptoteket_standalone` and `huleedu_school` as the first accepted realms,
requires realm-aware signed context before final cross-app proof, rejects local browser-auth bridges
and provider-role-derived Skriptoteket RBAC, and cleared the path for `PR-0254` after `ST-28-07`
through `ST-28-09` implemented the login/projection path.
