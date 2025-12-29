---
type: runbook
id: RUN-observability-metrics
title: "Runbook: Observability Metrics (Prometheus)"
status: active
owners: "olof"
created: 2025-12-29
updated: 2025-12-29
system: "skriptoteket"
---

Metrics and health endpoints exposed by Skriptoteket, plus Prometheus scrape guidance.

## Health Check Endpoint

`GET /healthz` returns HuleEdu-standard JSON:

```json
{
  "service": "skriptoteket",
  "status": "healthy|degraded|unhealthy",
  "message": "Service is healthy",
  "version": "0.1.0",
  "environment": "production",
  "checks": {
    "service_responsive": true,
    "dependencies_available": true
  },
  "dependencies": {
    "database": {"status": "healthy"}
  }
}
```

Response codes:

- `200 OK` - Service is healthy
- `503 Service Unavailable` - Service is degraded/unhealthy

Local example:

```bash
curl -s http://127.0.0.1:8000/healthz | jq
```

Production example:

```bash
ssh hemma "curl -s http://localhost:8000/healthz" | jq
```

## Prometheus Metrics Endpoint

`GET /metrics` exposes Prometheus metrics for scraping.

### Metrics exposed

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `skriptoteket_http_requests_total` | Counter | method, endpoint, status_code | Total HTTP requests |
| `skriptoteket_http_request_duration_seconds` | Histogram | method, endpoint | Request latency |
| `skriptoteket_session_files_bytes_total` | Gauge | - | Total bytes of stored session files |
| `skriptoteket_session_files_count` | Gauge | - | Count of stored session files |
| `skriptoteket_active_sessions` | Gauge | - | Current count of active user sessions |
| `skriptoteket_logins_total` | Counter | status | Login attempts (success/failure) |
| `skriptoteket_users_by_role` | Gauge | role | Active users by role |

Labels use route patterns (e.g., `/tools/{id}`) to avoid high cardinality.

Session file metrics are computed at scrape time by scanning `ARTIFACTS_ROOT/sessions/` (excluding `meta.json`).

### Local example

```bash
curl -s http://127.0.0.1:8000/metrics | head -50
```

### Prometheus scrape config

```yaml
scrape_configs:
  - job_name: 'skriptoteket'
    static_configs:
      - targets: ['skriptoteket-web:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### PromQL snippets

```promql
# Session files size (MiB)
skriptoteket_session_files_bytes_total / 1024 / 1024

# Session files count
skriptoteket_session_files_count

# 95th percentile latency
histogram_quantile(0.95, sum by (le) (rate(skriptoteket_http_request_duration_seconds_bucket[5m])))
```

Dashboards and data source verification live in `docs/runbooks/runbook-observability-grafana.md`.
