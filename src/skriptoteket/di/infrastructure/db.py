"""Infrastructure provider: settings, database engine, sessions, and unit of work."""

from __future__ import annotations

from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from skriptoteket.config import Settings
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class InfrastructureDatabaseProvider(Provider):
    """Provides settings and database session infrastructure."""

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._settings = settings

    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return self._settings

    @provide(scope=Scope.APP)
    def engine(self, settings: Settings) -> AsyncEngine:
        return create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DATABASE_ECHO,
            pool_pre_ping=True,
        )

    @provide(scope=Scope.APP)
    def sessionmaker(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    @provide(scope=Scope.REQUEST)
    async def session(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
    ) -> AsyncIterator[AsyncSession]:
        async with sessionmaker() as session:
            try:
                yield session
            finally:
                if session.in_transaction():
                    await session.rollback()

    @provide(scope=Scope.REQUEST)
    def uow(self, session: AsyncSession) -> UnitOfWorkProtocol:
        return SQLAlchemyUnitOfWork(session)
