---
type: runbook
id: RUN-observability-grafana
title: "Runbook: Observability Grafana"
status: active
owners: "olof"
created: 2025-12-29
updated: 2026-01-01
system: "skriptoteket"
---

Grafana dashboards and data sources for Skriptoteket.

## Access

- URL: https://grafana.hemma.hule.education
- Credentials: stored in `~/apps/skriptoteket/.env` on the server.

## Datasource Verification

Verify that these are "Success" in Grafana → Connections → Data sources:

- Prometheus
- Loki
- Jaeger

If a datasource is failing, confirm the observability stack is running; see
`docs/runbooks/runbook-home-server.md` (Observability section).

### Correlation links (logs ↔ traces)

Cross-links rely on the provisioned configuration in `observability/grafana/provisioning/datasources/datasources.yaml`:

- Loki derived field extracts `"trace_id"` from JSON logs and links to the Jaeger datasource.
- Jaeger `tracesToLogsV2` links traces back to Loki.

**Important:** datasource UIDs must remain stable for these links. We pin:

- Prometheus: `uid: prometheus`
- Loki: `uid: loki`
- Jaeger: `uid: jaeger`

## Dashboard Locations (Provisioned)

Dashboards are stored in the repo at:

- `observability/grafana/provisioning/dashboards/`

Known dashboards:

- `skriptoteket-session-files.json`
- `skriptoteket-user-activity.json`
- `skriptoteket-http-metrics.json`
- `skriptoteket-nginx-proxy-security.json`

## Panel Patterns

- Use route template labels (e.g., `/tools/{id}`) to avoid high-cardinality series.
- Prefer `rate()` + `histogram_quantile()` for latency panels.
- Pair error-rate panels with links to logs (Loki) and traces (Jaeger).

## Log Explore (Loki)

Use Grafana Explore to filter logs by `correlation_id` and `service.name=skriptoteket`.
See `docs/runbooks/runbook-observability-logging.md` for correlation ID handling.
