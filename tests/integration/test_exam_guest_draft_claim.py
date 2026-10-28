"""Guest exam draft claims across teachers and concurrent transactions."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from skriptoteket.web.error_mapping import error_to_status
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.infrastructure.repositories.exam_workspace_test_support import create_owner
from tests.integration.test_exam_workspace_guest_draft_handoff_titles import _handoff

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]


async def test_same_teacher_repeat_returns_existing_exam(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory)
    storage = LocalVaultStorage(vault_root=tmp_path)
    clock = FixedClock(datetime.now(UTC))
    draft = uuid4()
    first = await _handoff(session_factory, storage, clock, actor, draft, "Hemligt prov")
    second = await _handoff(session_factory, storage, clock, actor, draft, "Annat")
    assert second == first


async def test_other_teacher_gets_generic_409(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    first = await create_owner(session_factory)
    second = await create_owner(session_factory)
    storage = LocalVaultStorage(vault_root=tmp_path)
    clock = FixedClock(datetime.now(UTC))
    draft = uuid4()
    await _handoff(session_factory, storage, clock, first, draft, "Hemligt prov")
    with pytest.raises(DomainError) as caught:
        await _handoff(session_factory, storage, clock, second, draft, "Annat")
    assert caught.value.code == ErrorCode.CONFLICT
    assert error_to_status(caught.value.code) == 409
    assert caught.value.message == "Utkastet har redan sparats av ett annat konto."
    assert caught.value.details == {}


async def test_concurrent_teachers_exactly_one_wins(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    first = await create_owner(session_factory)
    second = await create_owner(session_factory)
    storage = LocalVaultStorage(vault_root=tmp_path)
    clock = FixedClock(datetime.now(UTC))
    draft = uuid4()
    results = await asyncio.gather(
        _handoff(session_factory, storage, clock, first, draft, "Hemligt prov"),
        _handoff(session_factory, storage, clock, second, draft, "Annat"),
        return_exceptions=True,
    )
    errors = [result for result in results if isinstance(result, DomainError)]
    assert len(errors) == 1
    assert errors[0].code == ErrorCode.CONFLICT
    assert sum(not isinstance(result, BaseException) for result in results) == 1
