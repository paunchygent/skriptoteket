from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.models import RunStatus
from skriptoteket.domain.scripting.tool_run_jobs import (
    ToolRunJob,
    enqueue_job,
    mark_job_finished,
    mark_job_started,
    requeue_job_with_backoff,
)


def test_enqueue_job_normalizes_queue_and_sets_defaults() -> None:
    now = datetime.now(timezone.utc)
    job_id = uuid4()
    run_id = uuid4()

    job = enqueue_job(
        job_id=job_id,
        run_id=run_id,
        now=now,
        queue=" default ",
        priority=5,
        max_attempts=3,
    )

    assert job.id == job_id
    assert job.run_id == run_id
    assert job.status is RunStatus.QUEUED
    assert job.queue == "default"
    assert job.priority == 5
    assert job.attempts == 0
    assert job.max_attempts == 3
    assert job.available_at == now
    assert job.locked_by is None
    assert job.locked_until is None
    assert job.last_error is None
    assert job.created_at == now
    assert job.updated_at == now
    assert job.started_at is None
    assert job.finished_at is None


def test_enqueue_job_when_queue_blank_raises_validation_error() -> None:
    now = datetime.now(timezone.utc)

    with pytest.raises(DomainError) as exc:
        enqueue_job(
            job_id=uuid4(),
            run_id=uuid4(),
            now=now,
            queue="   ",
        )

    assert exc.value.code is ErrorCode.VALIDATION_ERROR


def test_enqueue_job_when_max_attempts_invalid_raises_validation_error() -> None:
    now = datetime.now(timezone.utc)

    with pytest.raises(DomainError) as exc:
        enqueue_job(
            job_id=uuid4(),
            run_id=uuid4(),
            now=now,
            max_attempts=0,
        )

    assert exc.value.code is ErrorCode.VALIDATION_ERROR


def test_mark_job_started_transitions_to_running_and_sets_started_at() -> None:
    now = datetime.now(timezone.utc)
    job = enqueue_job(job_id=uuid4(), run_id=uuid4(), now=now)

    started = mark_job_started(job=job, now=now + timedelta(seconds=1))

    assert started.status is RunStatus.RUNNING
    assert started.started_at == now + timedelta(seconds=1)
    assert started.updated_at == now + timedelta(seconds=1)


def test_mark_job_started_when_not_queued_raises_conflict() -> None:
    now = datetime.now(timezone.utc)
    job = enqueue_job(job_id=uuid4(), run_id=uuid4(), now=now)
    running = job.model_copy(update={"status": RunStatus.RUNNING, "started_at": now})

    with pytest.raises(DomainError) as exc:
        mark_job_started(job=running, now=now)

    assert exc.value.code is ErrorCode.CONFLICT


def test_mark_job_started_when_before_available_at_raises_validation_error() -> None:
    now = datetime.now(timezone.utc)
    job = enqueue_job(job_id=uuid4(), run_id=uuid4(), now=now).model_copy(
        update={"available_at": now + timedelta(seconds=5)}
    )

    with pytest.raises(DomainError) as exc:
        mark_job_started(job=job, now=now)

    assert exc.value.code is ErrorCode.VALIDATION_ERROR


def test_mark_job_finished_transitions_to_terminal_and_clears_lease() -> None:
    now = datetime.now(timezone.utc)
    running = mark_job_started(
        job=enqueue_job(job_id=uuid4(), run_id=uuid4(), now=now), now=now
    ).model_copy(
        update={
            "locked_by": "worker-1",
            "locked_until": now + timedelta(seconds=30),
        }
    )

    finished = mark_job_finished(
        job=running, status=RunStatus.SUCCEEDED, now=now + timedelta(seconds=1)
    )

    assert finished.status is RunStatus.SUCCEEDED
    assert finished.finished_at == now + timedelta(seconds=1)
    assert finished.locked_by is None
    assert finished.locked_until is None


def test_mark_job_finished_when_not_running_raises_conflict() -> None:
    now = datetime.now(timezone.utc)
    job = enqueue_job(job_id=uuid4(), run_id=uuid4(), now=now)

    with pytest.raises(DomainError) as exc:
        mark_job_finished(job=job, status=RunStatus.SUCCEEDED, now=now)

    assert exc.value.code is ErrorCode.CONFLICT


@pytest.mark.parametrize("status", [RunStatus.QUEUED, RunStatus.RUNNING])
def test_mark_job_finished_with_non_terminal_status_raises_validation_error(
    status: RunStatus,
) -> None:
    now = datetime.now(timezone.utc)
    running = mark_job_started(job=enqueue_job(job_id=uuid4(), run_id=uuid4(), now=now), now=now)

    with pytest.raises(DomainError) as exc:
        mark_job_finished(job=running, status=status, now=now + timedelta(seconds=1))

    assert exc.value.code is ErrorCode.VALIDATION_ERROR


def test_mark_job_finished_when_before_started_at_raises_validation_error() -> None:
    now = datetime.now(timezone.utc)
    running = mark_job_started(job=enqueue_job(job_id=uuid4(), run_id=uuid4(), now=now), now=now)

    with pytest.raises(DomainError) as exc:
        mark_job_finished(job=running, status=RunStatus.SUCCEEDED, now=now - timedelta(seconds=1))

    assert exc.value.code is ErrorCode.VALIDATION_ERROR


def test_requeue_job_with_backoff_transitions_to_queued_and_updates_last_error() -> None:
    now = datetime.now(timezone.utc)
    running = mark_job_started(
        job=enqueue_job(job_id=uuid4(), run_id=uuid4(), now=now), now=now
    ).model_copy(
        update={
            "locked_by": "worker-1",
            "locked_until": now + timedelta(seconds=30),
        }
    )

    available_at = now + timedelta(seconds=10)
    requeued = requeue_job_with_backoff(
        job=running,
        now=now + timedelta(seconds=1),
        available_at=available_at,
        last_error="Missing runner container; requeued.",
    )

    assert requeued.status is RunStatus.QUEUED
    assert requeued.available_at == available_at
    assert requeued.locked_by is None
    assert requeued.locked_until is None
    assert requeued.last_error == "Missing runner container; requeued."


def test_requeue_job_with_backoff_when_not_running_raises_conflict() -> None:
    now = datetime.now(timezone.utc)
    queued = enqueue_job(job_id=uuid4(), run_id=uuid4(), now=now)

    with pytest.raises(DomainError) as exc:
        requeue_job_with_backoff(
            job=queued,
            now=now,
            available_at=now + timedelta(seconds=1),
        )

    assert exc.value.code is ErrorCode.CONFLICT


def test_requeue_job_with_backoff_when_available_at_before_now_raises_validation_error() -> None:
    now = datetime.now(timezone.utc)
    running = mark_job_started(job=enqueue_job(job_id=uuid4(), run_id=uuid4(), now=now), now=now)

    with pytest.raises(DomainError) as exc:
        requeue_job_with_backoff(
            job=running,
            now=now,
            available_at=now - timedelta(seconds=1),
        )

    assert exc.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize(
    ("attempts", "max_attempts"),
    [(-1, 1), (0, 0), (2, 1)],
)
def test_tool_run_job_validates_attempts_ranges(attempts: int, max_attempts: int) -> None:
    now = datetime.now(timezone.utc)

    with pytest.raises(ValueError):
        ToolRunJob(
            id=uuid4(),
            run_id=uuid4(),
            status=RunStatus.QUEUED,
            attempts=attempts,
            max_attempts=max_attempts,
            available_at=now,
            created_at=now,
            updated_at=now,
        )
