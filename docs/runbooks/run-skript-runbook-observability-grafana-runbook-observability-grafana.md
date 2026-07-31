---
type: runbook
id: RUN-SKRIPT-runbook-observability-grafana
title: 'Runbook: Observability Grafana'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
retired_ids:
- RUN-observability-grafana
summary: 'Runbook: Observability Grafana'
system: skriptoteket
---

## Trigger

Grafana dashboards and data sources for Skriptoteket.

## Preconditions

No separate preconditions is stated in the source.

## Steps

No separate steps is stated in the source.

## Expected Results


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

## Stop Conditions

No separate stop conditions is stated in the source.

## Rollback

No separate rollback is stated in the source.

### Source: Access


- URL: https://grafana.hemma.hule.education
- Credentials: stored in `~/apps/skriptoteket/.env` on the server.

### Source: Dashboard Locations (Provisioned)


Dashboards are stored in the repo at:

- `observability/grafana/provisioning/dashboards/`

Known dashboards:

- `skriptoteket-session-files.json`
- `skriptoteket-user-activity.json`
- `skriptoteket-http-metrics.json`
- `skriptoteket-nginx-proxy-security.json`

### Source: Panel Patterns


- Use route template labels (e.g., `/tools/{id}`) to avoid high-cardinality series.
- Prefer `rate()` + `histogram_quantile()` for latency panels.
- Pair error-rate panels with links to logs (Loki) and traces (Jaeger).

### Source: Log Explore (Loki)


Use Grafana Explore to filter logs by `correlation_id` and `service.name=skriptoteket`.
See `docs/runbooks/runbook-observability-logging.md` for correlation ID handling.
