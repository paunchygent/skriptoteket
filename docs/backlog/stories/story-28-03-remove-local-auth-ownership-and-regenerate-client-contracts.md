---
type: story
id: ST-28-03
title: "Remove local auth ownership and regenerate client contracts"
status: done
owners: "agents"
created: 2026-03-28
updated: 2026-04-12
epic: "EPIC-28"
acceptance_criteria:
  - "Given Skriptoteket has cut over to the HuleEdu-owned browser session contract, when browser auth flows are audited, then Skriptoteket-local browser auth authority/routes/models are deleted rather than retained as a hidden bridge."
  - "Given the shared browser session contract is the new source of truth, when the frontend client types are regenerated, then auth-related OpenAPI/types align with the shared session endpoints and payloads."
  - "Given local auth ownership is removed, when future browser work is added, then it depends on the shared HuleEdu session contract rather than reintroducing app-local browser auth assumptions."
ui_impact: "Should be behaviorally neutral to users; this is a hard-break ownership cleanup."
dependencies: ["ADR-0076", "ST-28-05", "ST-28-01", "ST-28-02"]
---

## Context

The cutover should end with one browser auth authority, not a compatibility bridge. Once the
frontend and modal flow consume the shared HuleEdu contract successfully, Skriptoteket must delete
its old local browser-auth ownership surfaces and regenerate client contracts against the new
shared endpoints.

## Notes

- This is intentionally a hard break.
- Retaining local browser auth routes "just in case" would violate the no-bridge constraint.
- Internal service-level authorization checks may still exist, but browser auth ownership must not.

## Implementation Summary (as of 2026-04-12)

`ST-28-03` is done through the approved `PR-0253` closeout. The implementation deletes the local
auth router/dependencies, removes local
login/logout/current-user/session repository runtime bindings, rewires browser app APIs to signed
HuleEdu-derived `require_app_*` dependencies, regenerates OpenAPI/frontend types without local auth
paths, replaces the SPA login form with a HuleEdu handoff, and drops the `sessions` table through
migration `c1d2e3f4a5b6` while keeping `tool_sessions` and app-local RBAC roles separate.

The retained review findings are closed in `REV-PR-0253`: remaining zombie browser-session contract
surfaces were removed, missing HuleEdu projections route to deliberate provisioning-required UX,
the live proof exercises the browser `/api` edge through a test gateway injector, docs/rules no
longer advertise removed local password-form smoke commands, and the product identity realm
correction is preserved for `ADR-0083` / `ST-28-06` through `ST-28-10`.
