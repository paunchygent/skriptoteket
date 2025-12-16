---
type: story
id: ST-06-03
title: "Add test coverage for error handling middleware (HTML + JSON)"
status: done
owners: "agents"
created: 2025-12-16
epic: "EPIC-06"
acceptance_criteria:
  - "error_handler.py coverage increases from ~43% to >80%."
  - "DomainError returns JSON for /api routes and for Accept: application/json."
  - "DomainError returns an HTML error template for browser requests."
  - "Unhandled exceptions return a safe 500 response (JSON or HTML depending on request)."
---

## Context

The error middleware is responsible for mapping `DomainError` to HTTP responses and returning safe 500s for unexpected
exceptions. It currently has low test coverage despite being on all request paths.

## Scope

- Add tests that exercise:
  - JSON error shape and status codes for API requests (`/api/...`) and Accept header negotiation.
  - HTML template error response for browser requests.
  - Generic exception path returning status 500.

## Notes

- Keep assertions resilient: validate status code + key JSON fields, and for HTML validate presence of error code/message.
