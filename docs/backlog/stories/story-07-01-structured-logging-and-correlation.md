---
type: story
id: ST-07-01
title: "Structured logging + correlation IDs (HuleEdu compatible)"
status: done
owners: "agents"
created: 2025-12-16
epic: "EPIC-07"
acceptance_criteria:
  - "Logs are structured JSON in production with required HuleEdu fields: timestamp, level, event, service.name, deployment.environment."
  - "`X-Correlation-ID` is accepted, echoed on responses, and available as `correlation_id` in logs."
  - "Error responses include `correlation_id` for JSON clients."
  - "Runner/execution lifecycle logs include run_id/tool_id/tool_version_id and context."
---

## Context

HuleEdu expects structured JSON logs suitable for Loki and cross-service debugging via correlation IDs. Skriptoteket also
needs strong debugging ergonomics around tool execution and runner lifecycle events.

Reference: `docs/reference/reports/ref-external-observability-integration.md`.

## Scope

- Add a single logging configuration entry point (structlog + stdlib integration).
- Add correlation middleware binding `correlation_id` via contextvars.
- Migrate web boundary logging (error handler + user routes) to structured events.
- Add lifecycle events for execution handler and Docker runner.

## Notes

- Avoid logging tool stdout/stderr/html (already persisted to DB); log metadata only.
- Include optional trace fields (`trace_id`, `span_id`) when OpenTelemetry is enabled.

