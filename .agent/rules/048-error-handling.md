---
id: "048-error-handling"
type: "implementation"
created: 2025-12-13
updated: 2026-01-22
scope: "backend"
---

# 048: Structured Error Handling (DomainError → API JSON)

Skriptoteket is SPA-first: application errors are returned as **JSON** to `/api/v1/*` callers. There are no
server-rendered page/HTMX error surfaces.

## 1. Domain errors (REQUIRED)

- Raise `DomainError` (no HTTP) in domain/application/infrastructure.
- Do not raise `HTTPException` from domain/application code.

Canonical implementation:

- `src/skriptoteket/domain/errors.py` (`DomainError`, `ErrorCode`, helpers like `not_found()`).

## 2. HTTP status mapping (web layer only)

Mapping lives in the web layer:

- `src/skriptoteket/web/error_mapping.py`

## 3. API error envelope (REQUIRED)

Errors are returned as:

```json
{
  "error": { "code": "SOME_CODE", "message": "...", "details": {} },
  "correlation_id": "..."
}
```

Canonical middleware:

- `src/skriptoteket/web/middleware/error_handler.py`

## 4. Correlation ID (REQUIRED)

- Correlation IDs are attached at the boundary via middleware and must be logged + returned in error responses.
- See: `src/skriptoteket/web/middleware/correlation.py`

## 5. SPA fallback note

The SPA history fallback (`src/skriptoteket/web/routes/spa_fallback.py`) may return minimal HTML for missing routes or
missing SPA build artifacts. Do not introduce new HTML “UI error pages”.
