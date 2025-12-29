from __future__ import annotations

from uuid import UUID

import structlog

from skriptoteket.application.scripting.tool_settings import ToolSettingsState
from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.scripting.tool_settings import (
    ToolSettingsSchema,
    ToolSettingsValues,
    compute_sandbox_settings_context,
    compute_settings_schema_hash,
    normalize_tool_settings_values,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.tool_settings import ToolSettingsServiceProtocol

logger = structlog.get_logger(__name__)


class ToolSettingsService(ToolSettingsServiceProtocol):
    """Resolve and persist tool settings via tool_sessions."""

    def __init__(
        self,
        *,
        sessions: ToolSessionRepositoryProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._sessions = sessions
        self._id_generator = id_generator

    async def resolve_sandbox_settings(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        draft_head_id: UUID,
        settings_schema: ToolSettingsSchema,
    ) -> ToolSettingsState:
        schema_version = compute_settings_schema_hash(settings_schema=settings_schema)
        context = compute_sandbox_settings_context(
            draft_head_id=draft_head_id,
            settings_schema=settings_schema,
        )
        session = await self._sessions.get_or_create(
            session_id=self._id_generator.new_uuid(),
            tool_id=tool_id,
            user_id=user_id,
            context=context,
        )

        try:
            values = normalize_tool_settings_values(
                settings_schema=settings_schema,
                values=session.state,
            )
        except DomainError:
            logger.warning(
                "Invalid persisted sandbox settings; ignoring",
                tool_id=str(tool_id),
                user_id=str(user_id),
                context=context,
            )
            values = {}

        return ToolSettingsState(
            tool_id=tool_id,
            schema_version=schema_version,
            settings_schema=settings_schema,
            values=values,
            state_rev=session.state_rev,
        )

    async def save_sandbox_settings(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        draft_head_id: UUID,
        settings_schema: ToolSettingsSchema,
        expected_state_rev: int,
        values: ToolSettingsValues,
    ) -> ToolSettingsState:
        schema_version = compute_settings_schema_hash(settings_schema=settings_schema)
        context = compute_sandbox_settings_context(
            draft_head_id=draft_head_id,
            settings_schema=settings_schema,
        )

        normalized = normalize_tool_settings_values(
            settings_schema=settings_schema,
            values=values,
        )

        await self._sessions.get_or_create(
            session_id=self._id_generator.new_uuid(),
            tool_id=tool_id,
            user_id=user_id,
            context=context,
        )
        session = await self._sessions.update_state(
            tool_id=tool_id,
            user_id=user_id,
            context=context,
            expected_state_rev=expected_state_rev,
            state=normalized,
        )

        try:
            persisted = normalize_tool_settings_values(
                settings_schema=settings_schema,
                values=session.state,
            )
        except DomainError:
            logger.warning(
                "Unexpected invalid sandbox settings after update; clearing",
                tool_id=str(tool_id),
                user_id=str(user_id),
                context=context,
            )
            persisted = {}

        return ToolSettingsState(
            tool_id=tool_id,
            schema_version=schema_version,
            settings_schema=settings_schema,
            values=persisted,
            state_rev=session.state_rev,
        )
