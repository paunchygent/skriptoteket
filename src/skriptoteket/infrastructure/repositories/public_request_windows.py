"""PostgreSQL repository for the public request-window limiter.

Purpose:
    Own the shared hourly counter table through the caller's Unit of Work:
    atomically bump one ``(bucket, caller_key, window_start)`` row up to its
    limit, and prune windows older than the previous hour.

Relationships:
    Implements ``PublicRequestWindowRepositoryProtocol``; consumed by
    ``application.public_request_limits.AdmitPublicRequestHandler``.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.infrastructure.db.models.public_request_window import (
    PublicRequestWindowModel,
)
from skriptoteket.protocols.public_request_limits import (
    PublicRequestBucket,
    PublicRequestWindowRepositoryProtocol,
)


class PostgreSQLPublicRequestWindowRepository(PublicRequestWindowRepositoryProtocol):
    """Postgres hourly counters on a request-scoped session; UoW owns commit."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def try_increment(
        self,
        *,
        bucket: PublicRequestBucket,
        caller_key: str,
        window_start: datetime,
        limit: int,
    ) -> int | None:
        if limit <= 0:
            return None
        statement = (
            insert(PublicRequestWindowModel)
            .values(
                bucket=bucket.value,
                caller_key=caller_key,
                window_start=window_start,
                request_count=1,
            )
            .on_conflict_do_update(
                index_elements=[
                    PublicRequestWindowModel.bucket,
                    PublicRequestWindowModel.caller_key,
                    PublicRequestWindowModel.window_start,
                ],
                set_={"request_count": PublicRequestWindowModel.request_count + 1},
                where=PublicRequestWindowModel.request_count < limit,
            )
            .returning(PublicRequestWindowModel.request_count)
        )
        result = await self._session.execute(statement)
        count = result.scalar_one_or_none()
        return int(count) if count is not None else None

    async def delete_windows_before(self, *, cutoff: datetime) -> None:
        await self._session.execute(
            delete(PublicRequestWindowModel).where(PublicRequestWindowModel.window_start < cutoff)
        )
