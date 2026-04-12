---
type: story
id: ST-28-07
title: "Hule Education-hosted Skriptoteket login ceremony"
status: done
owners: "agents"
created: 2026-04-11
updated: 2026-04-12
epic: "EPIC-28"
acceptance_criteria:
  - "Given `ADR-0083` is accepted, when a signed-out user starts from Skriptoteket, then the browser enters one Hule Education-hosted `app=skriptoteket` login ceremony without seeing a second Skriptoteket login page."
  - "Given the SPA renders a login handoff, when the user follows it, then the link targets a browser-navigable ceremony URL and never a POST-only `/v1/auth/login` API endpoint."
  - "Given a `next` destination is supplied, when the ceremony completes, then the user returns only to an allowed Skriptoteket origin and the original destination is preserved."
  - "Given the user chooses a supported realm, when authentication completes, then the gateway signs downstream context with the active app and product identity realm."
ui_impact: "Replaces temporary handoff copy with a direct, product-aware login ceremony."
dependencies:
  - "ST-28-06"
  - "ADR-0083"
  - "PR-0253"
  - "PR-0256"
  - "REV-PR-0256"
  - "HuleEdu TASK-0313"
  - "HuleEdu TASK-0314"
---

## Context

`PR-0253` split browser ceremony URLs from shared auth API URLs, but it does not
implement the real Hule Education-hosted Skriptoteket login ceremony. This story
owns the user-facing login path.

The ceremony must preserve unity through Hule Education while allowing
Skriptoteket standalone identity to remain distinct from HuleEdu school identity.

## Notes

- This is likely a cross-repo story with Hule Education Gateway/Identity work.
- Skriptoteket should keep `/auth/login?next=...` only as an interruption,
  fallback, or auto-handoff route.
- Do not restore local password collection in the Skriptoteket SPA.
- `PR-0254` should consume this story before it claims final login proof.
- `ADR-0083` is accepted through `ST-28-06` / `REV-ST-28-06`.
- HuleEdu `TASK-0313` / `TASK-0314` cleared the provider blocker with retained contract and public
  proof.
- `PR-0256` implemented the Skriptoteket consumer side: `/auth/login` now links to HuleEdu
  `GET /auth/login` with `app=skriptoteket`, default
  `product_identity_realm=skriptoteket_standalone`, callback `return_to=/auth/callback`, and safe
  route-level `next`; `/auth/callback` resumes the intended protected route after shared-session
  bootstrap.
- Review remediation keeps query/hash details on callback resume, hardens helper-level `next`
  handling against hostile/loop values, and fails closed unless the signed context carries
  `active_app=skriptoteket`, a supported product identity realm, and `realm_subject_id`.
- Realm-aware projection lookup remains explicitly owned by `ST-28-09`.
