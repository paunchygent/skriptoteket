from __future__ import annotations

import json

from pydantic import ValidationError

from skriptoteket.application.curated_apps.reagent_prep_chef import (
    ReagentPrepChefDefaultsResult,
    ReagentPrepChefLoadDefaultsRequest,
    ReagentPrepChefPrepRequest,
)
from skriptoteket.domain.curated_apps.models import curated_app_tool_id
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.reagent_prep_chef import ReagentPrepChefLoadDefaultsHandlerProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol, VaultStorageProtocol

APP_ID = "chemistry.reagent_prep_chef"
DEFAULTS_CONTEXT = "curated-app-defaults:v1"
DEFAULTS_KEY = "defaults"


class ReagentPrepChefLoadDefaultsHandler(ReagentPrepChefLoadDefaultsHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        id_generator: IdGeneratorProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
    ) -> None:
        self._uow = uow
        self._sessions = sessions
        self._id_generator = id_generator
        self._vault_files = vault_files
        self._vault_storage = vault_storage

    async def handle(
        self,
        *,
        actor: User,
        command: ReagentPrepChefLoadDefaultsRequest,
    ) -> ReagentPrepChefDefaultsResult:
        tool_id = curated_app_tool_id(app_id=APP_ID)

        async with self._uow:
            await self._sessions.get_or_create(
                session_id=self._id_generator.new_uuid(),
                tool_id=tool_id,
                user_id=actor.id,
                context=DEFAULTS_CONTEXT,
            )

            vault_file = await self._vault_files.get_by_id(file_id=command.file_id)
            if vault_file is None or vault_file.user_id != actor.id:
                raise not_found("VaultFile", str(command.file_id))

        try:
            raw = await self._vault_storage.read_file(user_id=actor.id, file_id=vault_file.id)
        except FileNotFoundError as exc:
            raise not_found("VaultFile", str(command.file_id)) from exc

        try:
            decoded = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise validation_error("Filen är inte giltig UTF-8 JSON.") from exc

        try:
            parsed = json.loads(decoded)
        except json.JSONDecodeError as exc:
            raise validation_error("Filen innehåller inte giltig JSON.") from exc

        if not isinstance(parsed, dict):
            raise validation_error("Filen innehåller inte ett giltigt inställningsobjekt.")

        try:
            defaults = ReagentPrepChefPrepRequest.model_validate(parsed)
        except ValidationError as exc:
            raise validation_error("Filen innehåller inte giltiga standardinställningar.") from exc

        async with self._uow:
            session = await self._sessions.update_state(
                tool_id=tool_id,
                user_id=actor.id,
                context=DEFAULTS_CONTEXT,
                expected_state_rev=command.expected_state_rev,
                state={DEFAULTS_KEY: defaults.model_dump(mode="json")},
            )

        return ReagentPrepChefDefaultsResult(defaults=defaults, state_rev=session.state_rev)
