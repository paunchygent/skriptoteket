---
type: story
id: ST-17-01
title: "Grafana datasource verification"
status: done
owners: "agents"
created: 2025-12-26
updated: 2025-12-29
epic: "EPIC-17"
acceptance_criteria:
  - "Given the observability stack is running, when I check Grafana datasources via UI, then Prometheus shows 'Success' status"
  - "Given the observability stack is running, when I check Grafana datasources via UI, then Loki shows 'Success' status"
  - "Given the observability stack is running, when I check Grafana datasources via UI, then Jaeger shows 'Success' status"
  - "Given a log entry with trace_id in Loki, when I click 'View Trace', then I navigate to the corresponding trace in Jaeger"
  - "Given a trace in Jaeger, when I click 'View Logs', then I see correlated logs in Loki for that trace"
---

## Context

Datasources are already configured in `observability/grafana/provisioning/datasources/datasources.yaml` with:

- Prometheus (metrics, default datasource)
- Loki (logs, with derived fields for trace linking)
- Jaeger (traces, with tracesToLogsV2 and tracesToMetrics)

This story verifies the provisioned configuration works end-to-end in the deployed environment.

## Scope

1. Access Grafana at https://grafana.hemma.hule.education
2. Navigate to Configuration > Data Sources
3. Test each datasource connection
4. Verify log-to-trace correlation (Loki → Jaeger)
5. Verify trace-to-log correlation (Jaeger → Loki)

## Notes

- If any datasource fails, check container networking on `hule-network`
- Jaeger internal URL is `http://jaeger:16686` (container name resolution)
- Loki internal URL is `http://loki:3100`
- Prometheus internal URL is `http://prometheus:9090`

## Verification (2025-12-29)

- Grafana proxy checks returned `200` for Prometheus/Loki/Jaeger.
- Loki → Jaeger and Jaeger → Loki correlation wiring verified after pinning datasource UIDs (`prometheus`, `loki`, `jaeger`).
