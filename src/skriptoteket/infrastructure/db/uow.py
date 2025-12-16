from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction

from skriptoteket.protocols.uow import UnitOfWorkProtocol

if TYPE_CHECKING:
    from types import TracebackType


class SQLAlchemyUnitOfWork(UnitOfWorkProtocol):
    """Unit of Work with conditional transaction handling.

    When the session is already in a transaction (e.g., test fixtures with flushed data),
    uses begin_nested() (savepoint) to avoid affecting the outer transaction on rollback.
    When no transaction exists, commits the session directly.

    The session provider in di.py commits any pending outer transaction on cleanup,
    ensuring data persists in production while test isolation is preserved.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._transaction: AsyncSessionTransaction | None = None

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        if self._session.in_transaction():
            # Already in transaction (test or dependency read triggered autobegin)
            # Use savepoint so rollback doesn't affect outer transaction
            self._transaction = await self._session.begin_nested()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._transaction is not None:
            # Savepoint mode - commit or rollback the savepoint
            if exc:
                await self._transaction.rollback()
            else:
                await self._transaction.commit()
        else:
            # Direct mode - commit or rollback the session
            if exc:
                await self._session.rollback()
            else:
                await self._session.commit()
