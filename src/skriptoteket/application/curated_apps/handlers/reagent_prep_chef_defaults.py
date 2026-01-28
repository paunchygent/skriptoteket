from __future__ import annotations

import structlog
from pydantic import JsonValue, ValidationError

from skriptoteket.application.curated_apps.reagent_prep_chef import (
    ReagentPrepChefDefaultsResult,
    ReagentPrepChefPrepRequest,
    ReagentPrepChefUpdateDefaultsRequest,
)
from skriptoteket.domain.curated_apps.models import curated_app_tool_id
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.reagent_prep_chef import (
    ReagentPrepChefGetDefaultsHandlerProtocol,
    ReagentPrepChefUpdateDefaultsHandlerProtocol,
)
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = structlog.get_logger(__name__)

APP_ID = "chemistry.reagent_prep_chef"
DEFAULTS_CONTEXT = "curated-app-defaults:v1"
DEFAULTS_KEY = "defaults"


def _parse_defaults(value: object) -> ReagentPrepChefPrepRequest | None:
    if not isinstance(value, dict):
        return None
    try:
        return ReagentPrepChefPrepRequest.model_validate(value)
    except ValidationError:
        return None


class ReagentPrepChefGetDefaultsHandler(ReagentPrepChefGetDefaultsHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._sessions = sessions
        self._id_generator = id_generator

    async def handle(self, *, actor: User) -> ReagentPrepChefDefaultsResult:
        tool_id = curated_app_tool_id(app_id=APP_ID)

        async with self._uow:
            session = await self._sessions.get_or_create(
                session_id=self._id_generator.new_uuid(),
                tool_id=tool_id,
                user_id=actor.id,
                context=DEFAULTS_CONTEXT,
            )

        defaults = _parse_defaults(session.state.get(DEFAULTS_KEY))
        if defaults is None and session.state:
            logger.warning(
                "Invalid reagent prep chef defaults; ignoring",
                actor_id=str(actor.id),
                context=DEFAULTS_CONTEXT,
            )

        return ReagentPrepChefDefaultsResult(
            defaults=defaults,
            state_rev=session.state_rev,
        )


class ReagentPrepChefUpdateDefaultsHandler(ReagentPrepChefUpdateDefaultsHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._sessions = sessions
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        command: ReagentPrepChefUpdateDefaultsRequest,
    ) -> ReagentPrepChefDefaultsResult:
        tool_id = curated_app_tool_id(app_id=APP_ID)

        async with self._uow:
            session = await self._sessions.get_or_create(
                session_id=self._id_generator.new_uuid(),
                tool_id=tool_id,
                user_id=actor.id,
                context=DEFAULTS_CONTEXT,
            )

            next_state: dict[str, JsonValue] = {}
            if command.defaults is not None:
                next_state[DEFAULTS_KEY] = command.defaults.model_dump(mode="json")

            session = await self._sessions.update_state(
                tool_id=tool_id,
                user_id=actor.id,
                context=DEFAULTS_CONTEXT,
                expected_state_rev=command.expected_state_rev,
                state=next_state,
            )

        defaults = _parse_defaults(session.state.get(DEFAULTS_KEY))
        return ReagentPrepChefDefaultsResult(defaults=defaults, state_rev=session.state_rev)
