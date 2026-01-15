---
type: pr
id: PR-0032
title: "Correlation: ASGI middleware so access logs include correlation_id"
status: ready
owners: "agents"
created: 2026-01-15
updated: 2026-01-15
stories:
  - "ST-07-06"
adrs:
  - "ADR-0061"
tags: ["backend", "observability"]
acceptance_criteria:
  - "Successful requests (2xx) include `correlation_id` in `uvicorn.access` logs."
  - "Streaming/SSE requests include `correlation_id` in `uvicorn.access` logs when response headers are sent (stream begins)."
  - "Tracing middleware sees `request.state.correlation_id` (when tracing is enabled)."
---

## Problem

`uvicorn.access` logs do not include `correlation_id` for successful requests because our current correlation
middleware uses `BaseHTTPMiddleware` and clears `structlog.contextvars` before the response is fully sent.

## Goal

Make correlation consistent across:

- application logs
- tracing spans (optional)
- **uvicorn access logs**, including successful and streaming requests

## Non-goals

- Changing the public correlation header name (keep `X-Correlation-ID`)
- Adding request/response body logging

## Implementation plan

- Implement correlation as pure ASGI middleware (per ADR-0061).
- Preserve `request.state.correlation_id` by writing to `scope["state"]`.
- Wrap `send` to inject `X-Correlation-ID` into `http.response.start`.
- Ensure middleware ordering makes correlation outermost (so tracing/metrics/error handler can access it).
- Add targeted tests for access-log correlation (including streaming).

## Test plan

- Unit/integration:
  - Add an ASGI-level test that asserts `X-Correlation-ID` echoing and captures `uvicorn.access` log records with
    `correlation_id` present at `http.response.start` (no real server required).
- Manual:
  - `curl -i -H 'X-Correlation-ID: <uuid>' http://127.0.0.1:8000/healthz` and confirm `docker logs skriptoteket_web`
    includes that `correlation_id` on the access log line.
  - Trigger an SSE endpoint (editor chat) and confirm the access log includes `correlation_id` when the stream begins.

## Rollback plan

- Revert to the prior `BaseHTTPMiddleware` implementation and restore previous middleware ordering.
