---
type: runbook
id: RUN-observability
title: "Runbook: Observability Overview"
status: active
owners: "olof"
created: 2025-12-29
updated: 2025-12-29
system: "skriptoteket"
---

Entry point for observability in Skriptoteket. This runbook links to focused guides for logging, metrics, tracing, and
Grafana usage.

Reference: `docs/reference/reports/ref-external-observability-integration.md`.

## Access (Home Server)

| Service | URL | Notes |
|---------|-----|-------|
| Grafana | https://grafana.hemma.hule.education | Credentials in `~/apps/skriptoteket/.env` |
| Prometheus | https://prometheus.hemma.hule.education | Basic auth password in `~/apps/skriptoteket/.env` |
| Jaeger | https://jaeger.hemma.hule.education | Basic auth (user `admin`, password `JAEGER_BASIC_AUTH_PASSWORD`) |

For container lifecycle (start/stop/restart), see `docs/runbooks/runbook-home-server.md`.

## Triage Flow (Fast Path)

1) **Health check**: confirm `/healthz` is responsive.
2) **Metrics**: check request rate/latency and session file gauges.
3) **Logs**: filter by correlation ID and error code.
4) **Trace**: if enabled, jump to Jaeger and inspect spans.

## Runbooks

- Logging + correlation: `docs/runbooks/runbook-observability-logging.md`
- Metrics + Prometheus: `docs/runbooks/runbook-observability-metrics.md`
- Grafana dashboards + data sources: `docs/runbooks/runbook-observability-grafana.md`
- Tracing + Jaeger: `docs/runbooks/runbook-observability-tracing.md`
