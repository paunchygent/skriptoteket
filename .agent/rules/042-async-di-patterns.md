---
id: "042-async-di-patterns"
type: "implementation"
created: 2025-12-13
scope: "backend"
---

# 042: Async Patterns & Dishka DI

## 1. Protocol Definitions

All dependencies **MUST** be defined as `typing.Protocol`:

```python
# protocols.py
from typing import Protocol
from uuid import UUID
from src.domain.users.models import User, CreateUserDTO

class UserRepositoryProtocol(Protocol):
    async def get_by_id(self, user_id: UUID) -> User | None: ...
    async def create(self, data: CreateUserDTO) -> User: ...
    async def update(self, user: User) -> User: ...
    async def delete(self, user_id: UUID) -> None: ...

class UserServiceProtocol(Protocol):
    async def get_by_id(self, user_id: UUID) -> User | None: ...
    async def create(self, data: CreateUserDTO, correlation_id: UUID) -> User: ...

class UnitOfWorkProtocol(Protocol):
    async def __aenter__(self) -> "UnitOfWorkProtocol": ...
    async def __aexit__(self, exc_type, exc, tb) -> None: ...

class EventPublisherProtocol(Protocol):
    async def publish(
        self,
        event: BaseModel,
        event_type: str,
        entity_id: str,
        correlation_id: UUID,
    ) -> None: ...

class IdempotencyProtocol(Protocol):
    async def is_processed(self, event_id: UUID) -> bool: ...
    async def mark_processed(self, event_id: UUID) -> None: ...
```

## 2. Dishka Container Setup

```python
# di.py
from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide, make_async_container
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import Settings
from src.protocols import (
    UserRepositoryProtocol,
    UserServiceProtocol,
    EventPublisherProtocol,
    UnitOfWorkProtocol,
)
from src.infrastructure.repositories.user_repository import PostgreSQLUserRepository  # takes AsyncSession
from src.infrastructure.uow import SQLAlchemyUnitOfWork
from src.domain.users.services import UserService
from src.infrastructure.publishers.kafka_publisher import KafkaEventPublisher

class AppProvider(Provider):
    # APP scope: Infrastructure singletons (created once)
    @provide(scope=Scope.APP)
    def provide_settings(self) -> Settings:
        return Settings()

    @provide(scope=Scope.APP)
    async def provide_engine(self, settings: Settings) -> AsyncEngine:
        return create_async_engine(
            settings.DATABASE_URL,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_pre_ping=True,
        )

    @provide(scope=Scope.APP)
    def provide_sessionmaker(
        self,
        engine: AsyncEngine,
    ) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(
            engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    @provide(scope=Scope.REQUEST)
    async def provide_session(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
    ) -> AsyncIterator[AsyncSession]:
        async with sessionmaker() as session:
            yield session

    @provide(scope=Scope.REQUEST)
    def provide_uow(self, session: AsyncSession) -> UnitOfWorkProtocol:
        return SQLAlchemyUnitOfWork(session)

    @provide(scope=Scope.APP)
    async def provide_kafka_publisher(
        self, settings: Settings
    ) -> EventPublisherProtocol:
        publisher = KafkaEventPublisher(settings.KAFKA_BOOTSTRAP_SERVERS)
        await publisher.start()
        return publisher

    # REQUEST scope: Repository (uses request session; never commits)
    @provide(scope=Scope.REQUEST)
    def provide_user_repo(self, session: AsyncSession) -> UserRepositoryProtocol:
        return PostgreSQLUserRepository(session)

    # REQUEST scope: Services/handlers (per-request)
    @provide(scope=Scope.REQUEST)
    async def provide_user_service(
        self,
        repo: UserRepositoryProtocol,
        publisher: EventPublisherProtocol,
        uow: UnitOfWorkProtocol,
    ) -> UserServiceProtocol:
        return UserService(repo, publisher, uow)

def create_container(settings: Settings):
    return make_async_container(AppProvider())
```

**Settings rule**:

- **REQUIRED**: `Settings()` is constructed once at app startup and passed into the DI container.
- **FORBIDDEN**: Global cached settings singletons (e.g. `@lru_cache def get_settings()`).

## 3. Dishka Scopes

| Scope | Lifetime | Use For |
|-------|----------|---------|
| `APP` | Application lifetime | Engine, sessionmaker, publishers |
| `REQUEST` | Single HTTP request | Session, unit-of-work, repos, services |

**Rule**: Repositories are `REQUEST` scope and must not manage sessions or transactions.

## 4. Unit of Work + Session Management

Transactions are owned by a **Unit of Work** at request/use-case scope.

```python
# infrastructure/uow.py
from src.protocols import UnitOfWorkProtocol
from sqlalchemy.ext.asyncio import AsyncSession

class SQLAlchemyUnitOfWork(UnitOfWorkProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        await self._session.begin()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc:
            await self._session.rollback()
            return
        await self._session.commit()

# infrastructure/repositories/user_repository.py
# - takes AsyncSession injected per request
# - never commits/rolls back
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from src.domain.users.models import User, CreateUserDTO
from src.infrastructure.models.user import UserModel

class PostgreSQLUserRepository(UserRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.id == user_id))
        row = result.scalar_one_or_none()
        return User.model_validate(row) if row else None

    async def create(self, data: CreateUserDTO) -> User:
        model = UserModel(**data.model_dump())
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return User.model_validate(model)
```

## 5. Async Patterns

### Concurrent Operations

```python
import asyncio

async def process_items(items: list[Item]) -> list[Result]:
    semaphore = asyncio.Semaphore(10)  # Limit concurrency

    async def process_one(item: Item) -> Result:
        async with semaphore:
            return await heavy_operation(item)

    return await asyncio.gather(*[process_one(i) for i in items])
```

### Timeout Handling

```python
async def call_with_timeout(coro, timeout: float = 30.0):
    from src.domain.errors import DomainError, ErrorCode

    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise DomainError(code=ErrorCode.TIMEOUT, message=f"Operation timed out after {timeout}s")
```

### Background Tasks

```python
# Start background task in app lifecycle
@app.on_event("startup")
async def start_background_tasks():
    app.state.outbox_task = asyncio.create_task(relay_outbox_events())

@app.on_event("shutdown")
async def stop_background_tasks():
    app.state.outbox_task.cancel()
    try:
        await app.state.outbox_task
    except asyncio.CancelledError:
        pass
```

## 6. Testing with DI

### Pure Implementation Pattern

Extract pure logic for unit testing:

```python
# domain/users/services.py
async def _create_user_impl(
    repo: UserRepositoryProtocol,
    publisher: EventPublisherProtocol,
    data: CreateUserDTO,
    correlation_id: UUID,
) -> User:
    """Pure implementation for unit testing."""
    user = await repo.create(data)
    await publisher.publish(
        UserCreatedV1(user_id=user.id),
        event_type="user.created.v1",
        entity_id=str(user.id),
        correlation_id=correlation_id,
    )
    return user

class UserService(UserServiceProtocol):
    def __init__(
        self,
        repo: UserRepositoryProtocol,
        publisher: EventPublisherProtocol,
        uow: UnitOfWorkProtocol,
    ):
        self._repo = repo
        self._publisher = publisher
        self._uow = uow

    async def create(self, data: CreateUserDTO, correlation_id: UUID) -> User:
        async with self._uow:
            return await _create_user_impl(self._repo, self._publisher, data, correlation_id)
```

### Protocol Mocking

```python
# tests/unit/test_user_service.py
from unittest.mock import AsyncMock
from src.protocols import UserRepositoryProtocol, EventPublisherProtocol
from src.domain.users.services import _create_user_impl

async def test_create_user_publishes_event():
    # Arrange
    mock_repo = AsyncMock(spec=UserRepositoryProtocol)
    mock_publisher = AsyncMock(spec=EventPublisherProtocol)
    mock_repo.create.return_value = User(id=uuid4(), email="test@example.com")

    # Act
    user = await _create_user_impl(
        repo=mock_repo,
        publisher=mock_publisher,
        data=CreateUserDTO(email="test@example.com"),
        correlation_id=uuid4(),
    )

    # Assert
    mock_publisher.publish.assert_called_once()
```

## 7. Issue Prevention

| Issue | Prevention |
|-------|------------|
| MissingGreenlet | Use `AsyncEngine`/`AsyncSession` only; no sync SQLAlchemy in async code |
| DetachedInstanceError | `expire_on_commit=False` + eager loading + avoid lazy loads across boundaries |
| Pool Exhaustion | One session per request; no per-method session creation |
| Partial commits | UoW controls a single commit/rollback per use-case |
| Resource Leaks | Request-scoped session provider closes sessions |
| Deadlocks | Semaphore-based concurrency limits |
