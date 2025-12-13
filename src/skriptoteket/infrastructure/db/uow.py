from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.protocols.uow import UnitOfWorkProtocol


class SQLAlchemyUnitOfWork(UnitOfWorkProtocol):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        await self._session.begin()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc:
            await self._session.rollback()
            return
        await self._session.commit()
