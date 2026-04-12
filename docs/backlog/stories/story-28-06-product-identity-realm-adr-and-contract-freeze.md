---
type: story
id: ST-28-06
title: "Product identity realm ADR and contract freeze"
status: blocked
owners: "agents"
created: 2026-04-11
updated: 2026-04-11
epic: "EPIC-28"
acceptance_criteria:
  - "Given `REV-PR-0253` accepts the local browser-auth retirement boundary, when this story completes, then `ADR-0083` is reviewed and accepted as the governing product identity realm contract for Skriptoteket login."
  - "Given Hule Education owns browser session authority, when the ADR is accepted, then it distinguishes browser session, product identity realm, Skriptoteket projection, and Skriptoteket RBAC without reintroducing a local browser auth bridge."
  - "Given `ST-28-04` / `PR-0254` is the cross-app proof lane, when this story completes, then its dependencies and wording make clear that final login proof waits for the accepted realm contract."
dependencies: ["REV-PR-0253", "PR-0253", "ADR-0083", "REF-hule-education-product-identity-realms-and-skriptoteket-standalone-identity"]
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
- `PR-0254` should be blocked or reframed until this contract is accepted.
