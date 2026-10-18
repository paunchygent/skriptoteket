"""Adversarial unit tests for the public request admission handler.

Purpose:
    Lock down the per-caller and pooled admission rules against a transactional
    fake store: a caller is refused at its own limit while a fresh IP is
    admitted, the pool refuses a fresh IP, a refusal rolls back the partial
    increment, the stored caller key is a hash of the IP, the API exposes no
    user-agent input, and the window is the truncated UTC hour.

Relationships:
    - Exercises ``AdmitPublicRequestHandler`` with an in-memory repository.
"""

from __future__ import annotations

import hashlib
import inspect
from datetime import UTC, datetime

import pytest

from skriptoteket.application.public_request_limits import (
    POOL_CALLER_KEY,
    AdmitPublicRequestHandler,
)
from skriptoteket.protocols.public_request_limits import (
    AdmitPublicRequestHandlerProtocol,
    PublicRequestAdmission,
    PublicRequestBucket,
    PublicRequestRefusal,
    PublicRequestWindowRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol

_BUCKET = PublicRequestBucket.GUEST_EXPORT
_NOW = datetime(2026, 10, 18, 15, 37, 20, tzinfo=UTC)
_WINDOW = datetime(2026, 10, 18, 15, 0, tzinfo=UTC)
_PREVIOUS_HOUR = datetime(2026, 10, 18, 14, 0, tzinfo=UTC)

_FIRST_IP = "203.0.113.10"
_SECOND_IP = "203.0.113.11"


def _caller_key(client_ip: str) -> str:
    return hashlib.sha256(client_ip.encode("utf-8")).hexdigest()


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class FakeWindowRepository(PublicRequestWindowRepositoryProtocol):
    """In-memory counters with snapshot/restore for rollback proof."""

    def __init__(self) -> None:
        self.counts: dict[tuple[PublicRequestBucket, str, datetime], int] = {}
        self.deleted_cutoffs: list[datetime] = []

    def snapshot(self) -> dict[tuple[PublicRequestBucket, str, datetime], int]:
        return dict(self.counts)

    def restore(self, snapshot: dict[tuple[PublicRequestBucket, str, datetime], int]) -> None:
        self.counts = snapshot

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
        key = (bucket, caller_key, window_start)
        current = self.counts.get(key, 0)
        if current >= limit:
            return None
        self.counts[key] = current + 1
        return current + 1

    async def delete_windows_before(self, *, cutoff: datetime) -> None:
        self.deleted_cutoffs.append(cutoff)
        self.counts = {key: value for key, value in self.counts.items() if key[2] >= cutoff}


class FakeUnitOfWork(UnitOfWorkProtocol):
    """Restore the repository snapshot when a refusal rolls the transaction back."""

    def __init__(self, repository: FakeWindowRepository) -> None:
        self._repository = repository
        self._snapshot: dict[tuple[PublicRequestBucket, str, datetime], int] | None = None
        self.commits = 0
        self.rollbacks = 0

    async def __aenter__(self) -> "FakeUnitOfWork":
        self._snapshot = self._repository.snapshot()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        assert self._snapshot is not None
        if exc_type is None:
            self.commits += 1
        else:
            self._repository.restore(self._snapshot)
            self.rollbacks += 1


def _make_handler(
    *, limits: tuple[int, int]
) -> tuple[AdmitPublicRequestHandler, FakeWindowRepository, FakeUnitOfWork]:
    repository = FakeWindowRepository()
    uow = FakeUnitOfWork(repository)
    handler = AdmitPublicRequestHandler(
        uow=uow,
        windows=repository,
        clock=FixedClock(_NOW),
        limits={bucket: limits for bucket in PublicRequestBucket},
    )
    return handler, repository, uow


@pytest.mark.unit
@pytest.mark.asyncio
async def test_caller_limit_refuses_one_ip_while_a_fresh_ip_is_admitted() -> None:
    handler, repository, uow = _make_handler(limits=(1, 100))

    first = await handler.admit(bucket=_BUCKET, client_ip=_FIRST_IP)
    assert first == PublicRequestAdmission(admitted=True, refusal=None)

    refused = await handler.admit(bucket=_BUCKET, client_ip=_FIRST_IP)
    assert refused.admitted is False
    assert refused.refusal is PublicRequestRefusal.CALLER_LIMIT

    other = await handler.admit(bucket=_BUCKET, client_ip=_SECOND_IP)
    assert other.admitted is True

    assert repository.counts[(_BUCKET, _caller_key(_FIRST_IP), _WINDOW)] == 1
    assert repository.counts[(_BUCKET, _caller_key(_SECOND_IP), _WINDOW)] == 1
    assert repository.counts[(_BUCKET, POOL_CALLER_KEY, _WINDOW)] == 2
    assert uow.commits == 2
    assert uow.rollbacks == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pool_limit_refuses_a_fresh_ip_once_the_pool_is_full() -> None:
    handler, repository, _uow = _make_handler(limits=(100, 1))

    assert (await handler.admit(bucket=_BUCKET, client_ip=_FIRST_IP)).admitted is True

    refused = await handler.admit(bucket=_BUCKET, client_ip=_SECOND_IP)
    assert refused.admitted is False
    assert refused.refusal is PublicRequestRefusal.POOL_LIMIT
    assert (_BUCKET, _caller_key(_SECOND_IP), _WINDOW) not in repository.counts
    assert repository.counts[(_BUCKET, POOL_CALLER_KEY, _WINDOW)] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refusal_rolls_back_both_counters() -> None:
    handler, repository, uow = _make_handler(limits=(100, 1))
    await handler.admit(bucket=_BUCKET, client_ip=_FIRST_IP)
    before = dict(repository.counts)

    refused = await handler.admit(bucket=_BUCKET, client_ip=_SECOND_IP)

    assert refused.refusal is PublicRequestRefusal.POOL_LIMIT
    assert repository.counts == before
    assert uow.rollbacks == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stored_caller_key_is_a_hash_not_the_raw_ip() -> None:
    handler, repository, _uow = _make_handler(limits=(5, 5))

    await handler.admit(bucket=_BUCKET, client_ip=_FIRST_IP)

    stored_keys = {caller_key for (_bucket, caller_key, _window) in repository.counts}
    assert _FIRST_IP not in stored_keys
    assert _caller_key(_FIRST_IP) in stored_keys


@pytest.mark.unit
@pytest.mark.asyncio
async def test_window_is_the_truncated_utc_hour_and_prunes_the_previous_hour() -> None:
    handler, repository, _uow = _make_handler(limits=(5, 5))

    await handler.admit(bucket=_BUCKET, client_ip=_FIRST_IP)

    assert {window_start for (_bucket, _caller, window_start) in repository.counts} == {_WINDOW}
    assert repository.deleted_cutoffs == [_PREVIOUS_HOUR]


@pytest.mark.unit
def test_public_limiter_api_exposes_no_user_agent_input() -> None:
    parameters = [
        *inspect.signature(AdmitPublicRequestHandler.admit).parameters,
        *inspect.signature(AdmitPublicRequestHandlerProtocol.admit).parameters,
        *inspect.signature(PublicRequestWindowRepositoryProtocol.try_increment).parameters,
        *inspect.signature(PublicRequestWindowRepositoryProtocol.delete_windows_before).parameters,
    ]

    assert [name for name in parameters if "agent" in name.lower()] == []
