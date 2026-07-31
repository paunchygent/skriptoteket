---
type: reference
id: REF-SKRIPT-RESEARCH-observability-correlation-trace-asgi-middleware-structlog-context-opentelemetry-spans-jaeger-loki-grafana
title: 'Observability Correlation Trace: ASGI Middleware → Structlog Context → OpenTelemetry
  Spans → Jaeger/Loki/Grafana'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: research
summary: 'Observability Correlation Trace: ASGI Middleware → Structlog Context → OpenTelemetry
  Spans → Jaeger/Loki/Grafana'
---

## Research Purpose And Boundary


Maps the complete correlation flow from HTTP request through the observability stack, showing how correlation IDs and trace context propagate through middleware, logging processors, OpenTelemetry spans, and infrastructure processing.

## Evidence And Sources

No separate evidence and sources is stated in the source.

### Source: Quick Index (Code + Docs)


### Web Middleware

- **Correlation Middleware**: `src/skriptoteket/web/middleware/correlation.py`
- **Tracing Middleware**: `src/skriptoteket/web/middleware/tracing.py`

### Infrastructure & Config

- **Logging Pipeline**: `src/skriptoteket/observability/logging.py`
- **Tracing Setup**: `src/skriptoteket/observability/tracing.py`
- **Promtail Config**: `observability/promtail/promtail-config.yaml`
- **Grafana Datasources**: `observability/grafana/provisioning/datasources/datasources.yaml`

---

### Source: Execution Flows


### 1. HTTP Request Correlation Processing

Web layer correlation ID extraction, binding, and response injection.

```text
HTTP Request Correlation Processing
├── CorrelationMiddleware.__call__() entry <-- correlation.py:41
│   ├── Extract headers from ASGI scope <-- 1a
│   ├── Parse/validate X-Correlation-ID <-- 1b
│   ├── Store in request.state for FastAPI <-- 1c
│   ├── Clear any existing contextvars <-- 1d
│   ├── Bind correlation_id to structlog <-- 1e
│   └── Wrap send() for response injection <-- correlation.py:57
│       └── Inject X-Correlation-ID header <-- correlation.py:61
└── Request lifecycle completion <-- correlation.py:66
    └── Clear contextvars in finally block <-- correlation.py:69
```

### 2. Structured Logging with Correlation

How structlog processes correlation context and trace information.

```text
Structured Logging Pipeline
├── configure_logging() setup <-- logging.py:38
│   ├── shared_processors array <-- logging.py:52
│   │   ├── merge_contextvars <-- 2a
│   │   ├── _add_trace_context() <-- logging.py:23
│   │   │   ├── get_current_span() <-- 2b
│   │   │   ├── format trace_id <-- 2c
│   │   │   └── format span_id <-- 2d
│   │   └── other processors... <-- logging.py:54
│   └── structlog.configure() <-- logging.py:102
└── Log emission during request <-- correlation.py:52
    └── Processors apply context <-- logging.py:53
        └── JSON output with fields <-- logging.py:72
```

### 3. OpenTelemetry Tracing with Correlation

How tracing middleware creates spans enriched with correlation data.

```text
HTTP Request Tracing Flow
├── tracing_middleware() entry point <-- tracing.py:39
│   ├── Extract W3C Trace Context <-- 3a
│   ├── Create Request Span <-- 3b
│   │   ├── Set HTTP attributes <-- tracing.py:63
│   │   ├── Enrich with Correlation <-- 3c
│   │   ├── Execute request handler <-- tracing.py:72
│   │   └── Set response status <-- tracing.py:75
│   └── Inject Trace Headers <-- 3d
└── OpenTelemetry Export Pipeline <-- tracing.py:38
    ├── Span processor batching <-- tracing.py:90
    └── OTLP export to Jaeger <-- tracing.py:88
```

### 4. Infrastructure Correlation Processing

How the observability stack processes and correlates the data.

```text
Observability Infrastructure Processing
├── Docker Container Logs <-- compose.yaml:15
│   └── Promtail Log Collection <-- compose.observability.yaml:89
│       ├── Parse JSON logs <-- 4a
│       ├── Extract trace context <-- 4b
│       └── Ship to Loki <-- promtail-config.yaml:11
└── Grafana Dashboard Layer <-- compose.observability.yaml:104
    ├── Loki Datasource <-- datasources.yaml:22
    │   └── Extract trace_id regex <-- 4c
    └── Jaeger Integration <-- datasources.yaml:39
        └── Query logs by trace ID <-- 4d
```

---

### Source: Key Locations


| ID | Title | Path |
| -- | ----- | ---- |
| 1a | Extract Request Headers | `src/skriptoteket/web/middleware/correlation.py:46` |
| 1b | Parse Correlation ID | `src/skriptoteket/web/middleware/correlation.py:47` |
| 1c | Store in Request State | `src/skriptoteket/web/middleware/correlation.py:49` |
| 1d | Clear Context | `src/skriptoteket/web/middleware/correlation.py:51` |
| 1e | Bind to Structlog | `src/skriptoteket/web/middleware/correlation.py:52` |
| 2a | Merge Context Variables | `src/skriptoteket/observability/logging.py:53` |
| 2b | Extract Current Span | `src/skriptoteket/observability/logging.py:27` |
| 2c | Add Trace ID | `src/skriptoteket/observability/logging.py:31` |
| 2d | Add Span ID | `src/skriptoteket/observability/logging.py:32` |
| 3a | Extract W3C Trace Context | `src/skriptoteket/web/middleware/tracing.py:56` |
| 3b | Create Request Span | `src/skriptoteket/web/middleware/tracing.py:61` |
| 3c | Enrich with Correlation | `src/skriptoteket/web/middleware/tracing.py:70` |
| 3d | Inject Trace Headers | `src/skriptoteket/web/middleware/tracing.py:85` |
| 4a | Extract Correlation in Promtail | `observability/promtail/promtail-config.yaml:74` |
| 4b | Extract Trace Context | `observability/promtail/promtail-config.yaml:75` |
| 4c | Grafana Trace Extraction | `observability/grafana/provisioning/datasources/datasources.yaml:33` |
| 4d | Trace-to-Log Query | `observability/grafana/provisioning/datasources/datasources.yaml:53` |

## Findings And Interpretation

No separate findings and interpretation is stated in the source.

## Evidence Gaps And Follow-Up

No separate evidence gaps and follow-up is stated in the source.
