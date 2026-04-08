---
type: story
id: ST-28-04
title: "Cross-app auth cutover smoke and operator runbook proof"
status: ready
owners: "agents"
created: 2026-03-28
updated: 2026-04-08
epic: "EPIC-28"
acceptance_criteria:
  - "Given the cutover is live, when a user starts auth from Skriptoteket through the canonical `/auth/login` entry contract or its equivalent HuleEdu-owned top-level handoff, then a HuleEdu-owned session is created and the same browser can open HuleEdu already authenticated."
  - "Given the shared browser session is active, when Skriptoteket performs a CSRF-protected write, then the request succeeds through the shared session + CSRF contract."
  - "Given a user logs out from either app, when the browser state refreshes, then both Skriptoteket and HuleEdu are logged out."
  - "Given the shared browser session cutover ships, when operator proof is reviewed, then HuleEdu teacher smoke and a dedicated Skriptoteket Playwright auth-cutover smoke are both green and documented in the runbook."
ui_impact: "Adds explicit cross-app auth proof and operator verification guidance."
dependencies: ["ADR-0076", "ST-28-05", "ST-28-01", "ST-28-02", "ST-28-03"]
---

## Context

This cutover is not complete when unit tests pass. We need one explicit joint proof lane covering:

- auth entry via the canonical `/auth/login` contract or an equivalent top-level HuleEdu-owned handoff
- protected-route bootstrap
- CSRF-protected write behavior
- logout invalidation across both apps

## Notes

- Add one dedicated Playwright auth-cutover smoke for Skriptoteket.
- Update the operator runbook with the exact public proof steps and failure interpretation.
- Do not certify the superseded modal-first auth-entry seam as the target contract for this lane.
- This story remains blocked on the preceding HuleEdu session-authority tranches shipping first.
