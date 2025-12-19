from __future__ import annotations

from typing import Protocol
from uuid import UUID

from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.ui.contract_v2 import ToolUiContractV2Result, UiFormAction
from skriptoteket.domain.scripting.ui.normalization import UiNormalizationResult
from skriptoteket.domain.scripting.ui.policy import UiPolicy, UiPolicyProfileId


class UiPolicyProviderProtocol(Protocol):
    """Returns a UI policy profile used for allowlists and budgets (ADR-0024)."""

    async def get_profile_id_for_tool(
        self,
        *,
        tool_id: UUID,
        actor: User,
    ) -> UiPolicyProfileId: ...

    async def get_profile_id_for_curated_app(
        self,
        *,
        curated_app_id: str,
        actor: User,
    ) -> UiPolicyProfileId: ...

    def get_policy(
        self,
        *,
        profile_id: UiPolicyProfileId,
    ) -> UiPolicy: ...


class BackendActionProviderProtocol(Protocol):
    """Provides backend-injected UI actions/capabilities (policy-gated)."""

    async def list_backend_actions(
        self,
        *,
        tool_id: UUID,
        actor: User,
        policy: UiPolicy,
    ) -> list[UiFormAction]: ...


class UiPayloadNormalizerProtocol(Protocol):
    """Deterministically normalizes a raw contract v2 payload into a stored ui_payload."""

    def normalize(
        self,
        *,
        raw_result: ToolUiContractV2Result,
        backend_actions: list[UiFormAction],
        policy: UiPolicy,
    ) -> UiNormalizationResult: ...
