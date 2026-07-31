---
type: reference
id: REF-SKRIPT-GENERAL-huleedu-observability-integration-guide-PART-02
title: HuleEdu Observability Integration Guide — part 02
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: REF-SKRIPT-GENERAL-huleedu-observability-integration-guide
part: 2
---

```python
from quart import Blueprint, jsonify
from sqlalchemy import text

health_bp = Blueprint("health", __name__)

@health_bp.route("/healthz")
async def health_check():
    """Standardized health check endpoint."""
    checks = {"service_responsive": True, "dependencies_available": True}
    dependencies = {}
    overall_status = "healthy"

    # Check database
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        dependencies["database"] = {"status": "healthy"}
    except Exception as e:
        dependencies["database"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "degraded"
        checks["dependencies_available"] = False

    # Check other dependencies (Redis, Kafka, etc.)
    # ...

    status_code = 200 if overall_status == "healthy" else 503
    return jsonify({
        "service": settings.SERVICE_NAME,
        "status": overall_status,
        "message": f"Service is {overall_status}",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "checks": checks,
        "dependencies": dependencies,
    }), status_code
```

---

### 5. Metrics Endpoint

### Standard Metrics Exposure

All services expose `/metrics` for Prometheus scraping:

```python
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest, REGISTRY
from quart import Blueprint, Response

metrics_bp = Blueprint("metrics", __name__)

@metrics_bp.route("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    metrics_data = generate_latest(REGISTRY)
    return Response(metrics_data, content_type=CONTENT_TYPE_LATEST)
```

---

### 6. Infrastructure Integration

### Prometheus Scrape Configuration

Register your service in Prometheus config:

```yaml
### prometheus.yml
scrape_configs:
  - job_name: 'your_service'
    static_configs:
      - targets: ['your_service:8080']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### Loki/Promtail Log Collection

Logs are collected from Docker containers automatically. Ensure your service:

1. **Outputs to stdout/stderr** (no file logging required)
2. **Emits JSON format** (parsed by Promtail)
3. **Includes standard fields** (level, timestamp, service.name)

Promtail extracts and indexes:
- `level` → Label (for filtering: `{level="error"}`)
- `service` → Label (for filtering: `{service="your_service"}`)
- Other fields → Available via JSON parsing in queries

### Jaeger Trace Collection

Services send traces via OTLP gRPC:
- **Endpoint**: `http://jaeger:4317` (internal Docker network)
- **External UI**: `http://localhost:16686`

---

### 7. Alert Integration

### Standard Alert Rules

HuleEdu uses threshold-based alerting. Example alert:

```yaml
### prometheus/rules/your-service-alerts.yml
groups:
- name: YourServiceAlerts
  rules:
  - alert: ServiceDown
    expr: up{job="your_service"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "{{ $labels.job }} is down"
      description: "Service has been down for more than 1 minute."

  - alert: HighErrorRate
    expr: rate(your_service_http_requests_total{status_code=~"5.."}[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate in {{ $labels.job }}"
      description: "5xx error rate exceeds 10% over 5 minutes."
```

### Alertmanager Webhook Integration

Configure alertmanager to send notifications:

```yaml
### alertmanager.yml
receivers:
- name: 'your-team'
  webhook_configs:
  - url: 'https://your-notification-endpoint/webhook'
    send_resolved: true
```

---

### 8. Quick Start Checklist

### Minimum Requirements

- [ ] **JSON logging** with `timestamp`, `level`, `event`, `service.name`
- [ ] **`/healthz` endpoint** returning standard health response
- [ ] **`/metrics` endpoint** exposing Prometheus metrics
- [ ] **Correlation ID** propagation via `X-Correlation-ID` header

### Recommended Additions

- [ ] **OpenTelemetry tracing** with OTLP export
- [ ] **HTTP request metrics** (requests_total, request_duration_seconds)
- [ ] **Database metrics** (query_duration, connection_pool status)
- [ ] **Business metrics** for key operations

### Environment Variables

```bash
### Required
SERVICE_NAME=your_service
ENVIRONMENT=development|staging|production

### Logging
LOG_LEVEL=INFO|DEBUG|WARNING|ERROR
LOG_FORMAT=json|console

### Tracing
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317

### Optional: File logging
LOG_TO_FILE=false
LOG_FILE_PATH=/app/logs/your_service.log
LOG_MAX_BYTES=104857600
LOG_BACKUP_COUNT=10
```

---

### 9. Dependencies

### Python Packages

```txt
### Logging
structlog>=25.3.0

### Metrics
prometheus-client>=0.20.0

### Tracing
opentelemetry-api>=1.25.0
opentelemetry-sdk>=1.25.0
opentelemetry-exporter-otlp-proto-grpc>=1.25.0
opentelemetry-instrumentation>=0.46b0
```

### Docker Network

Services must connect to `huleedu_internal_network` for observability components:

```yaml
### docker-compose.yml
services:
  your_service:
    networks:
      - huleedu_internal_network
```

---

### 10. Observability Stack Ports Reference

| Service | Internal Port | External Port | Purpose |
|---------|--------------|---------------|---------|
| Prometheus | 9090 | 9091 | Metrics storage |
| Grafana | 3000 | 3000 | Dashboards |
| Jaeger UI | 16686 | 16686 | Trace visualization |
| Jaeger OTLP | 4317 | 4317 | Trace ingestion (gRPC) |
| Loki | 3100 | 3100 | Log aggregation |
| Alertmanager | 9093 | 9094 | Alert routing |

---

### Reference Implementation

See these HuleEdu services for complete examples:

- **File Service**: Simple HTTP service with health checks and metrics
- **Batch Orchestrator Service**: Complex service with database monitoring
- **LLM Provider Service**: Service with custom business metrics

---

*Last Updated: December 2024*

## Facts And Semantics

The source material below remains authoritative for this section.

## Decisions And Interpretation

The source material below remains authoritative for this section.
