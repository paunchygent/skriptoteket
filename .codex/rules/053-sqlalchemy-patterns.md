---
id: "053-sqlalchemy-patterns"
type: "implementation"
created: 2025-12-13
updated: 2026-01-22
scope: "backend"
---

# 053: SQLAlchemy Patterns (Async + UoW)

## 1. Engine + session infrastructure

Canonical provider:

- `src/skriptoteket/di/infrastructure/db.py`

Key rules:

- Engine + sessionmaker are `Scope.APP`.
- `AsyncSession` is `Scope.REQUEST`.
- The session provider rolls back any open transaction on teardown (safety net).

## 2. Unit of Work owns transactions (REQUIRED)

Canonical implementation:

- `src/skriptoteket/infrastructure/db/uow.py` (`SQLAlchemyUnitOfWork`)

Rules:

- Repositories never call `commit()`/`rollback()`.
- Use `async with uow:` in application handlers to define transactional boundaries.

## 3. DB models location

SQLAlchemy ORM models live under:

- `src/skriptoteket/infrastructure/db/models/`

Example: `src/skriptoteket/infrastructure/db/models/user.py` (`UserModel`).

## 4. Repository pattern (no commits)

Repositories live under:

- `src/skriptoteket/infrastructure/repositories/`

They receive a request-scoped `AsyncSession` and:

- use `flush()` to materialize IDs / DB-generated fields
- use `refresh()` when needed
- never commit/rollback

Example: `src/skriptoteket/infrastructure/repositories/user_repository.py` (`PostgreSQLUserRepository`).

## 5. Query patterns

- Prefer `select(...)` + `session.execute(...)`.
- Use eager loading (`selectinload`, `joinedload`) to prevent N+1 and detached loads when relevant.
