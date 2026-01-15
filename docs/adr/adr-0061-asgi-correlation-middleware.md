---
type: adr
id: ADR-0061
title: "Observability: ASGI correlation middleware for request-complete correlation"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2026-01-15
updated: 2026-01-15
links: ["EPIC-07", "ST-07-06", "PR-0032"]
---

## Context

We use `structlog` + `structlog.contextvars` so logs can be correlated via `correlation_id` and queried in Loki.

The current correlation middleware is implemented using Starlette `BaseHTTPMiddleware`. This has two practical problems:

1. **Access logs miss `correlation_id` on successful requests**
   - `BaseHTTPMiddleware` returns a `Response` object before the response is fully sent (especially for streaming/SSE).
   - The middleware clears contextvars in `finally` immediately after `call_next(...)` returns.
   - In our pinned Uvicorn (`0.40.0`), access logs (`uvicorn.access`) are emitted when the server sends
     `http.response.start` (response headers). With `BaseHTTPMiddleware`, contextvars are already cleared by then, so
     `merge_contextvars` cannot attach `correlation_id` to the access log line.
2. **Ordering issues**
   - Our tracing/metrics/error-handling middleware currently run outside the correlation middleware, so they cannot
     reliably access `request.state.correlation_id` early in the request lifecycle (e.g., tracing spans miss the
     attribute).

## Decision

Replace the correlation middleware with a **pure ASGI middleware** that binds and clears contextvars at the correct
time for both normal and streaming responses:

- Parse `X-Correlation-ID` from inbound headers and validate it as a UUID; generate a new UUID if missing/invalid.
- Store the UUID in `scope["state"]["correlation_id"]` so it is available as `request.state.correlation_id` in FastAPI.
- Bind `correlation_id` via `structlog.contextvars` for the full ASGI request lifecycle.
- Wrap `send` to inject `X-Correlation-ID` into the `http.response.start` headers.
- Clear contextvars only after the response is complete (i.e., after the downstream ASGI app returns and/or after the
  final `http.response.body` with `more_body=False`).
- Register the correlation middleware as **outermost** so downstream HTTP middlewares (tracing/metrics/error handler)
  can read `request.state.correlation_id` and logs emitted by uvicorn access logging can include `correlation_id`.

## Consequences

- `uvicorn.access` log lines for 2xx/3xx requests include `correlation_id` (development and production).
- Correlation is reliable for streaming endpoints (SSE) and long-lived responses.
- Tracing middleware can attach `correlation_id` to spans when OpenTelemetry is enabled.
- We must be careful to avoid cross-request leakage by ensuring contextvars are always cleared on completion and on
  exceptions/disconnects.
