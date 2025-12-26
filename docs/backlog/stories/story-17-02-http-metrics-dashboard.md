---
type: story
id: ST-17-02
title: "HTTP metrics dashboard"
status: ready
owners: "agents"
created: 2025-12-26
epic: "EPIC-17"
dependencies:
  - "ST-17-01"
acceptance_criteria:
  - "Given the HTTP metrics dashboard exists, when I open it in Grafana, then I see panels for Request Rate, Error Rate, and Latency"
  - "Given the dashboard is loaded, when I select a time range, then all panels update with data from that range"
  - "Given the Request Rate panel, when I hover over the graph, then I see breakdown by endpoint (top 10)"
  - "Given the Error Rate panel, when errors exceed 5% of total requests, then the panel changes to warning color"
  - "Given the Latency panel, when P99 latency exceeds 1s, then the panel changes to warning color"
---

## Context

Skriptoteket exposes HTTP metrics via `/metrics`:

- `skriptoteket_http_requests_total` (Counter) - labels: method, endpoint, status_code
- `skriptoteket_http_request_duration_seconds` (Histogram) - labels: method, endpoint

This dashboard provides visibility into request traffic, error rates, and latency percentiles.

## Panels

| Panel | Type | Query |
|-------|------|-------|
| Request Rate | Time series | `rate(skriptoteket_http_requests_total[5m])` by endpoint |
| Error Rate | Gauge | `rate(skriptoteket_http_requests_total{status_code=~"4..\|5.."}[5m]) / rate(skriptoteket_http_requests_total[5m])` |
| Latency P50/P95/P99 | Time series | `histogram_quantile(0.99, rate(skriptoteket_http_request_duration_seconds_bucket[5m]))` |
| Status Code Distribution | Stacked bar | by status_code |
| Top Endpoints | Table | sorted by request count |

## Files

Create: `observability/grafana/provisioning/dashboards/skriptoteket-http-metrics.json`

Pattern: Follow `observability/grafana/provisioning/dashboards/skriptoteket-session-files.json`

## Notes

- Use route patterns (e.g., `/tools/{id}`) to avoid high cardinality
- Dashboard UID should be `skriptoteket-http-metrics` for stable linking
