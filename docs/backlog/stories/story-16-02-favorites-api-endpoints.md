---
type: story
id: ST-16-02
title: "Favorites API endpoints (add/remove/list)"
status: done
owners: "agents"
created: 2025-12-26
updated: 2025-12-28
epic: EPIC-16
acceptance_criteria:
  - "Given authenticated user with valid CSRF token, when POST /api/v1/favorites/{tool_id} with valid published tool, then favorite is added and returns 200"
  - "Given authenticated user with valid CSRF token, when POST /api/v1/favorites/{tool_id} for already-favorited tool, then returns 200 (idempotent)"
  - "Given authenticated user, when POST /api/v1/favorites/{tool_id} for nonexistent tool, then returns 404"
  - "Given authenticated user, when POST /api/v1/favorites/{tool_id} for unpublished tool, then returns 404"
  - "Given authenticated user with valid CSRF token, when DELETE /api/v1/favorites/{tool_id}, then favorite is removed and returns 200"
  - "Given authenticated user with valid CSRF token, when DELETE /api/v1/favorites/{tool_id} for non-favorited tool, then returns 200 (idempotent)"
  - "Given authenticated user, when POST/DELETE favorites without CSRF token, then returns 403"
  - "Given authenticated user with favorites, when GET /api/v1/favorites, then returns list of favorited tools with full metadata (published only)"
  - "Given limit=5, when GET /api/v1/favorites?limit=5, then returns at most 5 tools"
  - "Given authenticated user with no favorites, when GET /api/v1/favorites, then returns empty list"
  - "Given unauthenticated request, when calling any favorites endpoint, then returns 401"
---

## Context

This story implements the REST API endpoints for managing user favorites. It builds on the domain model and repository from ST-16-01.

## API contract

### Add favorite

```
POST /api/v1/favorites/{tool_id}
X-CSRF-Token: <token>

Response 200:
{
  "tool_id": "uuid",
  "is_favorite": true
}

Response 404: Tool not found or unpublished
Response 401: Not authenticated
```

### Remove favorite

```
DELETE /api/v1/favorites/{tool_id}
X-CSRF-Token: <token>

Response 200:
{
  "tool_id": "uuid",
  "is_favorite": false
}

Response 401: Not authenticated
```

### List favorites

```
GET /api/v1/favorites?limit=5

Response 200:
{
  "tools": [
    {
      "id": "uuid",
      "slug": "ordlista-generator",
      "title": "Ordlistegenerator",
      "summary": "Skapar ordlistor",
      "is_favorite": true
    }
  ]
}

Response 401: Not authenticated
```

## Implementation notes

### Handlers

Create in `src/skriptoteket/application/favorites/handlers/`:

- `add_favorite.py` — AddFavoriteHandler
- `remove_favorite.py` — RemoveFavoriteHandler
- `list_favorites.py` — ListFavoritesHandler

Each handler follows the established pattern with Dishka DI injection.

### Commands and queries

Create `src/skriptoteket/application/favorites/commands.py`:

```python
class AddFavoriteCommand(BaseModel):
    tool_id: UUID

class RemoveFavoriteCommand(BaseModel):
    tool_id: UUID
```

Create `src/skriptoteket/application/favorites/queries.py`:

```python
class ListFavoritesQuery(BaseModel):
    limit: int | None = None

class ListFavoritesResult(BaseModel):
    tools: list[FavoritedTool]
```

### API router

Create `src/skriptoteket/web/api/v1/favorites.py` with FastAPI router.

## Files to create

- `src/skriptoteket/application/favorites/__init__.py`
- `src/skriptoteket/application/favorites/commands.py`
- `src/skriptoteket/application/favorites/queries.py`
- `src/skriptoteket/application/favorites/handlers/__init__.py`
- `src/skriptoteket/application/favorites/handlers/add_favorite.py`
- `src/skriptoteket/application/favorites/handlers/remove_favorite.py`
- `src/skriptoteket/application/favorites/handlers/list_favorites.py`
- `src/skriptoteket/web/api/v1/favorites.py`
- `src/skriptoteket/di/favorites.py`

## Files to modify

- `src/skriptoteket/web/app.py` (register favorites router)
- `src/skriptoteket/di/__init__.py` (include FavoritesProvider)

## Testing

- Unit tests for each handler with mocked repository
- Integration tests for API endpoints
- Test idempotency of add/remove operations
