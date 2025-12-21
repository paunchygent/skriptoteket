from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.ui.contract_v2 import UiFormAction
from skriptoteket.domain.scripting.ui.policy import UiPolicy
from skriptoteket.protocols.scripting_ui import BackendActionProviderProtocol


class NoopBackendActionProvider(BackendActionProviderProtocol):
    async def list_backend_actions(
        self,
        *,
        tool_id: UUID,
        actor: User,
        policy: UiPolicy,
    ) -> list[UiFormAction]:
        del tool_id, actor, policy
        return []
