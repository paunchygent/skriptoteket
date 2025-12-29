from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from skriptoteket.config import Settings


@asynccontextmanager
async def open_session(settings: Settings) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with sessionmaker() as session:
            yield session
    finally:
        await engine.dispose()
