---
id: "090-observability-index"
type: "standards"
created: 2025-12-20
scope: "all"
---

# 090: Observability Standards Index

HuleEdu-compatible observability patterns. All services MUST implement these standards for production deployment.

## Child Rules

| Rule | Scope | Description |
|------|-------|-------------|
| [091-structured-logging.md](091-structured-logging.md) | Backend | JSON logging, correlation IDs, log levels |
| [092-health-and-metrics.md](092-health-and-metrics.md) | Backend | /healthz, /metrics, Prometheus naming |
| [093-distributed-tracing.md](093-distributed-tracing.md) | Backend | OpenTelemetry, spans, W3C Trace Context |
| [094-observability-infrastructure.md](094-observability-infrastructure.md) | DevOps | Stack deployment, Grafana, troubleshooting |

## Quick Reference

### Required Endpoints

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `/healthz` | Health check | JSON with status, dependencies |
| `/metrics` | Prometheus scrape | OpenMetrics format |

### Required Headers

| Header | Direction | Description |
|--------|-----------|-------------|
| `X-Correlation-ID` | Request/Response | Request tracking (UUID) |
| `X-Trace-ID` | Response | Distributed trace ID (32 hex chars) |
| `X-Span-ID` | Response | Current span ID (16 hex chars) |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_NAME` | `skriptoteket` | Service identifier in logs/traces |
| `ENVIRONMENT` | `development` | Deployment environment |
| `LOG_LEVEL` | `INFO` | Minimum log level |
| `LOG_FORMAT` | `console` | `json` for production |
| `OTEL_TRACING_ENABLED` | `false` | Enable distributed tracing |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | Jaeger OTLP endpoint |

## References

- ADR-0018: Structured logging and correlation
- ADR-0019: Health, metrics, and tracing endpoints
- ADR-0026: Observability stack infrastructure
- Runbook: `docs/runbooks/runbook-observability-logging.md`
- Integration guide: `docs/reference/reports/ref-external-observability-integration.md`
