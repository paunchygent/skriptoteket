from datetime import datetime, timezone
from uuid import uuid4

import pytest

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.input_files import InputFileEntry, InputManifest
from skriptoteket.domain.scripting.models import (
    RunContext,
    RunStatus,
    ToolVersion,
    VersionState,
    create_draft_version,
    finish_run,
    publish_version,
    save_draft_snapshot,
    start_tool_version_run,
    submit_for_review,
)
from skriptoteket.domain.scripting.ui.contract_v2 import UiPayloadV2


def test_create_draft_version_success() -> None:
    version_id = uuid4()
    tool_id = uuid4()
    user_id = uuid4()
    now = datetime.now(timezone.utc)

    version = create_draft_version(
        version_id=version_id,
        tool_id=tool_id,
        version_number=1,
        source_code="print('hello')",
        entrypoint="main.py",
        input_schema=[],
        created_by_user_id=user_id,
        derived_from_version_id=None,
        change_summary="Initial",
        now=now,
    )

    assert version.id == version_id
    assert version.state == VersionState.DRAFT
    assert version.version_number == 1
    assert version.content_hash  # Should be computed
    assert version.source_code == "print('hello')"


def test_create_draft_version_validation() -> None:
    version_id = uuid4()
    tool_id = uuid4()
    user_id = uuid4()
    now = datetime.now(timezone.utc)

    # Test invalid version number
    with pytest.raises(DomainError) as exc:
        create_draft_version(
            version_id=version_id,
            tool_id=tool_id,
            version_number=0,  # Invalid
            source_code="code",
            entrypoint="main.py",
            input_schema=[],
            created_by_user_id=user_id,
            derived_from_version_id=None,
            change_summary=None,
            now=now,
        )
    assert exc.value.code == ErrorCode.VALIDATION_ERROR

    # Test empty source code
    with pytest.raises(DomainError) as exc:
        create_draft_version(
            version_id=version_id,
            tool_id=tool_id,
            version_number=1,
            source_code="",  # Invalid
            entrypoint="main.py",
            input_schema=[],
            created_by_user_id=user_id,
            derived_from_version_id=None,
            change_summary=None,
            now=now,
        )
    assert exc.value.code == ErrorCode.VALIDATION_ERROR

    # Test invalid entrypoint (empty)
    with pytest.raises(DomainError) as exc:
        create_draft_version(
            version_id=version_id,
            tool_id=tool_id,
            version_number=1,
            source_code="code",
            entrypoint="   ",  # Invalid
            input_schema=[],
            created_by_user_id=user_id,
            derived_from_version_id=None,
            change_summary=None,
            now=now,
        )
    assert exc.value.code == ErrorCode.VALIDATION_ERROR

    # Test invalid entrypoint (too long)
    with pytest.raises(DomainError) as exc:
        create_draft_version(
            version_id=version_id,
            tool_id=tool_id,
            version_number=1,
            source_code="code",
            entrypoint="a" * 129,  # Invalid
            input_schema=[],
            created_by_user_id=user_id,
            derived_from_version_id=None,
            change_summary=None,
            now=now,
        )
    assert exc.value.code == ErrorCode.VALIDATION_ERROR


def test_save_draft_snapshot_success() -> None:
    now = datetime.now(timezone.utc)
    user_id = uuid4()
    new_version_id = uuid4()

    previous_draft = create_draft_version(
        version_id=uuid4(),
        tool_id=uuid4(),
        version_number=1,
        source_code="old code",
        entrypoint="main.py",
        input_schema=[],
        created_by_user_id=user_id,
        derived_from_version_id=None,
        change_summary="Initial",
        now=now,
    )

    new_draft = save_draft_snapshot(
        previous_version=previous_draft,
        new_version_id=new_version_id,
        new_version_number=2,
        source_code="new code",
        entrypoint="app.py",
        input_schema=[],
        saved_by_user_id=user_id,
        change_summary="  Updated  ",
        now=now,
    )

    assert new_draft.id == new_version_id
    assert new_draft.state == VersionState.DRAFT
    assert new_draft.version_number == 2
    assert new_draft.source_code == "new code"
    assert new_draft.entrypoint == "app.py"
    assert new_draft.derived_from_version_id == previous_draft.id
    assert new_draft.change_summary == "Updated"


def test_save_draft_snapshot_validations() -> None:
    now = datetime.now(timezone.utc)
    user_id = uuid4()

    previous_draft = create_draft_version(
        version_id=uuid4(),
        tool_id=uuid4(),
        version_number=2,
        source_code="code",
        entrypoint="main.py",
        input_schema=[],
        created_by_user_id=user_id,
        derived_from_version_id=None,
        change_summary=None,
        now=now,
    )

    # Fail if previous version is not DRAFT (hack state)
    in_review = submit_for_review(
        version=previous_draft,
        submitted_by_user_id=user_id,
        review_note=None,
        now=now,
    )
    with pytest.raises(DomainError) as exc:
        save_draft_snapshot(
            previous_version=in_review,
            new_version_id=uuid4(),
            new_version_number=3,
            source_code="code",
            entrypoint="main.py",
            input_schema=[],
            saved_by_user_id=user_id,
            change_summary=None,
            now=now,
        )
    assert exc.value.code == ErrorCode.CONFLICT

    # Fail if new version number is not incremented
    with pytest.raises(DomainError) as exc:
        save_draft_snapshot(
            previous_version=previous_draft,
            new_version_id=uuid4(),
            new_version_number=2,  # Same as previous
            source_code="code",
            entrypoint="main.py",
            input_schema=[],
            saved_by_user_id=user_id,
            change_summary=None,
            now=now,
        )
    assert exc.value.code == ErrorCode.VALIDATION_ERROR


def test_submit_for_review_success() -> None:
    now = datetime.now(timezone.utc)
    user_id = uuid4()

    # Setup DRAFT version
    draft = create_draft_version(
        version_id=uuid4(),
        tool_id=uuid4(),
        version_number=1,
        source_code="code",
        entrypoint="main.py",
        input_schema=[],
        created_by_user_id=uuid4(),
        derived_from_version_id=None,
        change_summary=None,
        now=now,
    )

    reviewed = submit_for_review(
        version=draft,
        submitted_by_user_id=user_id,
        review_note="  Please review  ",
        now=now,
    )

    assert reviewed.state == VersionState.IN_REVIEW
    assert reviewed.submitted_for_review_by_user_id == user_id
    assert reviewed.submitted_for_review_at == now
    assert reviewed.review_note == "Please review"


def test_submit_for_review_invalid_state() -> None:
    now = datetime.now(timezone.utc)

    # Setup DRAFT version and transition it manually (hack for test) or create invalid state object
    # Since model is frozen/immutable, we use submit_for_review to get IN_REVIEW first
    draft = create_draft_version(
        version_id=uuid4(),
        tool_id=uuid4(),
        version_number=1,
        source_code="code",
        entrypoint="main.py",
        input_schema=[],
        created_by_user_id=uuid4(),
        derived_from_version_id=None,
        change_summary=None,
        now=now,
    )
    in_review = submit_for_review(
        version=draft,
        submitted_by_user_id=uuid4(),
        review_note=None,
        now=now,
    )

    # Try to submit IN_REVIEW version again
    with pytest.raises(DomainError) as exc:
        submit_for_review(
            version=in_review,
            submitted_by_user_id=uuid4(),
            review_note=None,
            now=now,
        )
    assert exc.value.code == ErrorCode.CONFLICT


def test_publish_version_success() -> None:
    now = datetime.now(timezone.utc)
    publisher_id = uuid4()

    # Setup IN_REVIEW version
    draft = create_draft_version(
        version_id=uuid4(),
        tool_id=uuid4(),
        version_number=1,
        source_code="code",
        entrypoint="main.py",
        input_schema=[],
        created_by_user_id=uuid4(),
        derived_from_version_id=None,
        change_summary=None,
        now=now,
    )
    in_review = submit_for_review(
        version=draft,
        submitted_by_user_id=uuid4(),
        review_note=None,
        now=now,
    )

    new_active_id = uuid4()
    result = publish_version(
        reviewed_version=in_review,
        new_active_version_id=new_active_id,
        new_active_version_number=2,
        published_by_user_id=publisher_id,
        now=now,
        change_summary="Published v2",
        previous_active_version=None,
    )

    assert result.new_active_version.id == new_active_id
    assert result.new_active_version.state == VersionState.ACTIVE
    assert result.new_active_version.version_number == 2
    assert result.new_active_version.published_by_user_id == publisher_id

    assert result.archived_reviewed_version.id == in_review.id
    assert result.archived_reviewed_version.state == VersionState.ARCHIVED


def test_publish_version_validations() -> None:
    now = datetime.now(timezone.utc)
    publisher_id = uuid4()

    draft = create_draft_version(
        version_id=uuid4(),
        tool_id=uuid4(),
        version_number=1,
        source_code="code",
        entrypoint="main.py",
        input_schema=[],
        created_by_user_id=uuid4(),
        derived_from_version_id=None,
        change_summary=None,
        now=now,
    )
    in_review = submit_for_review(
        version=draft,
        submitted_by_user_id=uuid4(),
        review_note=None,
        now=now,
    )

    # 1. Fail if reviewed version is not IN_REVIEW
    with pytest.raises(DomainError) as exc:
        publish_version(
            reviewed_version=draft,  # Still DRAFT
            new_active_version_id=uuid4(),
            new_active_version_number=2,
            published_by_user_id=publisher_id,
            now=now,
            change_summary=None,
            previous_active_version=None,
        )
    assert exc.value.code == ErrorCode.CONFLICT

    # 2. Fail if previous_active_version belongs to different tool
    other_tool_active = ToolVersion(
        id=uuid4(),
        tool_id=uuid4(),  # Different tool
        version_number=1,
        state=VersionState.ACTIVE,
        source_code="code",
        entrypoint="main.py",
        content_hash="hash",
        created_by_user_id=uuid4(),
        created_at=now,
        published_by_user_id=uuid4(),
        published_at=now,
    )
    with pytest.raises(DomainError) as exc:
        publish_version(
            reviewed_version=in_review,
            new_active_version_id=uuid4(),
            new_active_version_number=2,
            published_by_user_id=publisher_id,
            now=now,
            change_summary=None,
            previous_active_version=other_tool_active,
        )
    assert exc.value.code == ErrorCode.VALIDATION_ERROR

    # 3. Fail if previous_active_version is not ACTIVE
    previous_archived = other_tool_active.model_copy(
        update={"tool_id": draft.tool_id, "state": VersionState.ARCHIVED}
    )
    with pytest.raises(DomainError) as exc:
        publish_version(
            reviewed_version=in_review,
            new_active_version_id=uuid4(),
            new_active_version_number=2,
            published_by_user_id=publisher_id,
            now=now,
            change_summary=None,
            previous_active_version=previous_archived,
        )
    assert exc.value.code == ErrorCode.VALIDATION_ERROR


def test_start_and_finish_tool_run() -> None:
    now = datetime.now(timezone.utc)
    run_id = uuid4()

    # Start
    run = start_tool_version_run(
        run_id=run_id,
        tool_id=uuid4(),
        version_id=uuid4(),
        context=RunContext.SANDBOX,
        requested_by_user_id=uuid4(),
        workdir_path="/tmp/run",
        input_filename="input.txt",
        input_size_bytes=100,
        input_manifest=InputManifest(files=[InputFileEntry(name="input.txt", bytes=100)]),
        now=now,
    )

    assert run.status == RunStatus.RUNNING
    assert run.started_at == now

    # Finish
    finished = finish_run(
        run=run,
        status=RunStatus.SUCCEEDED,
        now=now,
        stdout="ok",
        stderr=None,
        artifacts_manifest={},
        error_summary=None,
        ui_payload=UiPayloadV2(outputs=[], next_actions=[]),
    )

    assert finished.status == RunStatus.SUCCEEDED
    assert finished.finished_at == now


def test_start_tool_run_validation() -> None:
    now = datetime.now(timezone.utc)

    # Empty workdir
    with pytest.raises(DomainError) as exc:
        start_tool_version_run(
            run_id=uuid4(),
            tool_id=uuid4(),
            version_id=uuid4(),
            context=RunContext.SANDBOX,
            requested_by_user_id=uuid4(),
            workdir_path="  ",
            input_filename="input.txt",
            input_size_bytes=100,
            input_manifest=InputManifest(files=[InputFileEntry(name="input.txt", bytes=100)]),
            now=now,
        )
    assert exc.value.code == ErrorCode.VALIDATION_ERROR

    # Empty input filename
    with pytest.raises(DomainError) as exc:
        start_tool_version_run(
            run_id=uuid4(),
            tool_id=uuid4(),
            version_id=uuid4(),
            context=RunContext.SANDBOX,
            requested_by_user_id=uuid4(),
            workdir_path="/tmp/run",
            input_filename="  ",
            input_size_bytes=100,
            input_manifest=InputManifest(files=[InputFileEntry(name="input.txt", bytes=100)]),
            now=now,
        )
    assert exc.value.code == ErrorCode.VALIDATION_ERROR

    # Negative size
    with pytest.raises(DomainError) as exc:
        start_tool_version_run(
            run_id=uuid4(),
            tool_id=uuid4(),
            version_id=uuid4(),
            context=RunContext.SANDBOX,
            requested_by_user_id=uuid4(),
            workdir_path="/tmp/run",
            input_filename="input.txt",
            input_size_bytes=-1,
            input_manifest=InputManifest(files=[InputFileEntry(name="input.txt", bytes=100)]),
            now=now,
        )
    assert exc.value.code == ErrorCode.VALIDATION_ERROR


def test_finish_tool_run_validation() -> None:
    now = datetime.now(timezone.utc)

    run = start_tool_version_run(
        run_id=uuid4(),
        tool_id=uuid4(),
        version_id=uuid4(),
        context=RunContext.SANDBOX,
        requested_by_user_id=uuid4(),
        workdir_path="/tmp/run",
        input_filename="input.txt",
        input_size_bytes=100,
        input_manifest=InputManifest(files=[InputFileEntry(name="input.txt", bytes=100)]),
        now=now,
    )

    # 1. Fail if run already finished
    finished = finish_run(
        run=run,
        status=RunStatus.SUCCEEDED,
        now=now,
        stdout=None,
        stderr=None,
        artifacts_manifest={},
        error_summary=None,
        ui_payload=UiPayloadV2(outputs=[], next_actions=[]),
    )
    with pytest.raises(DomainError) as exc:
        finish_run(
            run=finished,
            status=RunStatus.FAILED,
            now=now,
            stdout=None,
            stderr=None,
            artifacts_manifest={},
            error_summary=None,
            ui_payload=UiPayloadV2(outputs=[], next_actions=[]),
        )
    assert exc.value.code == ErrorCode.CONFLICT

    # 2. Fail if new status is RUNNING
    with pytest.raises(DomainError) as exc:
        finish_run(
            run=run,
            status=RunStatus.RUNNING,  # Invalid
            now=now,
            stdout=None,
            stderr=None,
            artifacts_manifest={},
            error_summary=None,
            ui_payload=UiPayloadV2(outputs=[], next_actions=[]),
        )
    assert exc.value.code == ErrorCode.VALIDATION_ERROR

    # 3. Fail if finished_at before started_at
    past = datetime(2000, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(DomainError) as exc:
        finish_run(
            run=run,
            status=RunStatus.SUCCEEDED,
            now=past,
            stdout=None,
            stderr=None,
            artifacts_manifest={},
            error_summary=None,
            ui_payload=UiPayloadV2(outputs=[], next_actions=[]),
        )
    assert exc.value.code == ErrorCode.VALIDATION_ERROR
