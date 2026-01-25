from __future__ import annotations

import time

from pydantic import JsonValue

from skriptoteket.application.scripting.commands import (
    ExecuteToolVersionCommand,
    ExecuteToolVersionResult,
    ToolVersionOverride,
)
from skriptoteket.application.scripting.handlers.execute_tool_version_pipeline import (
    execute_tool_version_pipeline,
)
from skriptoteket.application.scripting.run_input_resolution import resolve_run_inputs
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.models import (
    ToolVersion,
    compute_content_hash,
    enqueue_tool_version_run,
)
from skriptoteket.domain.scripting.tool_inputs import (
    normalize_tool_input_schema,
    normalize_tool_input_values,
    validate_input_files_count,
)
from skriptoteket.domain.scripting.tool_run_jobs import enqueue_job
from skriptoteket.domain.scripting.tool_settings import (
    normalize_tool_settings_schema,
)
from skriptoteket.observability.tracing import get_tracer, trace_operation
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.execution_queue import ToolRunJobRepositoryProtocol
from skriptoteket.protocols.file_refs import FileRefResolverProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.promotions import PromotionApplierProtocol
from skriptoteket.protocols.run_inputs import RunInputStorageProtocol
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
        if override.input_schema is None:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="input_schema cannot be null",
            )
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


def _count_files_by_field(
    *,
    input_files_by_field: dict[str, list[tuple[str, bytes]]],
    file_refs_by_field: dict[str, list[str]],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for field, files in input_files_by_field.items():
        counts[field] = counts.get(field, 0) + len(files)
    for field, refs in file_refs_by_field.items():
        counts[field] = counts.get(field, 0) + len(refs)
    return counts


def _merge_refs_into_values(
    *,
    values: dict[str, JsonValue],
    refs_by_field: dict[str, list[str]],
) -> dict[str, JsonValue]:
    merged = dict(values)
    for field, refs in refs_by_field.items():
        if field in merged:
            raise validation_error(
                "File refs conflict with input values",
                details={"field": field},
            )
        refs_value: list[JsonValue] = list(refs)
        merged[field] = refs_value
    return merged


def _merge_refs_into_action_payload(
    *,
    action_payload: dict[str, JsonValue],
    refs_by_field: dict[str, list[str]],
) -> dict[str, JsonValue]:
    if not refs_by_field:
        return action_payload
    raw_input = action_payload.get("input")
    input_values = raw_input if isinstance(raw_input, dict) else {}
    merged_input = dict(input_values)
    for field, refs in refs_by_field.items():
        if field in merged_input:
            raise validation_error(
                "File refs conflict with action input values",
                details={"field": field},
            )
        refs_value: list[JsonValue] = list(refs)
        merged_input[field] = refs_value
    return {
        **action_payload,
        "input": merged_input,
    }


class ExecuteToolVersionHandler(ExecuteToolVersionHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        settings: Settings,
        versions: ToolVersionRepositoryProtocol,
        runs: ToolRunRepositoryProtocol,
        jobs: ToolRunJobRepositoryProtocol,
        run_inputs: RunInputStorageProtocol,
        sessions: ToolSessionRepositoryProtocol,
        runner: ToolRunnerProtocol,
        file_refs: FileRefResolverProtocol,
        promotion_applier: PromotionApplierProtocol,
        ui_policy_provider: UiPolicyProviderProtocol,
        backend_actions: BackendActionProviderProtocol,
        ui_normalizer: UiPayloadNormalizerProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._settings = settings
        self._versions = versions
        self._runs = runs
        self._jobs = jobs
        self._run_inputs = run_inputs
        self._sessions = sessions
        self._runner = runner
        self._file_refs = file_refs
        self._promotion_applier = promotion_applier
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

        now = self._clock.now()
        run_id = self._id_generator.new_uuid()

        queue_enabled = bool(self._settings.RUNNER_QUEUE_ENABLED)
        can_queue = (
            queue_enabled
            and command.context.value == "production"
            and command.action_payload is None
            and command.version_override is None
        )

        input_schema = normalize_tool_input_schema(input_schema=version.input_schema)
        if command.action_payload is None:
            validate_input_files_count(
                input_schema=input_schema,
                files_count_by_field=_count_files_by_field(
                    input_files_by_field=command.input_files_by_field,
                    file_refs_by_field=command.file_refs_by_field,
                ),
            )
        normalized_input_values = normalize_tool_input_values(
            input_schema=input_schema,
            values=command.input_values,
        )

        resolved_inputs = await resolve_run_inputs(
            tool_id=command.tool_id,
            user_id=actor.id,
            context=command.session_context,
            input_files_by_field=command.input_files_by_field,
            file_refs_by_field=command.file_refs_by_field,
            file_ref_resolver=self._file_refs,
        )
        input_values_for_run = normalized_input_values
        action_payload = command.action_payload
        if command.action_payload is None:
            input_values_for_run = _merge_refs_into_values(
                values=normalized_input_values,
                refs_by_field=resolved_inputs.refs_by_field,
            )
        else:
            action_payload = _merge_refs_into_action_payload(
                action_payload=command.action_payload,
                refs_by_field=resolved_inputs.refs_by_field,
            )

        if can_queue:
            primary_filename = resolved_inputs.primary_filename
            total_size_bytes = resolved_inputs.total_size_bytes
            input_manifest = resolved_inputs.manifest

            queued_run = enqueue_tool_version_run(
                run_id=run_id,
                tool_id=command.tool_id,
                version_id=command.version_id,
                snapshot_id=command.snapshot_id,
                context=command.context,
                requested_by_user_id=actor.id,
                session_context=command.session_context,
                workdir_path=str(run_id),
                input_filename=primary_filename,
                input_size_bytes=total_size_bytes,
                input_manifest=input_manifest,
                input_values=input_values_for_run,
                now=now,
            )

            max_attempts = max(1, int(self._settings.RUNNER_QUEUE_MAX_ATTEMPTS))
            job_id = self._id_generator.new_uuid()
            queued_job = enqueue_job(
                job_id=job_id,
                run_id=run_id,
                now=now,
                queue="default",
                priority=0,
                max_attempts=max_attempts,
            )

            async with self._uow:
                await self._runs.create(run=queued_run)
                await self._jobs.create(job=queued_job)
                if resolved_inputs.files:
                    await self._run_inputs.store(run_id=run_id, files=resolved_inputs.files)

            return ExecuteToolVersionResult(run=queued_run)

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
            updated_command = command
            if action_payload is not None and action_payload is not command.action_payload:
                updated_command = command.model_copy(
                    update={"action_payload": action_payload},
                )
            return await execute_tool_version_pipeline(
                span=span,
                actor=actor,
                command=updated_command,
                resolved_inputs=resolved_inputs,
                normalized_input_values=input_values_for_run,
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
                promotion_applier=self._promotion_applier,
                clock=self._clock,
                id_generator=self._id_generator,
            )
