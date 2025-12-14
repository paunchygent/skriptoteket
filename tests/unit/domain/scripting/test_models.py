from datetime import datetime, timezone
from uuid import uuid4

import pytest

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.models import (
    RunContext,
    RunStatus,
    VersionState,
    create_draft_version,
    finish_tool_run,
    publish_version,
    start_tool_run,
    submit_for_review,
)


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
            created_by_user_id=user_id,
            derived_from_version_id=None,
            change_summary=None,
            now=now,
        )
    assert exc.value.code == ErrorCode.VALIDATION_ERROR

    # Test empty source code
    with pytest.raises(DomainError):
        create_draft_version(
            version_id=version_id,
            tool_id=tool_id,
            version_number=1,
            source_code="",  # Invalid
            entrypoint="main.py",
            created_by_user_id=user_id,
            derived_from_version_id=None,
            change_summary=None,
            now=now,
        )


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
        created_by_user_id=uuid4(),
        derived_from_version_id=None,
        change_summary=None,
        now=now,
    )

    reviewed = submit_for_review(
        version=draft,
        submitted_by_user_id=user_id,
        review_note="Please review",
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


def test_start_and_finish_tool_run() -> None:
    now = datetime.now(timezone.utc)
    run_id = uuid4()

    # Start
    run = start_tool_run(
        run_id=run_id,
        tool_id=uuid4(),
        version_id=uuid4(),
        context=RunContext.SANDBOX,
        requested_by_user_id=uuid4(),
        workdir_path="/tmp/run",
        input_filename="input.txt",
        input_size_bytes=100,
        now=now,
    )

    assert run.status == RunStatus.RUNNING
    assert run.started_at == now

    # Finish
    finished = finish_tool_run(
        run=run,
        status=RunStatus.SUCCEEDED,
        now=now,
        html_output="<p>Done</p>",
        stdout="ok",
        stderr=None,
        artifacts_manifest={},
        error_summary=None,
    )

    assert finished.status == RunStatus.SUCCEEDED
    assert finished.finished_at == now
