---
type: story
id: ST-07-05
title: "Deploy observability stack (Prometheus, Grafana, Jaeger, Loki)"
status: done
owners: "agents"
created: 2025-12-20
epic: "EPIC-07"
acceptance_criteria:
  - "Prometheus scrapes Skriptoteket metrics from /metrics endpoint."
  - "Grafana shows all three datasources (Prometheus, Loki, Jaeger) as healthy."
  - "Jaeger UI displays traces from Skriptoteket requests."
  - "Loki receives logs from Docker containers via Promtail."
  - "Log-to-trace correlation works in Grafana (clicking trace_id navigates to Jaeger)."
  - "Stack survives server reboot (restart policy: unless-stopped)."
---

## Context

EPIC-07 stories ST-07-01 through ST-07-04 implemented application-level observability. The application now exposes
metrics, health checks, and traces. This story deploys the infrastructure to collect and visualize this data.

Reference: `docs/reference/reports/ref-external-observability-integration.md`.

## Scope

- Create `compose.observability.yaml` with Prometheus, Grafana, Jaeger, Loki, Promtail.
- Create config files under `observability/` directory.
- Update `compose.prod.yaml` to enable tracing (`OTEL_TRACING_ENABLED=true`).
- Add PDM scripts for stack management (`obs-start`, `obs-stop`, etc.).
- Update runbook with deployment and troubleshooting instructions.
- Deploy to home server and verify all acceptance criteria.

## Files

- `compose.observability.yaml` (new)
- `observability/prometheus/prometheus.yml` (new)
- `observability/loki/loki-config.yaml` (new)
- `observability/promtail/promtail-config.yaml` (new)
- `observability/grafana/provisioning/datasources/datasources.yaml` (new)
- `compose.prod.yaml` (modified - add tracing env vars)
- `pyproject.toml` (modified - add obs-* scripts)
- `docs/runbooks/runbook-observability.md` (modified)
