---
type: story
id: ST-11-13
title: "Cutover + deletion + E2E"
status: ready
owners: "agents"
created: 2025-12-21
epic: "EPIC-11"
acceptance_criteria:
  - "Given the SPA has reached route parity, when cutover happens, then legacy templates/HTMX assets and page routes are removed and all routes are served by the SPA without redirects"
  - "Given critical flows are automated, when running Playwright E2E, then login, browse, run tool, and admin/editor paths pass against the SPA"
ui_impact: "Completes the migration and removes legacy UI code paths."
dependencies: ["ADR-0027", "ST-11-03", "ST-11-06", "ST-11-07", "ST-11-11", "ST-11-12"]
---

## Context

This is the final switch: delete legacy UI surfaces and validate with E2E before shipping.
