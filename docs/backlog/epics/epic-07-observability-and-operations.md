---
type: epic
id: EPIC-07
title: "Observability and operations integration"
status: active
owners: "agents"
created: 2025-12-16
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

- ST-07-01: Structured logging + correlation IDs (HuleEdu compatible)
- ST-07-02: Standard `/healthz` and Prometheus `/metrics` endpoints
- ST-07-03: OpenTelemetry tracing integration (OTLP export + propagation)
- ST-07-04: Logging redaction + sensitive data policy

## Risks

- Logging PII/secrets (mitigate: redaction processor + policy + review checks).
- High log volume/noise (mitigate: event taxonomy + log levels + sampling where needed).
- Divergence from HuleEdu semantics (mitigate: ADR-backed contract + reference guide).

## Dependencies

- HuleEdu observability stack (Loki/Promtail, Prometheus/Grafana, Jaeger).
- Agreement on service naming (`service.name`) and environments (`deployment.environment`).

