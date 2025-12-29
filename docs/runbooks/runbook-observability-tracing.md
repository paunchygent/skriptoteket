---
type: runbook
id: RUN-observability-tracing
title: "Runbook: Observability Tracing (OpenTelemetry + Jaeger)"
status: active
owners: "olof"
created: 2025-12-29
updated: 2025-12-29
system: "skriptoteket"
---

Distributed tracing in Skriptoteket using OpenTelemetry with OTLP export to Jaeger.

## Access

- Jaeger UI: http://hemma.hule.education:16686

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_TRACING_ENABLED` | `false` | Enable tracing (explicit opt-in) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | OTLP collector endpoint (gRPC) |
| `SERVICE_VERSION` | from `APP_VERSION` | Service version in traces |
| `ENVIRONMENT` | `development` | Deployment environment |

## Local Jaeger Setup

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

## Traced Operations

| Operation | Span Name | Key Attributes |
|-----------|-----------|----------------|
| HTTP request | `{METHOD} {route}` | `http.method`, `http.route`, `http.status_code` |
| Tool execution | `execute_tool_version` | `tool.id`, `version.id`, `run.id`, `run.status` |
| Docker runner | `docker_runner.execute` | `run.id`, `run.context`, `run.status`, `run.duration_seconds` |

## Span Events (Docker Runner)

- `volume_created` - Docker volume created
- `container_started` - Container started
- `container_finished` - Container finished (includes `timed_out` attribute)
- `artifacts_extracted` - Artifacts extracted (includes `count` attribute)
