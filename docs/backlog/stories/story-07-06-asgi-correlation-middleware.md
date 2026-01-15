---
type: story
id: ST-07-06
title: "ASGI correlation middleware so access logs include correlation_id"
status: ready
owners: "agents"
created: 2026-01-15
epic: "EPIC-07"
acceptance_criteria:
  - "Given a request with `X-Correlation-ID`, when it returns 2xx, then the response echoes the same header and `uvicorn.access` logs include `correlation_id` for that request."
  - "Given a request without `X-Correlation-ID`, when it returns 2xx, then the response includes a generated UUID header and `uvicorn.access` logs include the same `correlation_id`."
  - "Given a streaming/SSE endpoint, when response headers are sent (stream begins), then `uvicorn.access` logs include `correlation_id` (not just application warnings/errors)."
  - "Tracing middleware can read `request.state.correlation_id` and attaches it to spans when tracing is enabled."
  - "Correlation context does not leak between concurrent requests (contextvars cleared after completion)."
---

## Context

The current correlation middleware is `BaseHTTPMiddleware` and clears `structlog.contextvars` too early. This causes
successful requests to miss `correlation_id` in `uvicorn.access` logs, which makes local debugging and Loki queries
harder than necessary.

ADR: `docs/adr/adr-0061-asgi-correlation-middleware.md`.

## Notes

- Keep the public contract stable: `X-Correlation-ID` header + `request.state.correlation_id`.
- Prefer pure ASGI middleware over `BaseHTTPMiddleware` to handle streaming responses correctly.
