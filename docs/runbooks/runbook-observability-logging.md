---
type: runbook
id: RUN-observability-logging
title: "Runbook: Observability (Logging + Correlation)"
status: active
owners: "olof"
created: 2025-12-16
system: "skriptoteket"
---

How to debug Skriptoteket using HuleEdu-compatible structured logs and correlation IDs.

Reference: `docs/reference/reports/ref-external-observability-integration.md`.

## Configuration

Environment variables:

- `SERVICE_NAME` (default: `skriptoteket`)
- `ENVIRONMENT` (default: `development`)
- `LOG_LEVEL` (default: `INFO`)
- `LOG_FORMAT` (`json` or `console`)

Recommended defaults:

- Local dev: `LOG_FORMAT=console`
- Production: `LOG_FORMAT=json`

## Correlation ID

Skriptoteket accepts `X-Correlation-ID` on incoming requests and echoes it on responses. The value is bound as
`correlation_id` for application logs emitted during request handling.

### Local example

```bash
CID="$(python -c 'import uuid; print(uuid.uuid4())')"
curl -i -H "X-Correlation-ID: ${CID}" http://127.0.0.1:8000/login
```

Search logs for the correlation id:

```bash
docker logs skriptoteket_web | rg "${CID}"
```

## JSON log shape (HuleEdu)

Required fields:

- `timestamp` (RFC 3339 / ISO 8601)
- `level` (`debug|info|warning|error|critical`)
- `event` (human-readable message)
- `service.name`
- `deployment.environment`

Optional fields (when available):

- `correlation_id`
- `trace_id`, `span_id` (once OpenTelemetry is enabled)

## Home server usage

```bash
# Follow logs
ssh hemma "docker logs -f skriptoteket_web"

# Filter by correlation id
ssh hemma "docker logs skriptoteket_web | rg '<correlation-id>'"
```

## Sensitive Data Policy

Skriptoteket handles school-related data. Observability must not become a data leakage vector.

### What MAY be logged

- User IDs, role names (e.g., `user`, `contributor`, `admin`)
- Tool IDs, tool version IDs, run IDs
- Request paths, methods, status codes
- Correlation IDs, trace IDs, span IDs
- Error types and non-sensitive error messages
- Timestamps and durations

### What MUST NOT be logged

- Passwords, tokens, secrets, API keys
- Email addresses (PII)
- Student names, personal data, school identifiers
- File contents from uploads
- Session cookies or bearer tokens
- Raw request/response bodies containing user data

### Automatic Redaction

The structlog configuration includes a redaction processor that automatically replaces values for sensitive keys with `[REDACTED]`. Keys matching these patterns are redacted (case-insensitive):

- `password`, `token`, `secret`
- `api_key`, `api-key`, `x-api-key`
- `authorization`, `credential`, `bearer`
- `cookie`, `session`

### Security Review Checklist

When adding new log statements, verify:

- [ ] No PII (emails, names, student data) in log events
- [ ] Sensitive data uses keys that trigger automatic redaction
- [ ] No raw request/response body logging
- [ ] Error messages don't expose internal system details
- [ ] File paths don't reveal user-specific information

## Health Check Endpoint

`GET /healthz` returns HuleEdu-standard JSON payload:

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

Docker compose uses `/healthz` for container health checks. Database connectivity is verified with a 2-second timeout.

### Local example

```bash
curl -s http://127.0.0.1:8000/healthz | jq
```

### Production example

```bash
ssh hemma "curl -s http://localhost:8000/healthz" | jq
```

## Prometheus Metrics Endpoint

`GET /metrics` exposes Prometheus-compatible metrics for scraping.

### Metrics exposed

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `skriptoteket_http_requests_total` | Counter | method, endpoint, status_code | Total HTTP requests |
| `skriptoteket_http_request_duration_seconds` | Histogram | method, endpoint | Request latency |
| `skriptoteket_session_files_bytes_total` | Gauge | - | Total bytes of stored session files |
| `skriptoteket_session_files_count` | Gauge | - | Count of stored session files |

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

## OpenTelemetry Tracing

Skriptoteket supports distributed tracing via OpenTelemetry with OTLP export to Jaeger.

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_TRACING_ENABLED` | `false` | Enable tracing (explicit opt-in) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | OTLP collector endpoint (gRPC) |
| `SERVICE_VERSION` | from `APP_VERSION` | Service version in traces |
| `ENVIRONMENT` | `development` | Deployment environment |

### Local Jaeger setup

```bash
# Start Jaeger all-in-one (OTLP + UI)
docker run --rm -d --name jaeger \
  -p 4317:4317 \
  -p 16686:16686 \
  jaegertracing/all-in-one:latest

# Enable tracing in .env
export OTEL_TRACING_ENABLED=true
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Run dev server
pdm run dev

# View traces at http://localhost:16686
```

### Traced operations

| Operation | Span Name | Key Attributes |
|-----------|-----------|----------------|
| HTTP request | `{METHOD} {route}` | `http.method`, `http.route`, `http.status_code` |
| Tool execution | `execute_tool_version` | `tool.id`, `version.id`, `run.id`, `run.status` |
| Docker runner | `docker_runner.execute` | `run.id`, `run.context`, `run.status`, `run.duration_seconds` |

### Span events (Docker runner)

- `volume_created` - Docker volume created
- `container_started` - Container started
- `container_finished` - Container finished (includes `timed_out` attribute)
- `artifacts_extracted` - Artifacts extracted (includes `count` attribute)

### Response headers

Tracing middleware adds headers to responses for debugging:

- `X-Trace-ID` - 32-char hex trace ID
- `X-Span-ID` - 16-char hex span ID

### Log correlation

When tracing is enabled, structured logs include `trace_id` and `span_id` fields. To find logs for a trace:

```bash
# Get trace ID from response header
curl -i http://127.0.0.1:8000/tools

# Search logs by trace ID
docker logs skriptoteket_web | rg "<trace-id>"
```

### W3C Trace Context

Skriptoteket accepts `traceparent` header for distributed tracing:

```bash
curl -H "traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01" \
  http://127.0.0.1:8000/tools
```

## Observability Stack Deployment

The observability stack runs separately from the application via `compose.observability.yaml`.

### Stack Components

| Service | Port (External) | Port (Internal) | Purpose |
|---------|-----------------|-----------------|---------|
| Prometheus | 9091 | 9090 | Metrics collection |
| Grafana | 3000 | 3000 | Dashboards |
| Jaeger | 16686 | 16686 | Trace visualization |
| Jaeger OTLP | 4317 | 4317 | Trace ingestion (gRPC) |
| Loki | 3100 | 3100 | Log aggregation |
| Promtail | - | 9080 | Log collection agent |

### Deployment

```bash
# Start observability stack
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.observability.yaml up -d"

# Check status
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.observability.yaml ps"

# View logs
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.observability.yaml logs -f"

# Stop stack
ssh hemma "cd ~/apps/skriptoteket && docker compose -f compose.observability.yaml down"
```

### PDM Scripts

```bash
pdm run obs-start    # Start stack
pdm run obs-stop     # Stop stack
pdm run obs-restart  # Restart stack
pdm run obs-logs     # Follow logs
pdm run obs-status   # Check status
```

### Access URLs

| Service | URL |
|---------|-----|
| Grafana | http://hemma.hule.education:3000 |
| Prometheus | http://hemma.hule.education:9091 |
| Jaeger UI | http://hemma.hule.education:16686 |

### Grafana Credentials

- **Admin user**: `admin`
- **Admin password**: Set via `GRAFANA_ADMIN_PASSWORD` environment variable (default: `admin`)
- **Anonymous access**: Enabled (Viewer role)

### Enable Tracing in Application

After deploying the observability stack, redeploy the application to enable tracing:

```bash
ssh hemma "cd ~/apps/skriptoteket && git pull && docker compose -f compose.prod.yaml up -d --build"
```

### Troubleshooting

#### Prometheus not scraping metrics

```bash
# Check Prometheus targets
curl http://hemma.hule.education:9091/api/v1/targets

# Verify skriptoteket-web is reachable from prometheus
ssh hemma "docker exec prometheus wget -qO- http://skriptoteket-web:8000/metrics | head -20"
```

#### Loki not receiving logs

```bash
# Check Promtail status
ssh hemma "docker logs promtail --tail 50"

# Verify Loki is ready
ssh hemma "docker exec loki wget -qO- http://localhost:3100/ready"
```

#### Jaeger not receiving traces

```bash
# Verify OTEL_TRACING_ENABLED is set
ssh hemma "docker exec skriptoteket-web printenv | grep OTEL"

# Make a request and check for trace headers
curl -i https://skriptoteket.hule.education/healthz
# Look for X-Trace-ID header in response
```

#### Grafana datasource errors

```bash
# Check Grafana logs
ssh hemma "docker logs grafana --tail 50"

# Verify network connectivity from Grafana
ssh hemma "docker exec grafana wget -qO- http://prometheus:9090/-/healthy"
ssh hemma "docker exec grafana wget -qO- http://loki:3100/ready"
```

### Data Retention

| Component | Retention | Configuration |
|-----------|-----------|---------------|
| Prometheus | 30 days | `--storage.tsdb.retention.time=30d` |
| Loki | 30 days | `limits_config.retention_period: 30d` |
| Jaeger | In-memory | Default (restart clears data) |
| Grafana | Persistent | Volume: `grafana_data` |

### Volume Locations

All data is stored in Docker named volumes:

- `prometheus_data` - Prometheus TSDB
- `loki_data` - Loki chunks and indices
- `promtail_positions` - Promtail file positions
- `grafana_data` - Grafana dashboards and settings
