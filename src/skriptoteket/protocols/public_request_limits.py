"""Protocols for the database-backed public request limiter (ST-SKRIPT-41-02 G3).

Purpose:
    Admit or refuse one anonymous public request through a shared Postgres
    counter so the per-caller and pooled hourly limits hold across workers and
    survive restarts.

Relationships:
    - ``PublicRequestWindowRepositoryProtocol`` is implemented by
      ``infrastructure.repositories.public_request_windows``.
    - ``AdmitPublicRequestHandlerProtocol`` is implemented by
      ``application.public_request_limits`` and bound in
      ``di.public_request_limits``.
    - Public routes hand the handler the client IP from
      ``web.request_metadata.get_client_ip``; the raw IP never reaches storage.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol


class PublicRequestBucket(StrEnum):
    """One limited public operation family."""

    GUEST_IMPORT = "guest_import"
    GUEST_EXPORT = "guest_export"
    GUEST_EDIT = "guest_edit"


class PublicRequestRefusal(StrEnum):
    """Which hourly limit refused the request."""

    CALLER_LIMIT = "caller_limit"
    POOL_LIMIT = "pool_limit"


@dataclass(frozen=True, slots=True)
class PublicRequestAdmission:
    """Outcome of admitting one public request."""

    admitted: bool
    refusal: PublicRequestRefusal | None = None


class PublicRequestWindowRepositoryProtocol(Protocol):
    """Own the hourly request-window rows through the caller's UoW.

    ``try_increment`` atomically inserts or bumps one ``(bucket, caller_key,
    window_start)`` row and returns the new count, or ``None`` when the row has
    already reached ``limit``. The repository never commits.
    """

    async def try_increment(
        self,
        *,
        bucket: PublicRequestBucket,
        caller_key: str,
        window_start: datetime,
        limit: int,
    ) -> int | None: ...

    async def delete_windows_before(self, *, cutoff: datetime) -> None: ...


class AdmitPublicRequestHandlerProtocol(Protocol):
    """Admit or refuse one public request against the per-caller and pooled limits."""

    async def admit(
        self, *, bucket: PublicRequestBucket, client_ip: str
    ) -> PublicRequestAdmission: ...
