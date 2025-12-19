---
type: adr
id: ADR-0019
title: "Observability: health, metrics, and tracing endpoints"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-16
---

## Context

HuleEdu’s platform expects every service to expose:

- `/healthz` with a standard JSON payload and dependency checks
- `/metrics` for Prometheus scraping
- OpenTelemetry tracing via OTLP export (Jaeger-compatible)

Reference guide: `docs/reference/reports/ref-external-observability-integration.md`.

Skriptoteket currently exposes `/health` only and does not expose Prometheus metrics or OpenTelemetry tracing.

## Decision

Implement standard observability endpoints and tracing:

1. **Health**: Add `GET /healthz` returning the HuleEdu standard payload and include a DB dependency check.
2. **Metrics**: Add `GET /metrics` using `prometheus_client` and record standard HTTP request metrics via middleware.
3. **Tracing**: Add OpenTelemetry SDK configuration and FastAPI + key-operation instrumentation with OTLP export.

## Consequences

- Enables Grafana dashboards and Alertmanager rules for uptime/error rate/latency.
- Adds runtime dependencies (prometheus client, OTEL SDK/exporter) and operational configuration (env vars, scrape jobs).
- Requires careful metric label design to avoid high cardinality and expensive queries.
