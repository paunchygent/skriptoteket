from __future__ import annotations

import structlog

from skriptoteket.application.scripting.tool_settings import (
    GetToolVersionSettingsQuery,
    GetToolVersionSettingsResult,
    ToolSettingsState,
)
from skriptoteket.domain.errors import DomainError, not_found
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.domain.scripting.policies import require_can_view_version
from skriptoteket.domain.scripting.tool_settings import (
    compute_settings_schema_hash,
    compute_settings_session_context,
    normalize_tool_settings_values,
)
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.scripting import ToolVersionRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.tool_settings import GetToolVersionSettingsHandlerProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = structlog.get_logger(__name__)


class GetToolVersionSettingsHandler(GetToolVersionSettingsHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        versions: ToolVersionRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        sessions: ToolSessionRepositoryProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._versions = versions
        self._maintainers = maintainers
        self._sessions = sessions
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        query: GetToolVersionSettingsQuery,
    ) -> GetToolVersionSettingsResult:
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)

        schema = None
        schema_version: str | None = None
        context: str | None = None
        session = None

        async with self._uow:
            version = await self._versions.get_by_id(version_id=query.version_id)
            if version is None:
                raise not_found("ToolVersion", str(query.version_id))

            is_tool_maintainer = actor.role in {Role.ADMIN, Role.SUPERUSER}
            if actor.role is Role.CONTRIBUTOR:
                is_tool_maintainer = await self._maintainers.is_maintainer(
                    tool_id=version.tool_id,
                    user_id=actor.id,
                )

            require_can_view_version(
                actor=actor,
                version=version,
                is_tool_maintainer=is_tool_maintainer,
            )

            schema = version.settings_schema
            if schema is None:
                return GetToolVersionSettingsResult(
                    settings=ToolSettingsState(
                        tool_id=version.tool_id,
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
                tool_id=version.tool_id,
                user_id=actor.id,
                context=context,
            )

        assert schema is not None
        assert schema_version is not None
        assert context is not None
        assert session is not None

        try:
            values = normalize_tool_settings_values(settings_schema=schema, values=session.state)
        except DomainError:
            logger.warning(
                "Invalid persisted tool settings; ignoring",
                tool_version_id=str(query.version_id),
                actor_id=str(actor.id),
                context=context,
            )
            values = {}

        return GetToolVersionSettingsResult(
            settings=ToolSettingsState(
                tool_id=session.tool_id,
                schema_version=schema_version,
                settings_schema=schema,
                values=values,
                state_rev=session.state_rev,
            )
        )
