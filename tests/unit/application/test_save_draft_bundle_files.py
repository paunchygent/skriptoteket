"""Saving gruppgenerator's real bundle from the editor and overriding it for a run."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.commands import (
    SaveDraftVersionCommand,
    ToolVersionOverride,
)
from skriptoteket.application.scripting.handlers.execute_tool_version import (
    _apply_version_override,
)
from skriptoteket.application.scripting.handlers.save_draft_version import SaveDraftVersionHandler
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.draft_locks import DraftLock
from skriptoteket.domain.scripting.tool_versions import ToolVersion, compute_content_hash
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.draft_locks import DraftLockRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.scripting import ToolVersionRepositoryProtocol
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.scripting.handlers.gruppgenerator_bundle_support import (
    edited_roster_py,
    gruppgenerator_draft,
    gruppgenerator_files,
)
from tests.unit.application.scripting.handlers.sandbox_test_support import FakeUow


async def _save(
    *, now: datetime, previous: ToolVersion, command_fields: dict[str, object]
) -> ToolVersion:
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = previous
    versions.list_for_tool.return_value = [previous]
    versions.get_next_version_number.return_value = previous.version_number + 1
    versions.create.side_effect = lambda *, version: version
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    maintainers.is_maintainer.return_value = True
    settings = Mock(spec=Settings)
    settings.DRAFT_LOCK_TTL_SECONDS = 600
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now
    locks = AsyncMock(spec=DraftLockRepositoryProtocol)
    locks.get_for_tool.return_value = DraftLock(
        tool_id=previous.tool_id,
        draft_head_id=previous.id,
        locked_by_user_id=previous.created_by_user_id,
        locked_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(minutes=5),
        forced_by_user_id=None,
    )
    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = uuid4()
    handler = SaveDraftVersionHandler(
        settings=settings,
        uow=FakeUow(),
        versions=versions,
        maintainers=maintainers,
        locks=locks,
        clock=clock,
        id_generator=id_generator,
    )
    result = await handler.handle(
        actor=make_user(role=Role.CONTRIBUTOR, user_id=previous.created_by_user_id),
        command=SaveDraftVersionCommand.model_validate(
            {
                "version_id": previous.id,
                "expected_parent_version_id": previous.id,
                "entrypoint": "run_tool",
                "source_code": previous.source_code,
                **command_fields,
            }
        ),
    )
    return result.version


def _draft(now: datetime) -> ToolVersion:
    return gruppgenerator_draft(
        version_id=uuid4(), tool_id=uuid4(), created_by_user_id=uuid4(), now=now
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_saving_an_edited_roster_keeps_every_other_file(now: datetime) -> None:
    previous = _draft(now)
    edited_bundle = {
        **previous.bundle_files,
        "roster.py": edited_roster_py(previous.bundle_files["roster.py"]),
    }

    saved = await _save(now=now, previous=previous, command_fields={"bundle_files": edited_bundle})

    source_code, original_bundle = gruppgenerator_files()
    assert saved.source_code == source_code
    assert saved.bundle_files["roster.py"] == edited_bundle["roster.py"]
    assert saved.bundle_files["grouping.py"] == original_bundle["grouping.py"]
    assert saved.content_hash == compute_content_hash(
        entrypoint="run_tool", source_code=source_code, bundle_files=edited_bundle
    )
    assert saved.content_hash != previous.content_hash


@pytest.mark.unit
@pytest.mark.asyncio
async def test_a_save_without_bundle_files_keeps_the_saved_bundle(now: datetime) -> None:
    previous = _draft(now)

    saved = await _save(now=now, previous=previous, command_fields={})

    assert saved.bundle_files == previous.bundle_files
    assert saved.bundle_files != {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_saving_a_bundle_file_named_outside_the_bundle_is_rejected(now: datetime) -> None:
    previous = _draft(now)

    with pytest.raises(DomainError) as exc:
        await _save(
            now=now,
            previous=previous,
            command_fields={"bundle_files": {**previous.bundle_files, "../roster.py": "x"}},
        )

    assert exc.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
def test_run_override_replaces_the_saved_bundle_and_rehashes(now: datetime) -> None:
    version = _draft(now)
    edited_bundle = {
        **version.bundle_files,
        "roster.py": edited_roster_py(version.bundle_files["roster.py"]),
    }

    overridden = _apply_version_override(
        version=version,
        override=ToolVersionOverride(source_code=version.source_code, bundle_files=edited_bundle),
    )

    assert overridden.bundle_files == edited_bundle
    assert overridden.content_hash == compute_content_hash(
        entrypoint=version.entrypoint,
        source_code=version.source_code,
        bundle_files=edited_bundle,
    )


@pytest.mark.unit
def test_run_override_without_bundle_files_keeps_the_saved_bundle(now: datetime) -> None:
    version = _draft(now)

    overridden = _apply_version_override(
        version=version, override=ToolVersionOverride(source_code="def run_tool(a, b):\n    pass\n")
    )

    assert overridden.bundle_files == version.bundle_files
