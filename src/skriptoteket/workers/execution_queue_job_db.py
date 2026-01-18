from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import cast
from uuid import UUID

import structlog
from dishka import Scope
from pydantic import JsonValue

from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.models import RunStatus, ToolRun, ToolRunJob, ToolVersion
from skriptoteket.domain.scripting.tool_run_jobs import mark_job_finished, requeue_job_with_backoff
from skriptoteket.domain.scripting.tool_runs import finish_run, requeue_running_run
from skriptoteket.domain.scripting.tool_settings import (
    compute_settings_session_context,
    normalize_tool_settings_values,
)
from skriptoteket.domain.scripting.ui.contract_v2 import UiFormAction
from skriptoteket.domain.scripting.ui.policy import UiPolicy
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.execution_queue import ToolRunJobRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import UserRepositoryProtocol
from skriptoteket.protocols.scripting import (
    ToolRunRepositoryProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.scripting_ui import (
    BackendActionProviderProtocol,
    UiPolicyProviderProtocol,
)
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class JobExecutionContext:
    run: ToolRun
    version: ToolVersion
    actor: User
    memory_json: bytes
    backend_actions: list[UiFormAction]
    policy: UiPolicy


async def load_execution_context(
    *,
    container,
    run_id: UUID,
    ui_policy_provider: UiPolicyProviderProtocol,
    backend_actions_provider: BackendActionProviderProtocol,
    id_generator: IdGeneratorProtocol,
) -> JobExecutionContext:
    async with container(scope=Scope.REQUEST) as request:
        uow = cast(UnitOfWorkProtocol, await request.get(UnitOfWorkProtocol))
        runs = cast(ToolRunRepositoryProtocol, await request.get(ToolRunRepositoryProtocol))
        versions = cast(
            ToolVersionRepositoryProtocol, await request.get(ToolVersionRepositoryProtocol)
        )
        users = cast(UserRepositoryProtocol, await request.get(UserRepositoryProtocol))
        sessions = cast(
            ToolSessionRepositoryProtocol, await request.get(ToolSessionRepositoryProtocol)
        )

        async with uow:
            run = await runs.get_by_id(run_id=run_id)
            if run is None:
                raise not_found("ToolRun", str(run_id))

            if run.version_id is None:
                raise DomainError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Execution queue only supports tool_version runs.",
                    details={"run_id": str(run_id)},
                )

            version = await versions.get_by_id(version_id=run.version_id)
            if version is None:
                raise not_found("ToolVersion", str(run.version_id))

            actor = await users.get_by_id(user_id=run.requested_by_user_id)
            if actor is None:
                raise not_found("User", str(run.requested_by_user_id))

            settings_values: dict[str, JsonValue] = {}
            memory_json = json.dumps(
                {"settings": settings_values},
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")

            if version.settings_schema is not None:
                context = compute_settings_session_context(settings_schema=version.settings_schema)
                session = await sessions.get_or_create(
                    session_id=id_generator.new_uuid(),
                    tool_id=run.tool_id,
                    user_id=actor.id,
                    context=context,
                )
                try:
                    settings_values = normalize_tool_settings_values(
                        settings_schema=version.settings_schema,
                        values=session.state,
                    )
                except DomainError:
                    logger.warning(
                        "Invalid persisted tool settings; ignoring",
                        run_id=str(run_id),
                        tool_id=str(run.tool_id),
                        tool_version_id=str(version.id),
                        actor_id=str(actor.id),
                    )
                    settings_values = {}
                memory_json = json.dumps(
                    {"settings": settings_values},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")

    profile_id = await ui_policy_provider.get_profile_id_for_tool(tool_id=run.tool_id, actor=actor)
    policy = ui_policy_provider.get_policy(profile_id=profile_id)
    backend_actions = await backend_actions_provider.list_backend_actions(
        tool_id=run.tool_id,
        actor=actor,
        policy=policy,
    )

    return JobExecutionContext(
        run=run,
        version=version,
        actor=actor,
        memory_json=memory_json,
        backend_actions=backend_actions,
        policy=policy,
    )


async def finalize_job(
    *,
    container,
    worker_id: str,
    run: ToolRun,
    job: ToolRunJob,
    normalized_state: dict[str, JsonValue],
    id_generator: IdGeneratorProtocol,
) -> bool:
    async with container(scope=Scope.REQUEST) as request:
        uow = cast(UnitOfWorkProtocol, await request.get(UnitOfWorkProtocol))
        runs = cast(ToolRunRepositoryProtocol, await request.get(ToolRunRepositoryProtocol))
        jobs = cast(ToolRunJobRepositoryProtocol, await request.get(ToolRunJobRepositoryProtocol))
        sessions = cast(
            ToolSessionRepositoryProtocol, await request.get(ToolSessionRepositoryProtocol)
        )

        async with uow:
            current_job = await jobs.get_by_run_id(run_id=run.id)
            if current_job is None:
                logger.warning(
                    "Job missing while finalizing",
                    run_id=str(run.id),
                    worker_id=worker_id,
                )
                return False
            if current_job.locked_by != worker_id:
                logger.warning(
                    "Lost lease before finalizing; skipping",
                    run_id=str(run.id),
                    job_id=str(current_job.id),
                    worker_id=worker_id,
                    locked_by=current_job.locked_by,
                )
                return False

            await runs.update(run=run)
            await jobs.update(job=job)

            if run.ui_payload is not None and run.ui_payload.next_actions:
                session = await sessions.get_or_create(
                    session_id=id_generator.new_uuid(),
                    tool_id=run.tool_id,
                    user_id=run.requested_by_user_id,
                    context="default",
                )
                try:
                    await sessions.update_state(
                        tool_id=run.tool_id,
                        user_id=run.requested_by_user_id,
                        context="default",
                        expected_state_rev=session.state_rev,
                        state=normalized_state,
                    )
                except DomainError:
                    logger.exception(
                        "Failed to persist normalized session state",
                        run_id=str(run.id),
                        tool_id=str(run.tool_id),
                        user_id=str(run.requested_by_user_id),
                    )

            return True


async def requeue_missing_adoptable_container(
    *,
    container,
    run: ToolRun,
    now: datetime,
    backoff_seconds: int,
    worker_id: str,
) -> None:
    backoff = timedelta(seconds=max(1, backoff_seconds))
    next_available_at = now + backoff
    async with container(scope=Scope.REQUEST) as request:
        uow = cast(UnitOfWorkProtocol, await request.get(UnitOfWorkProtocol))
        runs = cast(ToolRunRepositoryProtocol, await request.get(ToolRunRepositoryProtocol))
        jobs = cast(ToolRunJobRepositoryProtocol, await request.get(ToolRunJobRepositoryProtocol))
        async with uow:
            current_job = await jobs.get_by_run_id(run_id=run.id)
            if current_job is None:
                return
            if current_job.locked_by != worker_id:
                return
            current_run = await runs.get_by_id(run_id=run.id)
            if current_run is None:
                return
            requeued_job = requeue_job_with_backoff(
                job=current_job,
                now=now,
                available_at=next_available_at,
                last_error="Missing runner container; requeued.",
            )
            requeued_run = requeue_running_run(run=current_run, now=now)
            await jobs.update(job=requeued_job)
            await runs.update(run=requeued_run)


async def finalize_job_as_failed(
    *,
    container,
    worker_id: str,
    run_id: UUID,
    job_id: UUID,
    error_summary: str,
    clock: ClockProtocol,
) -> None:
    now = clock.now()
    async with container(scope=Scope.REQUEST) as request:
        uow = cast(UnitOfWorkProtocol, await request.get(UnitOfWorkProtocol))
        runs = cast(ToolRunRepositoryProtocol, await request.get(ToolRunRepositoryProtocol))
        jobs = cast(ToolRunJobRepositoryProtocol, await request.get(ToolRunJobRepositoryProtocol))

        async with uow:
            run = await runs.get_by_id(run_id=run_id)
            job = await jobs.get_by_run_id(run_id=run_id)
            if run is None or job is None:
                return
            if job.id != job_id:
                return
            if job.locked_by != worker_id:
                return
            if run.status is not RunStatus.RUNNING or run.started_at is None:
                return

            failed_run = finish_run(
                run=run,
                status=RunStatus.FAILED,
                now=now,
                stdout="",
                stderr="",
                artifacts_manifest={},
                error_summary=error_summary,
                ui_payload=None,
            )
            failed_job = mark_job_finished(job=job, status=RunStatus.FAILED, now=now)
            await runs.update(run=failed_run)
            await jobs.update(job=failed_job)


async def heartbeat_once(
    *,
    container,
    job_id: UUID,
    worker_id: str,
    now: datetime,
    lease_ttl: timedelta,
) -> bool:
    async with container(scope=Scope.REQUEST) as request:
        uow = cast(UnitOfWorkProtocol, await request.get(UnitOfWorkProtocol))
        jobs = cast(ToolRunJobRepositoryProtocol, await request.get(ToolRunJobRepositoryProtocol))
        async with uow:
            return await jobs.heartbeat(
                job_id=job_id,
                worker_id=worker_id,
                now=now,
                lease_ttl=lease_ttl,
            )
