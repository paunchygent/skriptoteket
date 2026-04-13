---
type: story
id: ST-28-10
title: "Auth outcome observability for realm cutover"
status: in_progress
owners: "agents"
created: 2026-04-11
updated: 2026-04-13
epic: "EPIC-28"
acceptance_criteria:
  - "Given local browser sessions are retired, when auth monitoring is restored, then no metric recreates `skriptoteket_active_sessions` from local session state."
  - "Given the Hule Education gateway authenticates browser users, when requests reach Skriptoteket, then metrics or logs distinguish signed-context verification success/failure, projection resolved, projection missing, and local RBAC denial."
  - "Given product identity realms are active, when operators inspect auth outcomes, then realm selection and Skriptoteket projection outcomes are visible without exposing sensitive identity data."
  - "Given bootstrap and lifecycle proof accounts are active, when operators inspect auth outcomes, then role-matrix proof and real-account lifecycle failures are distinguishable without exposing sensitive identity data."
  - "Given cross-app proof is run, when the operator runbook is reviewed, then it names the metrics/logs used to triage login, projection, lifecycle, and authorization failures."
dependencies: ["ST-28-06", "ST-28-09", "ST-28-11", "ST-28-12", "ST-28-04", "ADR-0083"]
---

## Context

`PR-0253` correctly removes local active-session metrics because Skriptoteket no
longer owns browser sessions. The new auth world still needs monitoring, but it
must observe the new boundaries: gateway auth, signed context, realm selection,
projection, and local RBAC.

This story should run after the realm-aware projection, bootstrap role matrix,
real lifecycle proof, and final cross-app proof lanes define the final events to
monitor.

## Notes

- Do not restore local browser-session gauges.
- Prefer low-cardinality counters and gauges that reflect product boundaries.
- Coordinate with the Hule Education gateway/identity observability story if it
  exists.

## PR Slices

- `PR-0264` opens this story as a planning/review-backed Skriptoteket-owned
  observability slice. It is limited to signed-context verification,
  app-continuation/projection outcomes, local RBAC decisions, and consumer-side
  runbook correlation. HuleEdu Gateway/session/lifecycle telemetry remains
  upstream-owned.
