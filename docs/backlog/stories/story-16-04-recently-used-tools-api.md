---
type: story
id: ST-16-04
title: "Recently used tools API endpoint"
status: ready
owners: "agents"
created: 2025-12-26
epic: EPIC-16
acceptance_criteria:
  - "Given user has run tools, when GET /api/v1/me/recent-tools, then returns tools ordered by most recent run first"
  - "Given limit=5 parameter, when called, then returns at most 5 tools"
  - "Given no limit parameter, when called, then defaults to 10 tools"
  - "Given user has run same tool multiple times, when listing recent, then tool appears once at its most recent position"
  - "Given user has run curated apps, when listing recent tools, then curated app runs are excluded"
  - "Given a tool was unpublished after being run, when listing recent, then that tool is excluded"
  - "Given response, when inspected, then each tool includes is_favorite boolean"
  - "Given user has never run any tools, when called, then returns empty list"
---

## Context

This story implements the recently-used tools API by leveraging the existing `tool_runs` table. It provides personalized quick access based on the user's actual usage history.

## API contract

```
GET /api/v1/me/recent-tools?limit=10

Response 200:
{
  "tools": [
    {
      "id": "uuid",
      "slug": "ordlista-generator",
      "title": "Ordlistegenerator",
      "summary": "Skapar ordlistor",
      "is_favorite": false,
      "last_used_at": "2025-12-26T10:30:00Z"
    }
  ]
}
```

## Implementation notes

### Repository extension

Add to `ToolRunRepositoryProtocol` in `src/skriptoteket/protocols/scripting.py`:

```python
from datetime import datetime

async def list_recent_tools_for_user(
    self, *, user_id: UUID, limit: int = 10
) -> list[tuple[UUID, datetime]]: ...
```

Implementation in `src/skriptoteket/infrastructure/repositories/tool_run_repository.py`:

```sql
SELECT tool_id, MAX(started_at) as last_run
FROM tool_runs
WHERE requested_by_user_id = :user_id
  AND context = 'production'  -- Exclude test/sandbox runs
  AND source_kind = 'tool_version'  -- Exclude curated app runs (scope decision for EPIC-16)
GROUP BY tool_id
ORDER BY last_run DESC
LIMIT :limit
```

### Handler

Create `src/skriptoteket/application/catalog/handlers/list_recent_tools.py`:

1. Get recent tool IDs from tool_runs repository
   - Repository returns `(tool_id, last_used_at)` tuples
2. Fetch tool details for each ID
3. Filter out unpublished tools
4. Batch-check favorites
5. Preserve order from recent query

### API endpoint

Add to a new or existing `/api/v1/me/` router:

```python
@router.get("/recent-tools")
async def list_recent_tools(
    limit: int = Query(10, ge=1, le=50),
    ...
) -> ListRecentToolsResponse:
```

## Files to create

- `src/skriptoteket/application/catalog/handlers/list_recent_tools.py`
- `src/skriptoteket/web/api/v1/me.py` (if not exists)

## Files to modify

- `src/skriptoteket/protocols/scripting.py` (add list_recent_tools_for_user)
- `src/skriptoteket/infrastructure/repositories/tool_run_repository.py` (implement)
- `src/skriptoteket/application/catalog/queries.py` (add ListRecentToolsQuery/Result)
- `src/skriptoteket/di/catalog.py` (wire handler)
- `src/skriptoteket/web/app.py` (register me router if new)

## Testing

- Unit test for handler with mocked repositories
- Integration test for repository query
- Test deduplication (same tool run multiple times)
- Test filtering of unpublished tools
