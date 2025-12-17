---
type: story
id: ST-07-03
title: "OpenTelemetry tracing integration (OTLP export + propagation)"
status: ready
owners: "agents"
created: 2025-12-16
epic: "EPIC-07"
acceptance_criteria:
  - "Incoming requests accept W3C Trace Context headers and propagate context."
  - "Traces are exported via OTLP (configurable endpoint)."
  - "Structured logs include `trace_id` and `span_id` when a span is active."
  - "Key operations (tool execution + runner execution) are traced with useful span attributes."
---

## Context

Tracing is required for cross-service debugging once Skriptoteket participates in the HuleEdu platform. Logs should
automatically include trace context when available.

Reference: `docs/reference/reports/ref-external-observability-integration.md`.

## Scope

- Add OTEL SDK + exporter wiring behind env flags.
- Instrument FastAPI + key application operations (execution/runner).
- Document environment variables and validation steps in runbooks.

