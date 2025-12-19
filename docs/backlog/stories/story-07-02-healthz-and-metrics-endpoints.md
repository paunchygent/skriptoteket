---
type: story
id: ST-07-02
title: "Standard /healthz and Prometheus /metrics endpoints"
status: done
owners: "agents"
created: 2025-12-16
epic: "EPIC-07"
ui_impact: "None (new endpoints only)."
data_impact: "None."
acceptance_criteria:
  - "`GET /healthz` returns the HuleEdu standard JSON payload including service, status, version, environment, checks, and dependencies."
  - "Docker/compose healthchecks use `/healthz` (remove `/health` to avoid parallel paths)."
  - "`GET /metrics` exposes Prometheus metrics."
  - "HTTP middleware records request count + duration with HuleEdu naming conventions."
---

## Context

Operators need standard health checks and metrics for alerting/dashboards. The observability guide defines payload shape
for `/healthz` and conventions for Prometheus metrics.

Reference: `docs/reference/reports/ref-external-observability-integration.md`.

## Scope

- Implement `/healthz` and wire DB dependency checks.
- Implement `/metrics` endpoint and HTTP middleware metrics.
- Update compose healthcheck + runbooks.

## Risks

- Metrics cardinality (avoid per-user labels; prefer route patterns).
