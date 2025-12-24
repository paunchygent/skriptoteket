from __future__ import annotations

import structlog

from skriptoteket.application.scripting.tool_settings import (
    GetToolSettingsQuery,
    GetToolSettingsResult,
    ToolSettingsState,
)
from skriptoteket.domain.errors import DomainError, not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.models import VersionState
from skriptoteket.domain.scripting.tool_settings import (
    compute_settings_schema_hash,
    compute_settings_session_context,
    normalize_tool_settings_values,
)
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.scripting import ToolVersionRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.tool_settings import GetToolSettingsHandlerProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = structlog.get_logger(__name__)


class GetToolSettingsHandler(GetToolSettingsHandlerProtocol):
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
        query: GetToolSettingsQuery,
    ) -> GetToolSettingsResult:
        async with self._uow:
            tool = await self._tools.get_by_id(tool_id=query.tool_id)
            if tool is None or not tool.is_published or tool.active_version_id is None:
                raise not_found("Tool", str(query.tool_id))

            version = await self._versions.get_by_id(version_id=tool.active_version_id)
            if version is None or version.state is not VersionState.ACTIVE:
                raise not_found("ToolVersion", str(tool.active_version_id))

            schema = version.settings_schema
            if schema is None:
                return GetToolSettingsResult(
                    settings=ToolSettingsState(
                        tool_id=tool.id,
                        schema_version=None,
                        settings_schema=None,
                        values={},
                        state_rev=0,
                    )
                )

            schema_version = compute_settings_schema_hash(settings_schema=schema)
            context = compute_settings_session_context(settings_schema=schema)
            session = await self._sessions.get_or_create(
                session_id=self._id_generator.new_uuid(),
                tool_id=tool.id,
                user_id=actor.id,
                context=context,
            )

        try:
            values = normalize_tool_settings_values(settings_schema=schema, values=session.state)
        except DomainError:
            logger.warning(
                "Invalid persisted tool settings; ignoring",
                tool_id=str(query.tool_id),
                actor_id=str(actor.id),
                context=context,
            )
            values = {}

        return GetToolSettingsResult(
            settings=ToolSettingsState(
                tool_id=query.tool_id,
                schema_version=schema_version,
                settings_schema=schema,
                values=values,
                state_rev=session.state_rev,
            )
        )
