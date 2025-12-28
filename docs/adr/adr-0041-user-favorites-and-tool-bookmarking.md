---
type: adr
id: ADR-0041
title: "User favorites and tool bookmarking"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-26
updated: 2025-12-28
---

## Context

Teachers using Skriptoteket need a way to bookmark frequently used tools for quick access. Currently, users must navigate through Profession → Category → Tools each time they want to run a familiar tool. There is no persistent personalization — every session starts fresh.

Key considerations:

1. **Cross-device access**: Teachers may use different devices (classroom computer, personal laptop, phone)
2. **Simplicity**: The feature should be lightweight — just "star" a tool
3. **Privacy**: Favorites are personal and should not be visible to other users
4. **Cleanup**: If a tool is deleted or unpublished, favorites should handle gracefully

## Decision

### 1. Server-side storage

Favorites are stored in PostgreSQL (not browser localStorage) to enable cross-device sync. This aligns with our existing user model and session-based authentication.

### 2. Domain model

A new `favorites` bounded context with a simple domain model:

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserFavorite(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    user_id: UUID
    tool_id: UUID
    created_at: datetime
```

This is a pure many-to-many relationship with no additional metadata beyond creation timestamp.

### 3. Database table

New `user_favorites` table:

```sql
CREATE TABLE user_favorites (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tool_id UUID NOT NULL REFERENCES tools(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (user_id, tool_id)
);

CREATE INDEX ix_user_favorites_user_id ON user_favorites(user_id);
CREATE INDEX ix_user_favorites_tool_id ON user_favorites(tool_id);
```

Cascade deletes ensure cleanup when users or tools are removed.

### 4. API contract

```
POST   /api/v1/favorites/{tool_id}        → Add favorite (idempotent, 200 OK)
DELETE /api/v1/favorites/{tool_id}        → Remove favorite (idempotent, 200 OK)
GET    /api/v1/favorites?limit={limit}    → List user's favorited tools (optional limit)
```

All endpoints require authentication via the existing SPA session cookie. The tool_id in POST/DELETE is the tool
UUID (not slug) for stability.

State-changing endpoints require CSRF protection via `X-CSRF-Token` (same as existing SPA APIs).

Response for GET includes full tool metadata:

```json
{
  "tools": [
    {
      "id": "uuid",
      "slug": "ordlista-generator",
      "title": "Ordlistegenerator",
      "summary": "Skapar ordlistor från text",
      "is_favorite": true
    }
  ]
}
```

### 5. Invariants

- Only **published** tools can be added as favorites (returns 404 for unpublished/nonexistent)
- If a tool becomes unpublished after being favorited, the favorite record remains but the tool is **excluded from listings**
- Adding an already-favorited tool is idempotent (no error, returns success)
- Removing a non-favorited tool is idempotent (no error, returns success)
- `GET /api/v1/favorites` supports an optional `limit` parameter for home page previews (e.g. `limit=5`)

### 6. Integration with tool listings

Tool list responses include an `is_favorite` boolean for the authenticated user (where applicable in EPIC-16):

- `GET /api/v1/catalog/tools` (flat catalog)
- `GET /api/v1/me/recent-tools` (recently used)

This requires batch-checking favorites for the tools in each response.

## Consequences

### Positive

- Teachers can quickly access their most-used tools from any device
- Simple UX: one-click star toggle on tool cards
- No external dependencies (uses existing PostgreSQL)
- Clean domain separation in new `favorites` bounded context

### Negative

- Slightly more complex tool listing queries (need to join/check favorites)
- Small additional database load for favorites lookups

### Implementation impact

New files to create:

- `src/skriptoteket/domain/favorites/models.py`
- `src/skriptoteket/domain/favorites/__init__.py`
- `src/skriptoteket/protocols/favorites.py`
- `src/skriptoteket/infrastructure/db/models/user_favorite.py`
- `src/skriptoteket/infrastructure/repositories/user_favorite_repository.py`
- `src/skriptoteket/application/favorites/` (commands, queries, handlers)
- `src/skriptoteket/web/api/v1/favorites.py`
- `src/skriptoteket/di/favorites.py`
- `migrations/versions/XXXX_user_favorites.py`

## Related

- ADR-0042: Flat catalog with label filtering (uses favorites)
- EPIC-16: Catalog discovery and personalization
