from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.ui.policy import UiPolicy, UiPolicyProfileId, get_ui_policy
from skriptoteket.protocols.scripting_ui import UiPolicyProviderProtocol


class DefaultUiPolicyProvider(UiPolicyProviderProtocol):
    async def get_profile_id_for_tool(
        self,
        *,
        tool_id: UUID,
        actor: User,
    ) -> UiPolicyProfileId:
        del tool_id, actor
        return UiPolicyProfileId.DEFAULT

    async def get_profile_id_for_curated_app(
        self,
        *,
        curated_app_id: str,
        actor: User,
    ) -> UiPolicyProfileId:
        del curated_app_id, actor
        return UiPolicyProfileId.CURATED

    def get_policy(self, *, profile_id: UiPolicyProfileId) -> UiPolicy:
        return get_ui_policy(profile_id=profile_id)
