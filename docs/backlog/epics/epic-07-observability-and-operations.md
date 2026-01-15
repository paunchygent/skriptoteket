---
type: epic
id: EPIC-07
title: "Observability and operations integration"
status: active
owners: "agents"
created: 2025-12-16
updated: 2026-01-15
outcome: "Skriptoteket is operable in production with HuleEdu-compatible logs, correlation, and a clear path to metrics + traces."
---

## Scope

- **Structured logging** aligned with HuleEdu conventions (JSON, required fields, consistent keys).
- **Correlation ID** propagation via `X-Correlation-ID` across requests and background/runner work.
- **Operational endpoints**: `/healthz` and `/metrics`.
- **Tracing**: OpenTelemetry propagation and OTLP export so logs include `trace_id`/`span_id`.
- **Safety**: explicit logging policy + redaction guardrails (avoid secrets/PII).
- **Runbooks** for operators (local + home server).

## Stories

- [ST-07-01: Structured logging + correlation IDs (HuleEdu compatible)](../stories/story-07-01-structured-logging-and-correlation.md) (done)
- [ST-07-02: Standard `/healthz` and Prometheus `/metrics` endpoints](../stories/story-07-02-healthz-and-metrics-endpoints.md) (done)
- [ST-07-03: OpenTelemetry tracing integration (OTLP export + propagation)](../stories/story-07-03-opentelemetry-tracing.md) (done)
- [ST-07-04: Logging redaction + sensitive data policy](../stories/story-07-04-logging-redaction-and-policy.md) (done)
- [ST-07-05: Deploy observability stack (Prometheus, Grafana, Jaeger, Loki)](../stories/story-07-05-observability-stack-deployment.md) (done)
- [ST-07-06: ASGI correlation middleware so access logs include correlation_id](../stories/story-07-06-asgi-correlation-middleware.md) (ready)

Note: EPIC-07 was previously marked `done`, but is reopened for ST-07-06 (access-log correlation for successful and streaming requests).

## Risks

- Logging PII/secrets (mitigate: redaction processor + policy + review checks).
- High log volume/noise (mitigate: event taxonomy + log levels + sampling where needed).
- Divergence from HuleEdu semantics (mitigate: ADR-backed contract + reference guide).

## Dependencies

- HuleEdu observability stack (Loki/Promtail, Prometheus/Grafana, Jaeger).
- Agreement on service naming (`service.name`) and environments (`deployment.environment`).
