---
type: adr
id: ADR-0018
title: "Observability: structured logging and correlation IDs (HuleEdu compatible)"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-16
---

## Context

Skriptoteket will integrate into HuleEdu, which standardizes on:

- Structlog JSON logs shipped to Loki (via Docker/Promtail)
- Correlation across services via `X-Correlation-ID`
- Optional OpenTelemetry trace context (`trace_id`, `span_id`)

Reference guide: `docs/reference/reports/ref-external-observability-integration.md`.

The project previously relied on basic stdlib logging configuration and had limited correlation and lifecycle visibility
around tool execution and Docker runner operations.

## Decision

Adopt HuleEdu-compatible structured logging and correlation IDs:

1. **Logging library**: Use `structlog` with stdlib integration (single configuration entry point).
2. **Format**:
   - Production emits JSON logs suitable for Loki ingestion.
   - Development may use console rendering for readability.
3. **Required fields** (always present):
   - `timestamp`, `level`, `event`, `service.name`, `deployment.environment`
4. **Correlation**:
   - Accept `X-Correlation-ID` on inbound requests and echo it on responses.
   - Bind `correlation_id` via `structlog.contextvars` so all logs within the request include it.
5. **Uvicorn compatibility**:
   - Configure stdlib root handler/formatter so uvicorn logs follow the same JSON format.
6. **Trace context (optional)**:
   - If OpenTelemetry is enabled, add `trace_id`/`span_id` to logs from the active span.

Implementation:

- Logging configuration: `src/skriptoteket/observability/logging.py`
- Correlation middleware: `src/skriptoteket/web/middleware/correlation.py`
- Settings/env: `src/skriptoteket/config.py`, `.env.example`, `.env.example.prod`

## Consequences

- Logs become queryable by `service.name`, `deployment.environment`, `correlation_id` (and later `trace_id`) in Loki.
- Exception debugging improves via consistent callsite fields and structured context.
- Requires discipline to avoid logging PII/secrets; follow-up work adds redaction + policy (ST-07-04).
