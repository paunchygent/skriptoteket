from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction

from skriptoteket.protocols.uow import UnitOfWorkProtocol

if TYPE_CHECKING:
    from types import TracebackType


class SQLAlchemyUnitOfWork(UnitOfWorkProtocol):
    """Unit of Work that controls SQLAlchemy transactions.

    - The outermost `async with uow:` joins the current transaction (nested or root)
      if one exists, otherwise starts a new root transaction.
    - Nested `async with uow:` blocks use SAVEPOINTs via `begin_nested()` so that
      an inner rollback does not wipe out outer changes.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._transactions: list[AsyncSessionTransaction] = []

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        if self._transactions:
            self._transactions.append(await self._session.begin_nested())
            return self

        if self._session.in_nested_transaction():
            transaction = self._session.get_nested_transaction()
            if transaction is None:
                transaction = await self._session.begin_nested()
            self._transactions.append(transaction)
            return self

        if self._session.in_transaction():
            transaction = self._session.get_transaction()
            if transaction is None:
                transaction = await self._session.begin()
            self._transactions.append(transaction)
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

        transaction = self._transactions.pop()
        if exc:
            await transaction.rollback()
        else:
            await transaction.commit()
