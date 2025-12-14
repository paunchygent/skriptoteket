from __future__ import annotations

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
    save_draft_snapshot,
    start_tool_run,
    submit_for_review,
)


def test_create_draft_version_sets_state_and_hash() -> None:
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    version = create_draft_version(
        version_id=uuid4(),
        tool_id=uuid4(),
        version_number=1,
        source_code="print('hello')\n",
        entrypoint="run_tool",
        created_by_user_id=uuid4(),
        derived_from_version_id=None,
        change_summary="  Added greeting  ",
        now=now,
    )

    assert version.state is VersionState.DRAFT
    assert version.version_number == 1
    assert version.content_hash
    assert version.change_summary == "Added greeting"


def test_save_draft_snapshot_creates_new_version_derived_from_previous() -> None:
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    tool_id = uuid4()
    previous = create_draft_version(
        version_id=uuid4(),
        tool_id=tool_id,
        version_number=1,
        source_code="print('v1')\n",
        entrypoint="run_tool",
        created_by_user_id=uuid4(),
        derived_from_version_id=None,
        change_summary=None,
        now=now,
    )

    newer = save_draft_snapshot(
        previous_version=previous,
        new_version_id=uuid4(),
        new_version_number=2,
        source_code="print('v2')\n",
        entrypoint="run_tool",
        saved_by_user_id=uuid4(),
        change_summary=None,
        now=now,
    )

    assert newer.tool_id == tool_id
    assert newer.state is VersionState.DRAFT
    assert newer.version_number == 2
    assert newer.derived_from_version_id == previous.id


def test_submit_for_review_sets_submission_audit_fields() -> None:
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    user_id = uuid4()
    version = create_draft_version(
        version_id=uuid4(),
        tool_id=uuid4(),
        version_number=1,
        source_code="print('hello')\n",
        entrypoint="run_tool",
        created_by_user_id=user_id,
        derived_from_version_id=None,
        change_summary=None,
        now=now,
    )

    submitted = submit_for_review(
        version=version,
        submitted_by_user_id=user_id,
        review_note="  Please review  ",
        now=now,
    )

    assert submitted.state is VersionState.IN_REVIEW
    assert submitted.submitted_for_review_by_user_id == user_id
    assert submitted.submitted_for_review_at == now
    assert submitted.review_note == "Please review"


def test_submit_for_review_raises_for_non_draft() -> None:
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    version = create_draft_version(
        version_id=uuid4(),
        tool_id=uuid4(),
        version_number=1,
        source_code="print('hello')\n",
        entrypoint="run_tool",
        created_by_user_id=uuid4(),
        derived_from_version_id=None,
        change_summary=None,
        now=now,
    )
    submitted = submit_for_review(
        version=version,
        submitted_by_user_id=uuid4(),
        review_note=None,
        now=now,
    )

    with pytest.raises(DomainError) as exc_info:
        submit_for_review(
            version=submitted,
            submitted_by_user_id=uuid4(),
            review_note=None,
            now=now,
        )

    assert exc_info.value.code == ErrorCode.CONFLICT


def test_publish_version_archives_reviewed_and_previous_active_and_creates_new_active() -> None:
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    tool_id = uuid4()
    reviewer = uuid4()

    draft = create_draft_version(
        version_id=uuid4(),
        tool_id=tool_id,
        version_number=3,
        source_code="print('draft')\n",
        entrypoint="run_tool",
        created_by_user_id=uuid4(),
        derived_from_version_id=None,
        change_summary="Draft changes",
        now=now,
    )
    in_review = submit_for_review(
        version=draft, submitted_by_user_id=uuid4(), review_note=None, now=now
    )

    previous_active = create_draft_version(
        version_id=uuid4(),
        tool_id=tool_id,
        version_number=2,
        source_code="print('active')\n",
        entrypoint="run_tool",
        created_by_user_id=uuid4(),
        derived_from_version_id=None,
        change_summary=None,
        now=now,
    ).model_copy(update={"state": VersionState.ACTIVE})

    result = publish_version(
        reviewed_version=in_review,
        new_active_version_id=uuid4(),
        new_active_version_number=4,
        published_by_user_id=reviewer,
        now=now,
        change_summary=None,
        previous_active_version=previous_active,
    )

    assert (
        result.new_active_version.state,
        result.new_active_version.version_number,
        result.new_active_version.derived_from_version_id,
        result.new_active_version.published_by_user_id,
        result.new_active_version.published_at,
    ) == (VersionState.ACTIVE, 4, in_review.id, reviewer, now)

    assert (
        result.archived_reviewed_version.state,
        result.archived_reviewed_version.published_by_user_id,
        result.archived_reviewed_version.published_at,
    ) == (VersionState.ARCHIVED, reviewer, now)

    assert result.archived_previous_active_version is not None
    assert result.archived_previous_active_version.state is VersionState.ARCHIVED


def test_start_and_finish_tool_run_transitions() -> None:
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    run = start_tool_run(
        run_id=uuid4(),
        tool_id=uuid4(),
        version_id=uuid4(),
        context=RunContext.SANDBOX,
        requested_by_user_id=uuid4(),
        workdir_path="123e4567-e89b-12d3-a456-426614174000/",
        input_filename="file.csv",
        input_size_bytes=123,
        now=now,
    )

    finished = finish_tool_run(
        run=run,
        status=RunStatus.SUCCEEDED,
        now=now,
        html_output="<p>ok</p>",
        stdout="",
        stderr="",
        artifacts_manifest={},
        error_summary=None,
    )

    assert finished.status is RunStatus.SUCCEEDED
    assert finished.finished_at == now
