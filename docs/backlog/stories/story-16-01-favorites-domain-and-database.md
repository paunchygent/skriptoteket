---
type: story
id: ST-16-01
title: "Favorites domain model and database migration"
status: ready
owners: "agents"
created: 2025-12-26
epic: EPIC-16
acceptance_criteria:
  - "Given the migration runs, when I inspect the database, then user_favorites table exists with composite PK (user_id, tool_id) and created_at column"
  - "Given user_favorites table, when a user is deleted, then their favorites are cascade deleted"
  - "Given user_favorites table, when a tool is deleted, then its favorites are cascade deleted"
  - "Given UserFavorite domain model, when instantiated, then it is frozen (immutable) with user_id, tool_id, created_at"
  - "Given UserFavoriteRepositoryProtocol, when imported, then it defines add, remove, is_favorite, list_for_user, list_favorites_for_tools methods"
  - "Given PostgreSQLUserFavoriteRepository, when add is called twice for same user/tool, then second call is idempotent (no error)"
---

## Context

This story establishes the domain model and database infrastructure for user favorites. It follows the established DDD/Clean Architecture patterns with protocol-first DI.

## Implementation notes

### Domain model

Create `src/skriptoteket/domain/favorites/models.py`:

```python
from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class UserFavorite(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)
    user_id: UUID
    tool_id: UUID
    created_at: datetime
```

### Database model

Create `src/skriptoteket/infrastructure/db/models/user_favorite.py`:

- Table name: `user_favorites`
- Composite PK: `(user_id, tool_id)`
- Indexes on both columns for efficient lookups
- Cascade deletes on both FKs

### Repository protocol

Create `src/skriptoteket/protocols/favorites.py`:

```python
class UserFavoriteRepositoryProtocol(Protocol):
    async def add(self, *, user_id: UUID, tool_id: UUID) -> UserFavorite: ...
    async def remove(self, *, user_id: UUID, tool_id: UUID) -> None: ...
    async def is_favorite(self, *, user_id: UUID, tool_id: UUID) -> bool: ...
    async def list_for_user(self, *, user_id: UUID) -> list[UUID]: ...
    async def list_favorites_for_tools(self, *, user_id: UUID, tool_ids: list[UUID]) -> set[UUID]: ...
```

### Migration

Create Alembic migration with:

- `CREATE TABLE user_favorites`
- Indexes on `user_id` and `tool_id`
- Cascade delete constraints

## Files to create

- `src/skriptoteket/domain/favorites/__init__.py`
- `src/skriptoteket/domain/favorites/models.py`
- `src/skriptoteket/protocols/favorites.py`
- `src/skriptoteket/infrastructure/db/models/user_favorite.py`
- `src/skriptoteket/infrastructure/repositories/user_favorite_repository.py`
- `migrations/versions/XXXX_user_favorites.py`

## Files to modify

- `src/skriptoteket/infrastructure/db/models/__init__.py` (export UserFavoriteModel)
- `src/skriptoteket/di/infrastructure.py` (wire repository)

## Testing

- Unit test for domain model immutability
- Integration test for repository with testcontainers PostgreSQL
- Migration idempotency test
