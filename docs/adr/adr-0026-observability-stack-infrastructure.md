---
type: adr
id: ADR-0026
title: "Observability stack infrastructure (Prometheus, Grafana, Jaeger, Loki)"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-20
---

## Context

EPIC-07 implemented application-level observability (structured logging, metrics endpoints, OpenTelemetry tracing). The
application now exposes `/metrics` and `/healthz` endpoints and can export traces via OTLP. However, no monitoring
infrastructure exists on the home server to collect, store, and visualize this data.

Reference: `docs/reference/reports/ref-external-observability-integration.md`.

## Decision

Deploy a complete observability stack on the home server as a separate Docker Compose file (`compose.observability.yaml`)
with independent lifecycle from the application:

| Component | Purpose | Ports |
|-----------|---------|-------|
| Prometheus | Metrics collection and storage | 9091 (external), 9090 (internal) |
| Grafana | Dashboards and visualization | 3000 |
| Jaeger | Distributed tracing backend | 16686 (UI), 4317 (OTLP) |
| Loki | Log aggregation | 3100 |
| Promtail | Docker log shipping to Loki | internal only |

Design principles:

1. **Separate lifecycle**: Observability stack can be started/stopped independently from application.
2. **Shared network**: All services connect to `hule-network` for internal communication.
3. **Persistent storage**: Named volumes for Prometheus, Loki, and Grafana data.
4. **Auto-provisioning**: Grafana datasources are provisioned automatically via YAML config.
5. **Log-to-trace correlation**: Grafana links logs to traces via `trace_id` field.

## Consequences

- Enables real-time monitoring, alerting, and debugging for production issues.
- Adds infrastructure complexity (5 additional containers, ~500MB memory footprint).
- Data retention: 30 days for metrics and logs; traces are in-memory only (lost on restart).
- Future HuleEdu integration: simply point env vars to HuleEdu's endpoints instead of local stack.
