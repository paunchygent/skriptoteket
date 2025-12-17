---
id: "053-sqlalchemy-patterns"
type: "implementation"
created: 2025-12-13
scope: "backend"
---

# 053: SQLAlchemy Patterns

## 1. Engine Configuration

```python
# di.py
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

@provide(scope=Scope.APP)
async def provide_engine(self, settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.DATABASE_POOL_SIZE,      # Default: 10
        max_overflow=settings.DATABASE_MAX_OVERFLOW, # Default: 20
        pool_pre_ping=True,                          # Verify connections
        pool_recycle=3600,                           # Recycle after 1 hour
        echo=settings.DATABASE_ECHO,                 # SQL logging (dev only)
    )
```

## 2. Model Definition

```python
# infrastructure/models/user.py
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from uuid import UUID, uuid4
from datetime import datetime

class Base(DeclarativeBase):
    pass

class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
```

## 3. Session + Unit of Work (transactions)

Create `AsyncEngine` and `async_sessionmaker` in `Scope.APP`, then create a single `AsyncSession` per request/use-case in `Scope.REQUEST`. A Unit of Work controls commit/rollback.

```python
# di.py
from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

@provide(scope=Scope.APP)
def provide_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

@provide(scope=Scope.REQUEST)
async def provide_session(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with sessionmaker() as session:
        try:
            yield session
        finally:
            # Ensure the connection is returned to the pool clean.
            # The Unit of Work owns commit; anything left open is rolled back.
            if session.in_transaction():
                await session.rollback()
```

```python
# infrastructure/uow.py
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction
from src.protocols import UnitOfWorkProtocol

if TYPE_CHECKING:
    from types import TracebackType

class SQLAlchemyUnitOfWork(UnitOfWorkProtocol):
    """Unit of Work that controls SQLAlchemy transactions.

    - The outermost `async with uow:` joins the current transaction (nested or root)
      if one exists, otherwise starts a new root transaction.
    - Nested `async with uow:` blocks use SAVEPOINTs via `begin_nested()` so that
      an inner rollback does not wipe out outer changes.
    """

    def __init__(self, session: AsyncSession):
        self._session = session
        self._transactions: list[AsyncSessionTransaction] = []

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        if self._transactions:
            self._transactions.append(await self._session.begin_nested())
            return self

        if self._session.in_nested_transaction():
            tx = self._session.get_nested_transaction()
            self._transactions.append(tx if tx is not None else await self._session.begin_nested())
            return self

        if self._session.in_transaction():
            tx = self._session.get_transaction()
            self._transactions.append(tx if tx is not None else await self._session.begin())
            return self

        self._transactions.append(await self._session.begin())
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if not self._transactions:
            return

        tx = self._transactions.pop()
        if exc:
            await tx.rollback()
        else:
            await tx.commit()
```

### Transaction handling modes

| Scenario | Behavior |
|----------|----------|
| Fresh request, no prior DB access | Outer UoW starts root transaction and commits/rolls back it. |
| Dependency did a read first (autobegin) | Outer UoW joins the root transaction and commits/rolls back it. |
| Nested `async with uow:` usage | Inner blocks use SAVEPOINTs to isolate rollbacks. |
| Integration tests that share a session + use `flush()` fixtures | Wrap each request in a SAVEPOINT so app rollbacks don't wipe fixture data. |

## 4. Repository Pattern (no commits)

Repositories receive an `AsyncSession` (injected) and **must not** call `commit()`/`rollback()`. Commit/rollback is owned by the Unit of Work.

```python
# infrastructure/repositories/user_repository.py
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from src.protocols import UserRepositoryProtocol
from src.domain.users.models import CreateUserDTO, User
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

    async def update(self, user: User) -> User:
        await self._session.execute(
            update(UserModel)
            .where(UserModel.id == user.id)
            .values(email=user.email, name=user.name)
        )
        return user

    async def delete(self, user_id: UUID) -> None:
        await self._session.execute(delete(UserModel).where(UserModel.id == user_id))
```

## 5. Eager Loading

Prevent N+1 queries and DetachedInstanceError:

```python
from sqlalchemy.orm import selectinload, joinedload

async def get_order_with_items(self, order_id: UUID) -> Order | None:
    result = await self._session.execute(
        select(OrderModel)
        .where(OrderModel.id == order_id)
        .options(selectinload(OrderModel.items))  # Eager load
    )
    row = result.scalar_one_or_none()
    return Order.model_validate(row) if row else None
```

| Strategy | Use When |
|----------|----------|
| `selectinload` | One-to-many, many-to-many (separate query) |
| `joinedload` | Many-to-one, one-to-one (single JOIN) |

## 6. Batch Operations

```python
async def create_many(self, items: list[CreateItemDTO]) -> list[Item]:
    models = [ItemModel(**item.model_dump()) for item in items]
    self._session.add_all(models)
    await self._session.flush()
    for model in models:
        await self._session.refresh(model)
    return [Item.model_validate(m) for m in models]
```

## 7. Transactions

For multi-operation transactions, use the Unit of Work at the use-case/handler boundary:

```python
async def transfer_funds(
    self,
    from_account_id: UUID,
    to_account_id: UUID,
    amount: float,
) -> None:
    async with self._uow:
        await self._repo.debit(from_account_id, amount)
        await self._repo.credit(to_account_id, amount)
```

### Autobegin boundary (FastAPI dependencies)

**REQUIRED**: On write routes, the first DB interaction **must** happen inside the handler’s `async with uow:`. SQLAlchemy
`AsyncSession` autobegins a transaction on the first DB call (even reads), and FastAPI dependencies share the same
request-scoped session; DB reads in dependencies will therefore start the transaction before your handler.

## 8. Optimistic Locking

```python
class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    status: Mapped[str] = mapped_column(String(50))
    version: Mapped[int] = mapped_column(default=1)  # Version column

async def update_status(self, order_id: UUID, new_status: str, expected_version: int) -> None:
    from src.domain.errors import DomainError, ErrorCode

    result = await self._session.execute(
        update(OrderModel)
        .where(
            OrderModel.id == order_id,
            OrderModel.version == expected_version,  # Check version
        )
        .values(status=new_status, version=expected_version + 1)
    )
    if result.rowcount == 0:
        raise DomainError(code=ErrorCode.CONFLICT, message="Order was modified by another process")
```

## 9. Query Patterns

```python
# Filtering
async def find_by_status(self, status: str) -> list[Order]:
    result = await self._session.execute(
        select(OrderModel)
        .where(OrderModel.status == status)
        .order_by(OrderModel.created_at.desc())
    )
    return [Order.model_validate(r) for r in result.scalars().all()]

# Pagination
async def list_paginated(self, limit: int, offset: int) -> list[Order]:
    result = await self._session.execute(
        select(OrderModel)
        .order_by(OrderModel.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [Order.model_validate(r) for r in result.scalars().all()]

# Aggregation
async def count_by_status(self) -> dict[str, int]:
    result = await self._session.execute(
        select(OrderModel.status, func.count())
        .group_by(OrderModel.status)
    )
    return {row[0]: row[1] for row in result.all()}
```

## 10. Forbidden Patterns

| Pattern | Why | Alternative |
|---------|-----|-------------|
| Raw SQL strings | SQL injection risk, no type safety | SQLAlchemy ORM |
| Global/shared `AsyncSession` singletons | Race conditions, leaks | Session per request/use-case |
| Repository calling `commit()`/`rollback()` | Breaks transaction boundaries | Unit of Work controls commit/rollback |
| `session.commit()` in loops | Partial commits | Single commit via Unit of Work |
| Missing `expire_on_commit=False` | DetachedInstanceError | Set on sessionmaker |
| `session.execute(text(...))` | Bypasses ORM safety | Use ORM constructs |
