"""Database-backed admission for anonymous public requests (ST-SKRIPT-41-02 G3).

Purpose:
    Admit or refuse one public request against a per-caller and a pooled hourly
    limit shared by all workers through the request-window table.

Relationships:
    - Implements ``AdmitPublicRequestHandlerProtocol``.
    - Owns the UoW transaction; the window repository never commits.
    - Public routes pass the client IP string from ``get_client_ip``.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.public_request_limits import (
    AdmitPublicRequestHandlerProtocol,
    PublicRequestAdmission,
    PublicRequestBucket,
    PublicRequestRefusal,
    PublicRequestWindowRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol

# The pooled counter shares the window table with a reserved caller key.
POOL_CALLER_KEY = "*"


class _RefusedAdmission(Exception):
    """Signals a refusal inside the UoW so the whole transaction rolls back."""

    def __init__(self, refusal: PublicRequestRefusal) -> None:
        super().__init__(refusal.value)
        self.refusal = refusal


class AdmitPublicRequestHandler(AdmitPublicRequestHandlerProtocol):
    """Admit one request per (bucket, caller) under per-caller and pooled limits."""

    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        windows: PublicRequestWindowRepositoryProtocol,
        clock: ClockProtocol,
        limits: Mapping[PublicRequestBucket, tuple[int, int]],
    ) -> None:
        self._uow = uow
        self._windows = windows
        self._clock = clock
        self._limits = limits

    async def admit(self, *, bucket: PublicRequestBucket, client_ip: str) -> PublicRequestAdmission:
        window_start = _hour_start(self._clock.now())
        caller_key = _caller_key(client_ip)
        caller_limit, pool_limit = self._limits[bucket]
        try:
            async with self._uow:
                await self._windows.delete_windows_before(cutoff=window_start - timedelta(hours=1))
                await self._increment_or_refuse(
                    bucket=bucket,
                    caller_key=caller_key,
                    window_start=window_start,
                    limit=caller_limit,
                    refusal=PublicRequestRefusal.CALLER_LIMIT,
                )
                await self._increment_or_refuse(
                    bucket=bucket,
                    caller_key=POOL_CALLER_KEY,
                    window_start=window_start,
                    limit=pool_limit,
                    refusal=PublicRequestRefusal.POOL_LIMIT,
                )
        except _RefusedAdmission as refused:
            return PublicRequestAdmission(admitted=False, refusal=refused.refusal)
        return PublicRequestAdmission(admitted=True, refusal=None)

    async def _increment_or_refuse(
        self,
        *,
        bucket: PublicRequestBucket,
        caller_key: str,
        window_start: datetime,
        limit: int,
        refusal: PublicRequestRefusal,
    ) -> None:
        count = await self._windows.try_increment(
            bucket=bucket,
            caller_key=caller_key,
            window_start=window_start,
            limit=limit,
        )
        if count is None:
            raise _RefusedAdmission(refusal)


def _hour_start(now: datetime) -> datetime:
    return now.astimezone(UTC).replace(minute=0, second=0, microsecond=0)


def _caller_key(client_ip: str) -> str:
    return hashlib.sha256(client_ip.encode("utf-8")).hexdigest()
