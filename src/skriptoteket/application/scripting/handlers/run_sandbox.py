from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import timedelta
from uuid import UUID

from pydantic import BaseModel

from skriptoteket.application.scripting.commands import (
    ExecuteToolVersionCommand,
    RunSandboxCommand,
    RunSandboxResult,
    SessionFilesMode,
    ToolVersionOverride,
)
from skriptoteket.application.scripting.draft_lock_checks import require_active_draft_lock
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found, validation_error
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.domain.scripting.file_refs import build_session_file_ref
from skriptoteket.domain.scripting.models import RunContext, VersionState
from skriptoteket.domain.scripting.sandbox_snapshots import SandboxSnapshot
from skriptoteket.domain.scripting.tool_inputs import normalize_tool_input_schema
from skriptoteket.domain.scripting.tool_settings import (
    compute_sandbox_settings_context,
    normalize_tool_settings_schema,
)
from skriptoteket.domain.scripting.ui.state_update import resolve_state_update
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.draft_locks import DraftLockRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.sandbox_snapshots import SandboxSnapshotRepositoryProtocol
from skriptoteket.protocols.scripting import (
    ExecuteToolVersionHandlerProtocol,
    RunSandboxHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.session_files import (
    SessionFileContent,
    SessionFileStorageProtocol,
)
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


def _sandbox_context(snapshot_id: UUID) -> str:
    """Build sandbox session context per ADR-0044."""
    return f"sandbox:{snapshot_id}"


def _sandbox_files_context(version_id: UUID) -> str:
    """Stable sandbox file context scoped to the current draft head."""
    return f"sandbox-files:{version_id}"


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized if normalized else None


def _serialize_schema(schema: Sequence[BaseModel]) -> list[dict[str, object]]:
    return [item.model_dump(mode="json") for item in schema]


def _serialize_optional_schema(
    schema: Sequence[BaseModel] | None,
) -> list[dict[str, object]] | None:
    if schema is None:
        return None
    return _serialize_schema(schema)


def _snapshot_payload_bytes(
    *,
    entrypoint: str,
    source_code: str,
    settings_schema: Sequence[BaseModel] | None,
    input_schema: Sequence[BaseModel],
    usage_instructions: str | None,
) -> int:
    payload = {
        "entrypoint": entrypoint,
        "source_code": source_code,
        "settings_schema": _serialize_optional_schema(settings_schema),
        "input_schema": _serialize_schema(input_schema),
        "usage_instructions": usage_instructions,
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return len(canonical)


class RunSandboxHandler(RunSandboxHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        versions: ToolVersionRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        sessions: ToolSessionRepositoryProtocol,
        id_generator: IdGeneratorProtocol,
        execute: ExecuteToolVersionHandlerProtocol,
        session_files: SessionFileStorageProtocol,
        locks: DraftLockRepositoryProtocol,
        clock: ClockProtocol,
        snapshots: SandboxSnapshotRepositoryProtocol,
        settings: Settings,
    ) -> None:
        self._uow = uow
        self._versions = versions
        self._maintainers = maintainers
        self._sessions = sessions
        self._id_generator = id_generator
        self._execute = execute
        self._session_files = session_files
        self._locks = locks
        self._clock = clock
        self._snapshots = snapshots
        self._settings = settings

    async def handle(
        self,
        *,
        actor: User,
        command: RunSandboxCommand,
    ) -> RunSandboxResult:
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)
        now = self._clock.now()
        entrypoint = command.snapshot_payload.entrypoint.strip()
        if not entrypoint:
            raise validation_error("entrypoint is required")
        source_code = command.snapshot_payload.source_code
        settings_schema = normalize_tool_settings_schema(
            settings_schema=command.snapshot_payload.settings_schema
        )
        input_schema = normalize_tool_input_schema(
            input_schema=command.snapshot_payload.input_schema
        )
        usage_instructions = _normalize_optional_text(command.snapshot_payload.usage_instructions)
        payload_bytes = _snapshot_payload_bytes(
            entrypoint=entrypoint,
            source_code=source_code,
            settings_schema=settings_schema,
            input_schema=input_schema,
            usage_instructions=usage_instructions,
        )
        if payload_bytes > self._settings.SANDBOX_SNAPSHOT_MAX_BYTES:
            raise validation_error(
                "Sandbox snapshot payload exceeds size limit",
                details={
                    "payload_bytes": payload_bytes,
                    "max_bytes": self._settings.SANDBOX_SNAPSHOT_MAX_BYTES,
                },
            )
        snapshot_id = self._id_generator.new_uuid()
        settings_context: str | None = None

        async with self._uow:
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

            if actor.role is Role.CONTRIBUTOR:
                is_tool_maintainer = await self._maintainers.is_maintainer(
                    tool_id=version.tool_id,
                    user_id=actor.id,
                )
                if not is_tool_maintainer:
                    raise DomainError(
                        code=ErrorCode.FORBIDDEN,
                        message="Insufficient permissions",
                        details={"tool_id": str(version.tool_id)},
                    )
            if actor.role is Role.CONTRIBUTOR and version.created_by_user_id != actor.id:
                raise DomainError(
                    code=ErrorCode.FORBIDDEN,
                    message="Cannot run another user's draft in sandbox",
                    details={
                        "actor_user_id": str(actor.id),
                        "version_id": str(version.id),
                        "created_by_user_id": str(version.created_by_user_id),
                    },
                )

            draft_versions = await self._versions.list_for_tool(
                tool_id=version.tool_id,
                states={VersionState.DRAFT},
                limit=1,
            )
            if draft_versions:
                draft_head = draft_versions[0]
                if version.id != draft_head.id:
                    raise DomainError(
                        code=ErrorCode.CONFLICT,
                        message="Sandbox runs require the current draft head",
                        details={
                            "tool_id": str(version.tool_id),
                            "version_id": str(version.id),
                            "draft_head_id": str(draft_head.id),
                        },
                    )
                await require_active_draft_lock(
                    locks=self._locks,
                    tool_id=version.tool_id,
                    draft_head_id=draft_head.id,
                    actor=actor,
                    now=now,
                )

            if settings_schema is not None:
                settings_context = compute_sandbox_settings_context(
                    draft_head_id=version.id,
                    settings_schema=settings_schema,
                )

            snapshot = SandboxSnapshot(
                id=snapshot_id,
                tool_id=version.tool_id,
                draft_head_id=version.id,
                created_by_user_id=actor.id,
                entrypoint=entrypoint,
                source_code=source_code,
                settings_schema=settings_schema,
                input_schema=input_schema,
                usage_instructions=usage_instructions,
                payload_bytes=payload_bytes,
                created_at=now,
                expires_at=now + timedelta(seconds=self._settings.SANDBOX_SNAPSHOT_TTL_SECONDS),
            )
            await self._snapshots.create(snapshot=snapshot)

        input_files_by_field = {
            field: list(files) for field, files in command.input_files_by_field.items() if files
        }
        file_refs_by_field = {
            field: list(refs) for field, refs in command.file_refs_by_field.items() if refs
        }
        has_uploads = any(input_files_by_field.values())
        has_refs = any(file_refs_by_field.values())

        files_context = _sandbox_files_context(command.version_id)
        if (
            not has_uploads
            and not has_refs
            and command.session_files_mode is SessionFilesMode.REUSE
        ):
            session_files = await self._session_files.list_files(
                tool_id=command.tool_id,
                user_id=actor.id,
                context=files_context,
            )
            for item in session_files:
                if item.field is None:
                    continue
                file_refs_by_field.setdefault(item.field, []).append(
                    build_session_file_ref(name=item.name)
                )
        elif (
            not has_uploads
            and not has_refs
            and command.session_files_mode is SessionFilesMode.CLEAR
        ):
            await self._session_files.clear_session(
                tool_id=command.tool_id,
                user_id=actor.id,
                context=files_context,
            )

        result = await self._execute.handle(
            actor=actor,
            command=ExecuteToolVersionCommand(
                tool_id=command.tool_id,
                version_id=command.version_id,
                snapshot_id=snapshot_id,
                context=RunContext.SANDBOX,
                session_context=files_context,
                settings_context=settings_context,
                version_override=ToolVersionOverride(
                    entrypoint=entrypoint,
                    source_code=source_code,
                    settings_schema=settings_schema,
                    input_schema=input_schema,
                    usage_instructions=usage_instructions,
                ),
                input_files_by_field=input_files_by_field,
                input_values=command.input_values,
                file_refs_by_field=file_refs_by_field,
            ),
        )

        # Persist session-scoped files for subsequent sandbox action runs (ADR-0039).
        if input_files_by_field:
            files_to_store = [
                SessionFileContent(name=name, content=content, field=field)
                for field, files in input_files_by_field.items()
                for name, content in files
            ]
            await self._session_files.upsert_files(
                tool_id=command.tool_id,
                user_id=actor.id,
                context=files_context,
                files=files_to_store,
            )

        # Persist sandbox session state if run has next_actions (ADR-0038)
        state_rev: int | None = None
        run = result.run
        if run.ui_payload is not None and run.ui_payload.next_actions:
            context = _sandbox_context(snapshot_id)
            async with self._uow:
                session = await self._sessions.get_or_create(
                    session_id=self._id_generator.new_uuid(),
                    tool_id=command.tool_id,
                    user_id=actor.id,
                    context=context,
                )
                # Update state (always increment state_rev on new run)
                updated_session = await self._sessions.update_state(
                    tool_id=command.tool_id,
                    user_id=actor.id,
                    context=context,
                    expected_state_rev=session.state_rev,
                    state=resolve_state_update(
                        update=result.state_update,
                        current_state=session.state,
                    ),
                )
                state_rev = updated_session.state_rev

        return RunSandboxResult(run=result.run, state_rev=state_rev, snapshot_id=snapshot_id)
