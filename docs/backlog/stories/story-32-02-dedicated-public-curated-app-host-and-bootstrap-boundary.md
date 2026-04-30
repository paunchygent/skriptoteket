---
type: story
id: ST-32-02
title: "Dedicated public curated-app host and bootstrap boundary"
status: done
owners: "agents"
created: 2026-04-03
updated: 2026-04-30
epic: "EPIC-32"
dependencies: ["ST-32-01", "ADR-0079"]
acceptance_criteria:
  - "Given a curated app supports public access, when an unauthenticated visitor opens its approved public entry route, then the SPA resolves a dedicated public host path outside `/apps/:appId`."
  - "Given the public curated-app host exists, when an authenticated or unauthenticated user uses the current `/apps/:appId` route or `GET /api/v1/apps/{app_id}` detail lookup, then those authenticated seams remain unchanged."
  - "Given a bespoke curated app supports both guest and authenticated use, when the SPA renders it, then the same app-specific shell can switch modes without falling back to the generic tool UI."
  - "Given a public curated-app bootstrap/detail contract is introduced, when it is reviewed, then it exposes only public-safe metadata and mode/bootstrap fields rather than owner-scoped app state."
ui_impact: "Introduces a dedicated public curated-app host path and guest/auth mode switching in bespoke app shells."
data_impact: "No schema change required by the planning contract itself."
---

## Context

The current SPA app host route is authenticated by design. Public curated-app
access should therefore be a parallel entry seam, not a hidden optional-auth
branch inside the authenticated host.

## Notes

- Keep the generic authenticated host semantics stable for existing deep links.
- The public host should stay curated-app-specific and fail closed when an app
  does not declare a public profile.
- This story is about entry/bootstrap boundaries, not guest persistence or
  anonymous helper APIs yet.

## Status Reconciliation (2026-04-30)

This story is now marked `done`. The SPA has a dedicated
`/public/apps/:appId` route, `PublicAppHostView` loads
`/api/v1/public/apps/{app_id}`, and authenticated `/apps/:appId` remains a
separate host route.
