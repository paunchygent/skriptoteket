from __future__ import annotations

import structlog

from skriptoteket.application.scripting.tool_settings import (
    ToolSettingsState,
    UpdateToolSettingsCommand,
    UpdateToolSettingsResult,
)
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.models import VersionState
from skriptoteket.domain.scripting.tool_sessions import validate_expected_state_rev
from skriptoteket.domain.scripting.tool_settings import (
    compute_settings_schema_hash,
    compute_settings_session_context,
    normalize_tool_settings_values,
)
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.scripting import ToolVersionRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.tool_settings import UpdateToolSettingsHandlerProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = structlog.get_logger(__name__)


class UpdateToolSettingsHandler(UpdateToolSettingsHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        versions: ToolVersionRepositoryProtocol,
        sessions: ToolSessionRepositoryProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._tools = tools
        self._versions = versions
        self._sessions = sessions
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        command: UpdateToolSettingsCommand,
    ) -> UpdateToolSettingsResult:
        validate_expected_state_rev(expected_state_rev=command.expected_state_rev)

        async with self._uow:
            tool = await self._tools.get_by_id(tool_id=command.tool_id)
            if tool is None or not tool.is_published or tool.active_version_id is None:
                raise not_found("Tool", str(command.tool_id))

            version = await self._versions.get_by_id(version_id=tool.active_version_id)
            if version is None or version.state is not VersionState.ACTIVE:
                raise not_found("ToolVersion", str(tool.active_version_id))

            schema = version.settings_schema
            if schema is None:
                raise validation_error(
                    "Tool has no settings schema",
                    details={"tool_id": str(command.tool_id)},
                )

            schema_version = compute_settings_schema_hash(settings_schema=schema)
            context = compute_settings_session_context(settings_schema=schema)

            values = normalize_tool_settings_values(
                settings_schema=schema,
                values=command.values,
            )

            await self._sessions.get_or_create(
                session_id=self._id_generator.new_uuid(),
                tool_id=tool.id,
                user_id=actor.id,
                context=context,
            )
            session = await self._sessions.update_state(
                tool_id=tool.id,
                user_id=actor.id,
                context=context,
                expected_state_rev=command.expected_state_rev,
                state=values,
            )

        logger.info(
            "Tool settings updated",
            tool_id=str(command.tool_id),
            actor_id=str(actor.id),
            context=context,
            state_rev=session.state_rev,
        )

        return UpdateToolSettingsResult(
            settings=ToolSettingsState(
                tool_id=tool.id,
                schema_version=schema_version,
                settings_schema=schema,
                values=session.state,
                state_rev=session.state_rev,
            )
        )
