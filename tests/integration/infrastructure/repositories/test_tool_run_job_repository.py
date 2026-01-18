from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.models import AuthProvider, Role
from skriptoteket.domain.scripting.input_files import InputManifest
from skriptoteket.domain.scripting.models import (
    RunContext,
    RunStatus,
    enqueue_tool_version_run,
    start_tool_version_run,
)
from skriptoteket.domain.scripting.tool_run_jobs import enqueue_job, mark_job_started
from skriptoteket.domain.scripting.tool_versions import VersionState
from skriptoteket.infrastructure.db.models.tool import ToolModel
from skriptoteket.infrastructure.db.models.tool_version import ToolVersionModel
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.repositories.tool_run_job_repository import (
    PostgreSQLToolRunJobRepository,
)
from skriptoteket.infrastructure.repositories.tool_run_repository import PostgreSQLToolRunRepository

pytestmark = pytest.mark.asyncio(loop_scope="module")


async def _create_user(*, db_session: AsyncSession, now: datetime) -> uuid.UUID:
    user_id = uuid.uuid4()
    db_session.add(
        UserModel(
            id=user_id,
            email=f"queue-{user_id.hex[:8]}@example.com",
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
            settings_schema=None,
            input_schema=[],
            usage_instructions=None,
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
async def test_claim_next_adopts_running_jobs_before_queued(db_session: AsyncSession) -> None:
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    actor_id = await _create_user(db_session=db_session, now=now)
    tool_id = await _create_tool(db_session=db_session, now=now, owner_user_id=actor_id)
    version_id = await _create_tool_version(
        db_session=db_session,
        tool_id=tool_id,
        created_by_user_id=actor_id,
        now=now,
    )

    runs = PostgreSQLToolRunRepository(db_session)
    jobs = PostgreSQLToolRunJobRepository(db_session)

    run_running_id = uuid.uuid4()
    running_run = start_tool_version_run(
        run_id=run_running_id,
        tool_id=tool_id,
        version_id=version_id,
        context=RunContext.PRODUCTION,
        requested_by_user_id=actor_id,
        workdir_path=str(run_running_id),
        input_filename=None,
        input_size_bytes=0,
        input_manifest=InputManifest(),
        now=now - timedelta(seconds=60),
    )
    await runs.create(run=running_run)

    adoptable_job = mark_job_started(
        job=enqueue_job(
            job_id=uuid.uuid4(), run_id=run_running_id, now=now - timedelta(seconds=60)
        ),
        now=running_run.requested_at,
    ).model_copy(
        update={
            "attempts": 1,
            "max_attempts": 3,
            "locked_by": None,
            "locked_until": None,
        }
    )
    await jobs.create(job=adoptable_job)

    run_queued_id = uuid.uuid4()
    queued_run = enqueue_tool_version_run(
        run_id=run_queued_id,
        tool_id=tool_id,
        version_id=version_id,
        context=RunContext.PRODUCTION,
        requested_by_user_id=actor_id,
        workdir_path=str(run_queued_id),
        input_filename=None,
        input_size_bytes=0,
        input_manifest=InputManifest(),
        now=now - timedelta(seconds=30),
    )
    await runs.create(run=queued_run)

    queued_job = enqueue_job(
        job_id=uuid.uuid4(), run_id=run_queued_id, now=now - timedelta(seconds=30)
    ).model_copy(update={"priority": 999})
    await jobs.create(job=queued_job)

    lease_ttl = timedelta(seconds=30)
    claim = await jobs.claim_next(
        worker_id="worker-1",
        now=now,
        lease_ttl=lease_ttl,
        queue="default",
    )

    assert claim is not None
    assert claim.is_adoption is True
    assert claim.job.run_id == run_running_id
    assert claim.job.attempts == 1
    assert claim.job.locked_by == "worker-1"
    assert claim.job.locked_until == now + lease_ttl

    queued_job_again = await jobs.get_by_run_id(run_id=run_queued_id)
    assert queued_job_again is not None
    assert queued_job_again.status is RunStatus.QUEUED
    assert queued_job_again.locked_by is None
    assert queued_job_again.locked_until is None


@pytest.mark.integration
async def test_claim_next_transitions_queued_to_running_and_updates_run(
    db_session: AsyncSession,
) -> None:
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    actor_id = await _create_user(db_session=db_session, now=now)
    tool_id = await _create_tool(db_session=db_session, now=now, owner_user_id=actor_id)
    version_id = await _create_tool_version(
        db_session=db_session,
        tool_id=tool_id,
        created_by_user_id=actor_id,
        now=now,
    )

    runs = PostgreSQLToolRunRepository(db_session)
    jobs = PostgreSQLToolRunJobRepository(db_session)

    run_id = uuid.uuid4()
    queued_run = enqueue_tool_version_run(
        run_id=run_id,
        tool_id=tool_id,
        version_id=version_id,
        context=RunContext.PRODUCTION,
        requested_by_user_id=actor_id,
        workdir_path=str(run_id),
        input_filename=None,
        input_size_bytes=0,
        input_manifest=InputManifest(),
        now=now - timedelta(seconds=5),
    )
    await runs.create(run=queued_run)

    queued_job = enqueue_job(
        job_id=uuid.uuid4(), run_id=run_id, now=now - timedelta(seconds=5)
    ).model_copy(update={"max_attempts": 3})
    await jobs.create(job=queued_job)

    run_before = await runs.get_by_id(run_id=run_id)
    job_before = await jobs.get_by_run_id(run_id=run_id)
    assert (
        run_before is not None
        and run_before.status is RunStatus.QUEUED
        and run_before.started_at is None
    )
    assert (
        job_before is not None
        and job_before.status is RunStatus.QUEUED
        and job_before.started_at is None
    )
    assert job_before.attempts == 0

    lease_ttl = timedelta(seconds=30)
    claim = await jobs.claim_next(
        worker_id="worker-1", now=now, lease_ttl=lease_ttl, queue="default"
    )

    assert claim is not None
    assert claim.is_adoption is False
    assert claim.job.run_id == run_id
    assert claim.job.status is RunStatus.RUNNING
    assert claim.job.attempts == 1
    assert claim.job.locked_by == "worker-1"
    assert claim.job.locked_until == now + lease_ttl
    assert claim.job.started_at == now

    run_after = await runs.get_by_id(run_id=run_id)
    assert run_after is not None
    assert run_after.status is RunStatus.RUNNING
    assert run_after.started_at == now


@pytest.mark.integration
async def test_heartbeat_returns_true_only_when_locked_by_matches(db_session: AsyncSession) -> None:
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    actor_id = await _create_user(db_session=db_session, now=now)
    tool_id = await _create_tool(db_session=db_session, now=now, owner_user_id=actor_id)
    version_id = await _create_tool_version(
        db_session=db_session,
        tool_id=tool_id,
        created_by_user_id=actor_id,
        now=now,
    )

    runs = PostgreSQLToolRunRepository(db_session)
    jobs = PostgreSQLToolRunJobRepository(db_session)

    run_id = uuid.uuid4()
    running_run = start_tool_version_run(
        run_id=run_id,
        tool_id=tool_id,
        version_id=version_id,
        context=RunContext.PRODUCTION,
        requested_by_user_id=actor_id,
        workdir_path=str(run_id),
        input_filename=None,
        input_size_bytes=0,
        input_manifest=InputManifest(),
        now=now - timedelta(seconds=60),
    )
    await runs.create(run=running_run)

    job = mark_job_started(
        job=enqueue_job(job_id=uuid.uuid4(), run_id=run_id, now=now), now=now
    ).model_copy(
        update={
            "attempts": 1,
            "max_attempts": 3,
            "locked_by": "worker-1",
            "locked_until": now + timedelta(seconds=10),
        }
    )
    await jobs.create(job=job)

    lease_ttl = timedelta(seconds=30)
    ok = await jobs.heartbeat(
        job_id=job.id,
        worker_id="worker-1",
        now=now,
        lease_ttl=lease_ttl,
    )
    assert ok is True

    ok_other = await jobs.heartbeat(
        job_id=job.id,
        worker_id="worker-2",
        now=now,
        lease_ttl=lease_ttl,
    )
    assert ok_other is False

    refreshed = await jobs.get_by_run_id(run_id=run_id)
    assert refreshed is not None
    assert refreshed.locked_by == "worker-1"
    assert refreshed.locked_until == now + lease_ttl


@pytest.mark.integration
async def test_clear_stale_leases_clears_running_leases_and_returns_count(
    db_session: AsyncSession,
) -> None:
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    actor_id = await _create_user(db_session=db_session, now=now)
    tool_id = await _create_tool(db_session=db_session, now=now, owner_user_id=actor_id)
    version_id = await _create_tool_version(
        db_session=db_session,
        tool_id=tool_id,
        created_by_user_id=actor_id,
        now=now,
    )

    runs = PostgreSQLToolRunRepository(db_session)
    jobs = PostgreSQLToolRunJobRepository(db_session)

    stale_run_id = uuid.uuid4()
    await runs.create(
        run=start_tool_version_run(
            run_id=stale_run_id,
            tool_id=tool_id,
            version_id=version_id,
            context=RunContext.PRODUCTION,
            requested_by_user_id=actor_id,
            workdir_path=str(stale_run_id),
            input_filename=None,
            input_size_bytes=0,
            input_manifest=InputManifest(),
            now=now - timedelta(seconds=60),
        )
    )
    await jobs.create(
        job=mark_job_started(
            job=enqueue_job(
                job_id=uuid.uuid4(),
                run_id=stale_run_id,
                now=now - timedelta(seconds=60),
            ),
            now=now - timedelta(seconds=60),
        ).model_copy(
            update={
                "attempts": 1,
                "locked_by": "worker-1",
                "locked_until": now - timedelta(seconds=1),
            }
        )
    )

    fresh_run_id = uuid.uuid4()
    await runs.create(
        run=start_tool_version_run(
            run_id=fresh_run_id,
            tool_id=tool_id,
            version_id=version_id,
            context=RunContext.PRODUCTION,
            requested_by_user_id=actor_id,
            workdir_path=str(fresh_run_id),
            input_filename=None,
            input_size_bytes=0,
            input_manifest=InputManifest(),
            now=now - timedelta(seconds=60),
        )
    )
    await jobs.create(
        job=mark_job_started(
            job=enqueue_job(
                job_id=uuid.uuid4(),
                run_id=fresh_run_id,
                now=now - timedelta(seconds=60),
            ),
            now=now - timedelta(seconds=60),
        ).model_copy(
            update={
                "attempts": 1,
                "locked_by": "worker-2",
                "locked_until": now + timedelta(seconds=60),
            }
        )
    )

    queued_run_id = uuid.uuid4()
    await runs.create(
        run=enqueue_tool_version_run(
            run_id=queued_run_id,
            tool_id=tool_id,
            version_id=version_id,
            context=RunContext.PRODUCTION,
            requested_by_user_id=actor_id,
            workdir_path=str(queued_run_id),
            input_filename=None,
            input_size_bytes=0,
            input_manifest=InputManifest(),
            now=now - timedelta(seconds=5),
        )
    )
    await jobs.create(
        job=enqueue_job(
            job_id=uuid.uuid4(), run_id=queued_run_id, now=now - timedelta(seconds=5)
        ).model_copy(update={"locked_by": "worker-3", "locked_until": now - timedelta(seconds=1)})
    )

    cleared = await jobs.clear_stale_leases(now=now)
    assert cleared == 1

    stale_job = await jobs.get_by_run_id(run_id=stale_run_id)
    assert stale_job is not None
    assert stale_job.status is RunStatus.RUNNING
    assert stale_job.locked_by is None
    assert stale_job.locked_until is None

    fresh_job = await jobs.get_by_run_id(run_id=fresh_run_id)
    assert fresh_job is not None
    assert fresh_job.locked_by == "worker-2"
    assert fresh_job.locked_until is not None and fresh_job.locked_until > now

    queued_job = await jobs.get_by_run_id(run_id=queued_run_id)
    assert queued_job is not None
    assert queued_job.status is RunStatus.QUEUED
    assert queued_job.locked_by == "worker-3"
    assert queued_job.locked_until is not None and queued_job.locked_until < now
