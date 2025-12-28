from __future__ import annotations

import structlog

from skriptoteket.application.scripting.tool_settings import (
    ToolSettingsState,
    UpdateToolVersionSettingsCommand,
    UpdateToolVersionSettingsResult,
)
from skriptoteket.domain.errors import DomainError, not_found, validation_error
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.domain.scripting.policies import require_can_view_version
from skriptoteket.domain.scripting.tool_sessions import validate_expected_state_rev
from skriptoteket.domain.scripting.tool_settings import (
    compute_settings_schema_hash,
    compute_settings_session_context,
    normalize_tool_settings_values,
)
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.scripting import ToolVersionRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.tool_settings import UpdateToolVersionSettingsHandlerProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = structlog.get_logger(__name__)


class UpdateToolVersionSettingsHandler(UpdateToolVersionSettingsHandlerProtocol):
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
        command: UpdateToolVersionSettingsCommand,
    ) -> UpdateToolVersionSettingsResult:
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)
        validate_expected_state_rev(expected_state_rev=command.expected_state_rev)

        schema = None
        schema_version: str | None = None
        context: str | None = None
        session = None

        async with self._uow:
            version = await self._versions.get_by_id(version_id=command.version_id)
            if version is None:
                raise not_found("ToolVersion", str(command.version_id))

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
                raise validation_error(
                    "ToolVersion has no settings schema",
                    details={"tool_version_id": str(command.version_id)},
                )

            schema_version = compute_settings_schema_hash(settings_schema=schema)
            context = compute_settings_session_context(settings_schema=schema)

            values = normalize_tool_settings_values(
                settings_schema=schema,
                values=command.values,
            )

            await self._sessions.get_or_create(
                session_id=self._id_generator.new_uuid(),
                tool_id=version.tool_id,
                user_id=actor.id,
                context=context,
            )
            session = await self._sessions.update_state(
                tool_id=version.tool_id,
                user_id=actor.id,
                context=context,
                expected_state_rev=command.expected_state_rev,
                state=values,
            )

        assert schema is not None
        assert schema_version is not None
        assert context is not None
        assert session is not None

        try:
            normalized = normalize_tool_settings_values(
                settings_schema=schema,
                values=session.state,
            )
        except DomainError:
            logger.warning(
                "Unexpected invalid tool settings after update; clearing",
                tool_version_id=str(command.version_id),
                actor_id=str(actor.id),
                context=context,
            )
            normalized = {}

        logger.info(
            "Tool version settings updated",
            tool_version_id=str(command.version_id),
            actor_id=str(actor.id),
            context=context,
            state_rev=session.state_rev,
        )

        return UpdateToolVersionSettingsResult(
            settings=ToolSettingsState(
                tool_id=session.tool_id,
                schema_version=schema_version,
                settings_schema=schema,
                values=normalized,
                state_rev=session.state_rev,
            )
        )
