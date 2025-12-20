---
id: "093-distributed-tracing"
type: "implementation"
created: 2025-12-20
scope: "backend"
---

# 093: Distributed Tracing

OpenTelemetry tracing with W3C Trace Context propagation.

## 1. Configuration

Tracing is opt-in via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_TRACING_ENABLED` | `false` | Enable tracing |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | OTLP gRPC endpoint |
| `SERVICE_NAME` | `skriptoteket` | Service name in traces |
| `SERVICE_VERSION` | from config | Version in traces |

## 2. Tracer Initialization

```python
# observability/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION

def configure_tracing(settings: Settings) -> None:
    if not settings.OTEL_TRACING_ENABLED:
        return

    resource = Resource.create({
        SERVICE_NAME: settings.SERVICE_NAME,
        SERVICE_VERSION: settings.SERVICE_VERSION,
        "deployment.environment": settings.ENVIRONMENT,
    })

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
```

## 3. Tracing Middleware

```python
# web/middleware/tracing.py
from opentelemetry import trace
from opentelemetry.propagate import extract
from opentelemetry.trace import SpanKind, Status, StatusCode

EXCLUDED_PATHS = frozenset({"/healthz", "/metrics", "/static"})

async def tracing_middleware(request: Request, call_next):
    path = request.url.path

    # Skip tracing for observability endpoints (reduces noise)
    if any(path.startswith(excluded) for excluded in EXCLUDED_PATHS):
        return await call_next(request)

    tracer = trace.get_tracer(__name__)

    # Extract parent context from incoming headers (W3C Trace Context)
    ctx = extract(request.headers)

    with tracer.start_as_current_span(
        f"{request.method} {_get_route_pattern(request)}",
        context=ctx,
        kind=SpanKind.SERVER,
    ) as span:
        # Set HTTP semantic attributes
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.route", _get_route_pattern(request))
        span.set_attribute("http.url", str(request.url))

        try:
            response = await call_next(request)
            span.set_attribute("http.status_code", response.status_code)

            if response.status_code >= 400:
                span.set_status(Status(StatusCode.ERROR))

            # Add trace headers to response
            span_ctx = span.get_span_context()
            if span_ctx.is_valid:
                response.headers["X-Trace-ID"] = format(span_ctx.trace_id, "032x")
                response.headers["X-Span-ID"] = format(span_ctx.span_id, "016x")

            return response

        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise
```

## 4. Creating Custom Spans

For business operations, create explicit spans:

```python
# application/scripting/handlers/execute_tool_version.py
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def handle(self, command: ExecuteToolVersionCommand):
    with tracer.start_as_current_span("execute_tool_version") as span:
        span.set_attribute("tool.id", str(command.tool_id))
        span.set_attribute("version.id", str(command.version_id))

        result = await self._runner.execute(...)

        span.set_attribute("run.id", str(result.run_id))
        span.set_attribute("run.status", result.status.value)
        return result
```

## 5. Span Events

Add events for significant moments within a span:

```python
# infrastructure/runner/docker_runner.py
with tracer.start_as_current_span("docker_runner.execute") as span:
    # ... create volume
    span.add_event("volume_created", {"volume_name": volume_name})

    # ... start container
    span.add_event("container_started", {"container_id": container.id})

    # ... wait for completion
    span.add_event("container_finished", {
        "exit_code": exit_code,
        "timed_out": timed_out,
    })
```

## 6. W3C Trace Context

Skriptoteket propagates trace context via the `traceparent` header:

```
traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01
             ^^ ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ^^^^^^^^^^^^^^^^ ^^
             |  |                                |                |
             |  trace-id (32 hex)                span-id (16 hex) flags
             version
```

Incoming requests with valid `traceparent` will continue the parent trace.

## 7. Response Headers

When tracing is enabled, responses include:

| Header | Format | Example |
|--------|--------|---------|
| `X-Trace-ID` | 32 hex chars | `a151c2883a22b6f2657ff644440d51f4` |
| `X-Span-ID` | 16 hex chars | `244558e85b1e41a1` |

## 8. Log Correlation

When tracing is enabled, logs include trace context:

```json
{
  "event": "Tool execution completed",
  "trace_id": "a151c2883a22b6f2657ff644440d51f4",
  "span_id": "244558e85b1e41a1",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

To find logs for a trace:
```bash
docker logs skriptoteket_web | grep "a151c2883a22b6f2657ff644440d51f4"
```

## 9. Excluded Endpoints

These paths are excluded from tracing to reduce noise:
- `/healthz` - High-frequency health checks
- `/metrics` - Prometheus scraping
- `/static` - Static file serving

## 10. Semantic Conventions

Follow OpenTelemetry semantic conventions:

| Attribute | Description |
|-----------|-------------|
| `http.method` | HTTP method (GET, POST, etc.) |
| `http.route` | Route pattern (`/tools/{id}`) |
| `http.status_code` | Response status code |
| `http.url` | Full request URL |
| `tool.id` | Tool UUID (business attribute) |
| `run.id` | Run UUID (business attribute) |

## References

- ADR-0019: Health, metrics, and tracing endpoints
- Runbook: `docs/runbooks/runbook-observability-logging.md`
