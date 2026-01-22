---
id: "042-async-di-patterns"
type: "implementation"
created: 2025-12-13
updated: 2026-01-22
scope: "backend"
---

# 042: Async Patterns & Dishka DI (Skriptoteket)

## 1. Protocol-first DI (REQUIRED)

- Depend on `typing.Protocol`, not concrete implementations.
- Protocols live in `src/skriptoteket/protocols/` and are organized by domain (not a single `protocols.py`).

Examples in the codebase:

- `src/skriptoteket/protocols/uow.py`
- `src/skriptoteket/protocols/identity.py`
- `src/skriptoteket/protocols/runner.py`

## 2. Composition root (REQUIRED)

The DI container is assembled in:

- `src/skriptoteket/di/__init__.py` (`create_container(settings)`)

Providers are split by responsibility; infrastructure providers live under:

- `src/skriptoteket/di/infrastructure/`

## 3. Settings rule (REQUIRED)

- **REQUIRED**: Construct `Settings()` once in the app factory (`src/skriptoteket/web/app.py`) and pass it into
  `create_container(settings)`.
- **FORBIDDEN**: global cached settings singletons (e.g. `@lru_cache def get_settings()`).

## 4. Scopes (Dishka)

| Scope | Lifetime | Use For |
|-------|----------|---------|
| `APP` | Application lifetime | Settings, engine, sessionmaker, singletons |
| `REQUEST` | Single HTTP request | AsyncSession, UoW, repositories, handlers |

## 5. DB session + Unit of Work (REQUIRED)

Canonical provider:

- `src/skriptoteket/di/infrastructure/db.py`

Rules:

- **One AsyncSession per request** (Dishka `Scope.REQUEST`).
- **Unit of Work owns transactions** (`src/skriptoteket/infrastructure/db/uow.py`).
- **Repositories never commit/rollback**; they only `flush()`/`refresh()` as needed.
- **Safety net**: request-scoped session provider rolls back any open transaction on teardown.

## 6. Async patterns

- Prefer async-first libraries (SQLAlchemy asyncio, httpx/aiohttp).
- For bounded concurrency, use `asyncio.Semaphore` and `asyncio.gather`.
- Use timeouts at the boundary (network calls, LLM calls, runner calls); wrap failures into `DomainError` in the
  appropriate layer.
