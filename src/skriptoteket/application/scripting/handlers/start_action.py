from __future__ import annotations

import json
from uuid import UUID

from pydantic import JsonValue

from skriptoteket.application.scripting.commands import ExecuteToolVersionCommand
from skriptoteket.application.scripting.interactive_tools import (
    StartActionCommand,
    StartActionResult,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.execution import ToolExecutionResult
from skriptoteket.domain.scripting.input_files import InputFileEntry, InputManifest
from skriptoteket.domain.scripting.models import (
    RunContext,
    RunStatus,
    finish_run,
    start_curated_app_run,
)
from skriptoteket.domain.scripting.tool_sessions import (
    normalize_tool_session_context,
    validate_expected_state_rev,
)
from skriptoteket.domain.scripting.ui.contract_v2 import ToolUiContractV2Result, UiFormAction
from skriptoteket.domain.scripting.ui.normalization import UiNormalizationResult
from skriptoteket.domain.scripting.ui.policy import UiPolicy
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import (
    CuratedAppExecutorProtocol,
    CuratedAppRegistryProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.interactive_tools import StartActionHandlerProtocol
from skriptoteket.protocols.scripting import (
    ExecuteToolVersionHandlerProtocol,
    ToolRunRepositoryProtocol,
)
from skriptoteket.protocols.scripting_ui import (
    BackendActionProviderProtocol,
    UiPayloadNormalizerProtocol,
    UiPolicyProviderProtocol,
)
from skriptoteket.protocols.session_files import SessionFileStorageProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class StartActionHandler(StartActionHandlerProtocol):
    """Start an interactive tool action (ADR-0024).

    The tool receives JSON input bytes with the shape:
    {"action_id": str, "input": {...}, "state": {...}}.
    """

    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        curated_apps: CuratedAppRegistryProtocol,
        curated_executor: CuratedAppExecutorProtocol,
        sessions: ToolSessionRepositoryProtocol,
        runs: ToolRunRepositoryProtocol,
        execute: ExecuteToolVersionHandlerProtocol,
        ui_policy_provider: UiPolicyProviderProtocol,
        backend_actions: BackendActionProviderProtocol,
        ui_normalizer: UiPayloadNormalizerProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        session_files: SessionFileStorageProtocol,
    ) -> None:
        self._uow = uow
        self._tools = tools
        self._curated_apps = curated_apps
        self._curated_executor = curated_executor
        self._sessions = sessions
        self._runs = runs
        self._execute = execute
        self._ui_policy_provider = ui_policy_provider
        self._backend_actions = backend_actions
        self._ui_normalizer = ui_normalizer
        self._clock = clock
        self._id_generator = id_generator
        self._session_files = session_files

    async def _execute_curated_app_action(
        self,
        *,
        actor: User,
        tool_id: UUID,
        current_state: dict[str, JsonValue],
        command: StartActionCommand,
        input_bytes: bytes,
    ) -> tuple[UUID, dict[str, JsonValue]]:
        app = self._curated_apps.get_by_tool_id(tool_id=tool_id)
        if app is None:
            raise not_found("Tool", str(tool_id))

        require_at_least_role(user=actor, role=app.min_role)

        profile_id = await self._ui_policy_provider.get_profile_id_for_curated_app(
            curated_app_id=app.app_id,
            actor=actor,
        )
        policy = self._ui_policy_provider.get_policy(profile_id=profile_id)
        backend_actions_list = await self._backend_actions.list_backend_actions(
            tool_id=tool_id,
            actor=actor,
            policy=policy,
        )

        now = self._clock.now()
        run_id = self._id_generator.new_uuid()
        run = start_curated_app_run(
            run_id=run_id,
            tool_id=tool_id,
            curated_app_id=app.app_id,
            curated_app_version=app.app_version,
            context=RunContext.PRODUCTION,
            requested_by_user_id=actor.id,
            workdir_path=str(run_id),
            input_filename="action.json",
            input_size_bytes=len(input_bytes),
            input_manifest=InputManifest(
                files=[InputFileEntry(name="action.json", bytes=len(input_bytes))]
            ),
            now=now,
        )

        async with self._uow:
            await self._runs.create(run=run)

        domain_error_to_raise: DomainError | None = None
        execution_result: ToolExecutionResult | None = None
        fallback_ui_result: ToolUiContractV2Result | None = None
        try:
            execution_result = await self._curated_executor.execute_action(
                run_id=run_id,
                app=app,
                actor=actor,
                action_id=command.action_id,
                input=command.input,
                state=current_state,
            )
        except DomainError as exc:
            domain_error_to_raise = exc
            fallback_ui_result = ToolUiContractV2Result(
                status="failed",
                error_summary=exc.message,
                outputs=[],
                next_actions=[],
                state=None,
                artifacts=[],
            )
        except Exception:  # noqa: BLE001
            domain_error_to_raise = DomainError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Execution failed (internal error).",
            )
            fallback_ui_result = ToolUiContractV2Result(
                status="failed",
                error_summary="Execution failed (internal error).",
                outputs=[],
                next_actions=[],
                state=None,
                artifacts=[],
            )

        finish_now = self._clock.now()
        if execution_result is None:
            execution_result = ToolExecutionResult(
                status=RunStatus.FAILED,
                stdout="",
                stderr="",
                ui_result=(
                    fallback_ui_result
                    if fallback_ui_result is not None
                    else ToolUiContractV2Result(
                        status="failed",
                        error_summary=None,
                        outputs=[],
                        next_actions=[],
                        state=None,
                        artifacts=[],
                    )
                ),
                artifacts_manifest=ArtifactsManifest(artifacts=[]),
            )

        normalization_result: UiNormalizationResult
        try:
            normalization_result = self._normalize_result(
                raw_result=execution_result.ui_result,
                backend_actions=backend_actions_list,
                policy=policy,
            )
        except DomainError as exc:
            normalization_result = self._normalize_result(
                raw_result=ToolUiContractV2Result(
                    status="failed",
                    error_summary="Execution failed (ui_payload normalization error).",
                    outputs=[],
                    next_actions=[],
                    state=None,
                    artifacts=[],
                ),
                backend_actions=backend_actions_list,
                policy=policy,
            )
            domain_error_to_raise = DomainError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Execution failed (ui_payload normalization error).",
                details=exc.details,
            )

        finished = finish_run(
            run=run,
            status=execution_result.status,
            now=finish_now,
            stdout=execution_result.stdout,
            stderr=execution_result.stderr,
            artifacts_manifest=execution_result.artifacts_manifest.model_dump(),
            error_summary=execution_result.ui_result.error_summary,
            ui_payload=normalization_result.ui_payload,
        )

        async with self._uow:
            await self._runs.update(run=finished)

        if domain_error_to_raise is not None:
            raise domain_error_to_raise

        return finished.id, normalization_result.state

    def _normalize_result(
        self,
        *,
        raw_result: ToolUiContractV2Result,
        backend_actions: list[UiFormAction],
        policy: UiPolicy,
    ) -> UiNormalizationResult:
        return self._ui_normalizer.normalize(
            raw_result=raw_result,
            backend_actions=backend_actions,
            policy=policy,
        )

    async def handle(
        self,
        *,
        actor: User,
        command: StartActionCommand,
    ) -> StartActionResult:
        context = normalize_tool_session_context(context=command.context)
        validate_expected_state_rev(expected_state_rev=command.expected_state_rev)

        active_version_id = None
        is_curated_app = False

        async with self._uow:
            tool = await self._tools.get_by_id(tool_id=command.tool_id)
            if tool is not None and tool.is_published and tool.active_version_id is not None:
                active_version_id = tool.active_version_id
            else:
                app = self._curated_apps.get_by_tool_id(tool_id=command.tool_id)
                if app is None:
                    raise not_found("Tool", str(command.tool_id))
                require_at_least_role(user=actor, role=app.min_role)
                is_curated_app = True

            session = await self._sessions.get_or_create(
                session_id=self._id_generator.new_uuid(),
                tool_id=command.tool_id,
                user_id=actor.id,
                context=context,
            )
            if session.state_rev != command.expected_state_rev:
                raise DomainError(
                    code=ErrorCode.CONFLICT,
                    message="ToolSession state_rev conflict",
                    details={
                        "tool_id": str(command.tool_id),
                        "user_id": str(actor.id),
                        "context": context,
                        "expected_state_rev": command.expected_state_rev,
                        "current_state_rev": session.state_rev,
                    },
                )

            current_state = session.state

        payload = {
            "action_id": command.action_id,
            "input": command.input,
            "state": current_state,
        }
        input_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        run_id: UUID
        normalized_state: dict[str, JsonValue]
        if is_curated_app:
            run_id, normalized_state = await self._execute_curated_app_action(
                actor=actor,
                tool_id=command.tool_id,
                current_state=current_state,
                command=command,
                input_bytes=input_bytes,
            )
        else:
            if active_version_id is None:
                raise DomainError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Internal error (missing active_version_id).",
                )
            persisted_files = await self._session_files.get_files(
                tool_id=command.tool_id,
                user_id=actor.id,
                context=context,
            )
            result = await self._execute.handle(
                actor=actor,
                command=ExecuteToolVersionCommand(
                    tool_id=command.tool_id,
                    version_id=active_version_id,
                    context=RunContext.PRODUCTION,
                    input_files=[*persisted_files, ("action.json", input_bytes)],
                ),
            )
            run_id = result.run.id
            normalized_state = result.normalized_state

        async with self._uow:
            updated_session = await self._sessions.update_state(
                tool_id=command.tool_id,
                user_id=actor.id,
                context=context,
                expected_state_rev=command.expected_state_rev,
                state=normalized_state,
            )

        return StartActionResult(run_id=run_id, state_rev=updated_session.state_rev)
