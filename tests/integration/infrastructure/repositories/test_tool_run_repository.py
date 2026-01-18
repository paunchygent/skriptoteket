from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.curated_apps.models import curated_app_tool_id
from skriptoteket.domain.identity.models import AuthProvider, Role
from skriptoteket.domain.scripting.input_files import InputFileEntry, InputManifest
from skriptoteket.domain.scripting.models import (
    RunContext,
    RunSourceKind,
    RunStatus,
    ToolRun,
    VersionState,
)
from skriptoteket.infrastructure.db.models.tool import ToolModel
from skriptoteket.infrastructure.db.models.tool_version import ToolVersionModel
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.repositories.tool_run_repository import PostgreSQLToolRunRepository

pytestmark = pytest.mark.asyncio(loop_scope="module")


async def _create_user(*, db_session: AsyncSession, now: datetime) -> uuid.UUID:
    user_id = uuid.uuid4()
    db_session.add(
        UserModel(
            id=user_id,
            email=f"runner-{user_id.hex[:8]}@example.com",
            password_hash="hash",
            role=Role.USER,
            auth_provider=AuthProvider.LOCAL,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    return user_id


async def _create_tool(
    *,
    db_session: AsyncSession,
    now: datetime,
    owner_user_id: uuid.UUID,
) -> uuid.UUID:
    tool_id = uuid.uuid4()
    db_session.add(
        ToolModel(
            id=tool_id,
            owner_user_id=owner_user_id,
            slug=f"tool-{tool_id.hex[:8]}",
            title="Test tool",
            summary=None,
            is_published=False,
            active_version_id=None,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    return tool_id


async def _create_tool_version(
    *,
    db_session: AsyncSession,
    tool_id: uuid.UUID,
    created_by_user_id: uuid.UUID,
    now: datetime,
) -> uuid.UUID:
    version_id = uuid.uuid4()
    db_session.add(
        ToolVersionModel(
            id=version_id,
            tool_id=tool_id,
            version_number=1,
            state=VersionState.DRAFT,
            source_code="print('hi')",
            entrypoint="run_tool",
            content_hash="hash",
            input_schema=[],
            derived_from_version_id=None,
            created_by_user_id=created_by_user_id,
            created_at=now,
            submitted_for_review_by_user_id=None,
            submitted_for_review_at=None,
            reviewed_by_user_id=None,
            reviewed_at=None,
            published_by_user_id=None,
            published_at=None,
            change_summary=None,
            review_note=None,
        )
    )
    await db_session.flush()
    return version_id


@pytest.mark.integration
async def test_tool_run_create_get_and_update(db_session: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    user_id = await _create_user(db_session=db_session, now=now)
    tool_id = await _create_tool(db_session=db_session, now=now, owner_user_id=user_id)
    version_id = await _create_tool_version(
        db_session=db_session, tool_id=tool_id, created_by_user_id=user_id, now=now
    )

    repo = PostgreSQLToolRunRepository(db_session)
    run_id = uuid.uuid4()
    running = ToolRun(
        id=run_id,
        tool_id=tool_id,
        version_id=version_id,
        context=RunContext.SANDBOX,
        requested_by_user_id=user_id,
        status=RunStatus.RUNNING,
        requested_at=now,
        started_at=now,
        finished_at=None,
        workdir_path=f"{run_id}/work",
        input_filename="input.txt",
        input_size_bytes=5,
        input_manifest=InputManifest(files=[InputFileEntry(name="input.txt", bytes=5)]),
        html_output=None,
        stdout=None,
        stderr=None,
        artifacts_manifest={},
        error_summary=None,
    )

    created = await repo.create(run=running)
    assert created.id == run_id
    assert created.status is RunStatus.RUNNING

    fetched = await repo.get_by_id(run_id=run_id)
    assert fetched is not None
    assert fetched.input_filename == "input.txt"

    finished_at = now + timedelta(seconds=1)
    completed = fetched.model_copy(
        update={
            "status": RunStatus.SUCCEEDED,
            "finished_at": finished_at,
            "stdout": "ok",
            "stderr": "",
            "html_output": "<p>ok</p>",
            "artifacts_manifest": {"artifacts": []},
            "error_summary": None,
        }
    )
    updated = await repo.update(run=completed)
    assert updated.status is RunStatus.SUCCEEDED
    assert updated.finished_at == finished_at

    fetched_again = await repo.get_by_id(run_id=run_id)
    assert fetched_again is not None
    assert fetched_again.stdout == "ok"


@pytest.mark.integration
async def test_tool_run_get_missing_returns_none(db_session: AsyncSession) -> None:
    repo = PostgreSQLToolRunRepository(db_session)
    missing = await repo.get_by_id(run_id=uuid.uuid4())
    assert missing is None


@pytest.mark.integration
async def test_tool_run_update_missing_raises_not_found(db_session: AsyncSession) -> None:
    from skriptoteket.domain.errors import DomainError, ErrorCode

    now = datetime.now(timezone.utc)
    user_id = await _create_user(db_session=db_session, now=now)
    tool_id = await _create_tool(db_session=db_session, now=now, owner_user_id=user_id)
    version_id = await _create_tool_version(
        db_session=db_session, tool_id=tool_id, created_by_user_id=user_id, now=now
    )

    repo = PostgreSQLToolRunRepository(db_session)
    missing = ToolRun(
        id=uuid.uuid4(),
        tool_id=tool_id,
        version_id=version_id,
        context=RunContext.SANDBOX,
        requested_by_user_id=user_id,
        status=RunStatus.RUNNING,
        requested_at=now,
        started_at=now,
        finished_at=None,
        workdir_path="missing/work",
        input_filename="input.txt",
        input_size_bytes=1,
        input_manifest=InputManifest(files=[InputFileEntry(name="input.txt", bytes=1)]),
        html_output=None,
        stdout=None,
        stderr=None,
        artifacts_manifest={},
        error_summary=None,
    )

    with pytest.raises(DomainError) as exc:
        await repo.update(run=missing)
    assert exc.value.code is ErrorCode.NOT_FOUND


@pytest.mark.integration
async def test_tool_run_complex_fields_roundtrip(db_session: AsyncSession) -> None:
    """Test that complex fields (input_manifest, artifacts_manifest, ui_payload) roundtrip."""
    from skriptoteket.domain.scripting.ui.contract_v2 import (
        UiNoticeLevel,
        UiNoticeOutput,
        UiPayloadV2,
    )

    now = datetime.now(timezone.utc)
    user_id = await _create_user(db_session=db_session, now=now)
    tool_id = await _create_tool(db_session=db_session, now=now, owner_user_id=user_id)
    version_id = await _create_tool_version(
        db_session=db_session, tool_id=tool_id, created_by_user_id=user_id, now=now
    )

    repo = PostgreSQLToolRunRepository(db_session)
    run_id = uuid.uuid4()

    # Create with complex input_manifest
    input_manifest = InputManifest(
        files=[
            InputFileEntry(name="doc1.pdf", bytes=1024),
            InputFileEntry(name="doc2.pdf", bytes=2048),
        ]
    )

    run = ToolRun(
        id=run_id,
        tool_id=tool_id,
        version_id=version_id,
        context=RunContext.PRODUCTION,
        requested_by_user_id=user_id,
        status=RunStatus.RUNNING,
        requested_at=now,
        started_at=now,
        finished_at=None,
        workdir_path=f"{run_id}/work",
        input_filename="doc1.pdf",
        input_size_bytes=1024,
        input_manifest=input_manifest,
        html_output=None,
        stdout=None,
        stderr=None,
        artifacts_manifest={},
        error_summary=None,
    )
    await repo.create(run=run)

    # Verify input_manifest roundtrip
    fetched = await repo.get_by_id(run_id=run_id)
    assert fetched is not None
    assert fetched.input_manifest.files[0].name == "doc1.pdf"
    assert fetched.input_manifest.files[0].bytes == 1024
    assert fetched.input_manifest.files[1].name == "doc2.pdf"
    assert fetched.input_manifest.files[1].bytes == 2048

    # Update with ui_payload and artifacts_manifest
    ui_payload = UiPayloadV2(
        outputs=[UiNoticeOutput(level=UiNoticeLevel.INFO, message="Processing complete")]
    )
    artifacts_manifest = {
        "artifacts": [{"name": "output.pdf", "size": 4096, "path": "artifacts/output.pdf"}]
    }

    finished_at = now + timedelta(seconds=5)
    completed = fetched.model_copy(
        update={
            "status": RunStatus.SUCCEEDED,
            "finished_at": finished_at,
            "stdout": "Done",
            "stderr": "",
            "html_output": "<p>Complete</p>",
            "artifacts_manifest": artifacts_manifest,
            "ui_payload": ui_payload,
        }
    )
    await repo.update(run=completed)

    # Verify all complex fields roundtrip
    fetched_again = await repo.get_by_id(run_id=run_id)
    assert fetched_again is not None
    assert fetched_again.artifacts_manifest == artifacts_manifest
    assert fetched_again.ui_payload is not None
    output = fetched_again.ui_payload.outputs[0]
    assert isinstance(output, UiNoticeOutput)
    assert output.message == "Processing complete"
    assert fetched_again.html_output == "<p>Complete</p>"
    assert fetched_again.stdout == "Done"
    assert fetched_again.stderr == ""


@pytest.mark.integration
async def test_tool_run_error_summary_roundtrip(db_session: AsyncSession) -> None:
    """Test that error_summary persists correctly on failed runs."""
    now = datetime.now(timezone.utc)
    user_id = await _create_user(db_session=db_session, now=now)
    tool_id = await _create_tool(db_session=db_session, now=now, owner_user_id=user_id)
    version_id = await _create_tool_version(
        db_session=db_session, tool_id=tool_id, created_by_user_id=user_id, now=now
    )

    repo = PostgreSQLToolRunRepository(db_session)
    run_id = uuid.uuid4()

    run = ToolRun(
        id=run_id,
        tool_id=tool_id,
        version_id=version_id,
        context=RunContext.SANDBOX,
        requested_by_user_id=user_id,
        status=RunStatus.RUNNING,
        requested_at=now,
        started_at=now,
        finished_at=None,
        workdir_path=f"{run_id}/work",
        input_filename="input.txt",
        input_size_bytes=10,
        input_manifest=InputManifest(files=[InputFileEntry(name="input.txt", bytes=10)]),
        html_output=None,
        stdout=None,
        stderr=None,
        artifacts_manifest={},
        error_summary=None,
    )
    await repo.create(run=run)

    # Update with error
    failed = run.model_copy(
        update={
            "status": RunStatus.FAILED,
            "finished_at": now + timedelta(seconds=1),
            "stderr": "Traceback: SyntaxError",
            "error_summary": "Script failed with SyntaxError on line 42",
        }
    )
    await repo.update(run=failed)

    fetched = await repo.get_by_id(run_id=run_id)
    assert fetched is not None
    assert fetched.status is RunStatus.FAILED
    assert fetched.error_summary == "Script failed with SyntaxError on line 42"
    assert fetched.stderr == "Traceback: SyntaxError"


@pytest.mark.integration
async def test_list_recent_tools_for_user_groups_orders_and_limits(
    db_session: AsyncSession,
) -> None:
    now = datetime.now(timezone.utc)
    user_id = await _create_user(db_session=db_session, now=now)
    tool_id_a = await _create_tool(db_session=db_session, now=now, owner_user_id=user_id)
    tool_id_b = await _create_tool(db_session=db_session, now=now, owner_user_id=user_id)
    version_id_a = await _create_tool_version(
        db_session=db_session,
        tool_id=tool_id_a,
        created_by_user_id=user_id,
        now=now,
    )
    version_id_b = await _create_tool_version(
        db_session=db_session,
        tool_id=tool_id_b,
        created_by_user_id=user_id,
        now=now,
    )

    repo = PostgreSQLToolRunRepository(db_session)
    input_manifest = InputManifest(files=[InputFileEntry(name="input.txt", bytes=1)])

    tool_a_old = ToolRun(
        id=uuid.uuid4(),
        tool_id=tool_id_a,
        version_id=version_id_a,
        context=RunContext.PRODUCTION,
        requested_by_user_id=user_id,
        status=RunStatus.SUCCEEDED,
        requested_at=now - timedelta(minutes=5),
        started_at=now - timedelta(minutes=5),
        finished_at=now - timedelta(minutes=5) + timedelta(seconds=1),
        workdir_path="a-old/work",
        input_filename="input.txt",
        input_size_bytes=1,
        input_manifest=input_manifest,
        html_output=None,
        stdout=None,
        stderr=None,
        artifacts_manifest={},
        error_summary=None,
    )
    tool_a_new = tool_a_old.model_copy(
        update={
            "id": uuid.uuid4(),
            "requested_at": now - timedelta(minutes=1),
            "started_at": now - timedelta(minutes=1),
            "finished_at": now - timedelta(minutes=1) + timedelta(seconds=1),
        }
    )
    tool_b = tool_a_old.model_copy(
        update={
            "id": uuid.uuid4(),
            "tool_id": tool_id_b,
            "version_id": version_id_b,
            "requested_at": now - timedelta(minutes=3),
            "started_at": now - timedelta(minutes=3),
            "finished_at": now - timedelta(minutes=3) + timedelta(seconds=1),
        }
    )

    app_id = "demo.counter"
    curated_run = ToolRun(
        id=uuid.uuid4(),
        tool_id=curated_app_tool_id(app_id=app_id),
        source_kind=RunSourceKind.CURATED_APP,
        version_id=None,
        curated_app_id=app_id,
        curated_app_version="1.0.0",
        context=RunContext.PRODUCTION,
        requested_by_user_id=user_id,
        status=RunStatus.SUCCEEDED,
        requested_at=now - timedelta(seconds=30),
        started_at=now - timedelta(seconds=30),
        finished_at=now - timedelta(seconds=29),
        workdir_path="app/work",
        input_filename="input.txt",
        input_size_bytes=1,
        input_manifest=input_manifest,
        html_output=None,
        stdout=None,
        stderr=None,
        artifacts_manifest={},
        error_summary=None,
    )

    sandbox_run = tool_a_old.model_copy(
        update={
            "id": uuid.uuid4(),
            "context": RunContext.SANDBOX,
            "requested_at": now,
            "started_at": now,
            "finished_at": now + timedelta(seconds=1),
        }
    )

    for run in [tool_a_old, tool_a_new, tool_b, curated_run, sandbox_run]:
        await repo.create(run=run)

    rows = await repo.list_recent_tools_for_user(user_id=user_id, limit=10)
    assert [(row.source_kind, row.tool_id) for row in rows] == [
        (RunSourceKind.CURATED_APP, curated_run.tool_id),
        (RunSourceKind.TOOL_VERSION, tool_id_a),
        (RunSourceKind.TOOL_VERSION, tool_id_b),
    ]
    assert rows[1].last_used_at == tool_a_new.requested_at

    limited_rows = await repo.list_recent_tools_for_user(user_id=user_id, limit=2)
    assert len(limited_rows) == 2
    assert limited_rows[0].last_used_at == curated_run.requested_at


@pytest.mark.integration
async def test_count_for_user_this_month_returns_correct_count(
    db_session: AsyncSession,
) -> None:
    """Test that count_for_user_this_month only counts runs from current month."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month = month_start - timedelta(days=1)

    user_id = await _create_user(db_session=db_session, now=now)
    tool_id = await _create_tool(db_session=db_session, now=now, owner_user_id=user_id)
    version_id = await _create_tool_version(
        db_session=db_session, tool_id=tool_id, created_by_user_id=user_id, now=now
    )

    repo = PostgreSQLToolRunRepository(db_session)
    input_manifest = InputManifest(files=[InputFileEntry(name="input.txt", bytes=1)])

    # Create 3 PRODUCTION runs for user THIS MONTH
    for i in range(3):
        run = ToolRun(
            id=uuid.uuid4(),
            tool_id=tool_id,
            version_id=version_id,
            context=RunContext.PRODUCTION,
            requested_by_user_id=user_id,
            status=RunStatus.SUCCEEDED,
            requested_at=now - timedelta(minutes=i),
            started_at=now - timedelta(minutes=i),
            finished_at=now - timedelta(minutes=i) + timedelta(seconds=1),
            workdir_path=f"prod-{i}/work",
            input_filename="input.txt",
            input_size_bytes=1,
            input_manifest=input_manifest,
            html_output=None,
            stdout=None,
            stderr=None,
            artifacts_manifest={},
            error_summary=None,
        )
        await repo.create(run=run)

    # Create 2 PRODUCTION runs for user LAST MONTH (should not be counted)
    for i in range(2):
        run = ToolRun(
            id=uuid.uuid4(),
            tool_id=tool_id,
            version_id=version_id,
            context=RunContext.PRODUCTION,
            requested_by_user_id=user_id,
            status=RunStatus.SUCCEEDED,
            requested_at=last_month - timedelta(days=i),
            started_at=last_month - timedelta(days=i),
            finished_at=last_month - timedelta(days=i) + timedelta(seconds=1),
            workdir_path=f"last-month-{i}/work",
            input_filename="input.txt",
            input_size_bytes=1,
            input_manifest=input_manifest,
            html_output=None,
            stdout=None,
            stderr=None,
            artifacts_manifest={},
            error_summary=None,
        )
        await repo.create(run=run)

    # Create 1 SANDBOX run for user THIS MONTH (should not be counted - wrong context)
    sandbox_run = ToolRun(
        id=uuid.uuid4(),
        tool_id=tool_id,
        version_id=version_id,
        context=RunContext.SANDBOX,
        requested_by_user_id=user_id,
        status=RunStatus.SUCCEEDED,
        requested_at=now,
        started_at=now,
        finished_at=now + timedelta(seconds=1),
        workdir_path="sandbox/work",
        input_filename="input.txt",
        input_size_bytes=1,
        input_manifest=input_manifest,
        html_output=None,
        stdout=None,
        stderr=None,
        artifacts_manifest={},
        error_summary=None,
    )
    await repo.create(run=sandbox_run)

    # Verify count for user's PRODUCTION runs THIS MONTH only
    count = await repo.count_for_user_this_month(user_id=user_id, context=RunContext.PRODUCTION)
    assert count == 3  # Only this month's production runs

    # Verify SANDBOX runs this month
    sandbox_count = await repo.count_for_user_this_month(
        user_id=user_id, context=RunContext.SANDBOX
    )
    assert sandbox_count == 1
