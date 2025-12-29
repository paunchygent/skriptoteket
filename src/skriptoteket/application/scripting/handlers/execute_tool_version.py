from __future__ import annotations

import time

from skriptoteket.application.scripting.commands import (
    ExecuteToolVersionCommand,
    ExecuteToolVersionResult,
    ToolVersionOverride,
)
from skriptoteket.application.scripting.handlers.execute_tool_version_pipeline import (
    execute_tool_version_pipeline,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.models import ToolVersion, compute_content_hash
from skriptoteket.domain.scripting.tool_inputs import (
    normalize_tool_input_schema,
)
from skriptoteket.domain.scripting.tool_settings import (
    normalize_tool_settings_schema,
)
from skriptoteket.observability.tracing import get_tracer, trace_operation
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.runner import ToolRunnerProtocol
from skriptoteket.protocols.scripting import (
    ExecuteToolVersionHandlerProtocol,
    ToolRunRepositoryProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.scripting_ui import (
    BackendActionProviderProtocol,
    UiPayloadNormalizerProtocol,
    UiPolicyProviderProtocol,
)
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


def _apply_version_override(
    *,
    version: ToolVersion,
    override: ToolVersionOverride,
) -> ToolVersion:
    updated: dict[str, object] = {}
    fields_set = override.model_fields_set

    entrypoint = None
    if "entrypoint" in fields_set and override.entrypoint is not None:
        entrypoint = override.entrypoint
    source_code = None
    if "source_code" in fields_set and override.source_code is not None:
        source_code = override.source_code
    if entrypoint is not None:
        updated["entrypoint"] = entrypoint
    if source_code is not None:
        updated["source_code"] = source_code
    if "settings_schema" in fields_set:
        updated["settings_schema"] = normalize_tool_settings_schema(
            settings_schema=override.settings_schema
        )
    if "input_schema" in fields_set:
        updated["input_schema"] = normalize_tool_input_schema(input_schema=override.input_schema)
    if "usage_instructions" in fields_set:
        updated["usage_instructions"] = override.usage_instructions

    if not updated:
        return version

    entrypoint = entrypoint or version.entrypoint
    source_code = source_code or version.source_code
    updated["content_hash"] = compute_content_hash(
        entrypoint=entrypoint,
        source_code=source_code,
    )

    return version.model_copy(update=updated)


class ExecuteToolVersionHandler(ExecuteToolVersionHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        versions: ToolVersionRepositoryProtocol,
        runs: ToolRunRepositoryProtocol,
        sessions: ToolSessionRepositoryProtocol,
        runner: ToolRunnerProtocol,
        ui_policy_provider: UiPolicyProviderProtocol,
        backend_actions: BackendActionProviderProtocol,
        ui_normalizer: UiPayloadNormalizerProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._versions = versions
        self._runs = runs
        self._sessions = sessions
        self._runner = runner
        self._ui_policy_provider = ui_policy_provider
        self._backend_actions = backend_actions
        self._ui_normalizer = ui_normalizer
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        command: ExecuteToolVersionCommand,
    ) -> ExecuteToolVersionResult:
        started_at = time.monotonic()
        version = await self._versions.get_by_id(version_id=command.version_id)
        if version is None:
            raise not_found("ToolVersion", str(command.version_id))
        if version.tool_id != command.tool_id:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message="ToolVersion does not belong to the specified Tool",
                details={
                    "tool_id": str(command.tool_id),
                    "version_id": str(command.version_id),
                    "version_tool_id": str(version.tool_id),
                },
            )
        if command.version_override is not None:
            version = _apply_version_override(version=version, override=command.version_override)

        profile_id = await self._ui_policy_provider.get_profile_id_for_tool(
            tool_id=command.tool_id,
            actor=actor,
        )
        policy = self._ui_policy_provider.get_policy(profile_id=profile_id)
        backend_actions_list = await self._backend_actions.list_backend_actions(
            tool_id=command.tool_id,
            actor=actor,
            policy=policy,
        )

        now = self._clock.now()
        run_id = self._id_generator.new_uuid()

        # Start tracing span for execution
        tracer = get_tracer("skriptoteket")
        with trace_operation(
            tracer,
            "execute_tool_version",
            {
                "tool.id": str(command.tool_id),
                "version.id": str(command.version_id),
                "run.id": str(run_id),
                "run.context": command.context.value,
                "actor.id": str(actor.id),
            },
        ) as span:
            return await execute_tool_version_pipeline(
                span=span,
                actor=actor,
                command=command,
                run_id=run_id,
                version=version,
                now=now,
                backend_actions_list=backend_actions_list,
                policy=policy,
                started_at=started_at,
                uow=self._uow,
                runs=self._runs,
                sessions=self._sessions,
                runner=self._runner,
                ui_normalizer=self._ui_normalizer,
                clock=self._clock,
                id_generator=self._id_generator,
            )
