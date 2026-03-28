---
type: story
id: ST-28-03
title: "Remove local auth ownership and regenerate client contracts"
status: ready
owners: "agents"
created: 2026-03-28
epic: "EPIC-28"
acceptance_criteria:
  - "Given Skriptoteket has cut over to the HuleEdu-owned browser session contract, when browser auth flows are audited, then Skriptoteket-local browser auth authority/routes/models are deleted rather than retained as a hidden bridge."
  - "Given the shared browser session contract is the new source of truth, when the frontend client types are regenerated, then auth-related OpenAPI/types align with the shared session endpoints and payloads."
  - "Given local auth ownership is removed, when future browser work is added, then it depends on the shared HuleEdu session contract rather than reintroducing app-local browser auth assumptions."
ui_impact: "Should be behaviorally neutral to users; this is a hard-break ownership cleanup."
dependencies: ["ADR-0076", "ST-28-01", "ST-28-02"]
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
