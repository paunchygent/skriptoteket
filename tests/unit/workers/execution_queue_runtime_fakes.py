from __future__ import annotations

import asyncio
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import JsonValue

from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.execution import ToolExecutionResult
from skriptoteket.domain.scripting.models import RunContext, ToolVersion
from skriptoteket.domain.scripting.run_inputs import ResolvedInputFile
from skriptoteket.domain.scripting.ui.contract_v2 import UiFormAction
from skriptoteket.domain.scripting.ui.policy import DEFAULT_UI_POLICY, UiPolicy, UiPolicyProfileId
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.promotions import PromotionApplierProtocol
from skriptoteket.protocols.runner import ToolRunnerAdoptionProtocol, ToolRunnerProtocol
from skriptoteket.protocols.scripting_ui import (
    BackendActionProviderProtocol,
    UiPolicyProviderProtocol,
)


class FakeClock(ClockProtocol):
    def __init__(self, *, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class FakeSleeper:
    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)


class FakeIdGenerator(IdGeneratorProtocol):
    def new_uuid(self) -> UUID:
        return uuid4()


class FakeUiPolicyProvider(UiPolicyProviderProtocol):
    async def get_profile_id_for_tool(self, *, tool_id: UUID, actor: User) -> UiPolicyProfileId:
        del tool_id, actor
        return UiPolicyProfileId.DEFAULT

    async def get_profile_id_for_curated_app(
        self, *, curated_app_id: str, actor: User
    ) -> UiPolicyProfileId:
        del curated_app_id, actor
        return UiPolicyProfileId.DEFAULT

    def get_policy(self, *, profile_id: UiPolicyProfileId) -> UiPolicy:
        del profile_id
        return DEFAULT_UI_POLICY


class FakeBackendActionProvider(BackendActionProviderProtocol):
    async def list_backend_actions(
        self,
        *,
        tool_id: UUID,
        actor: User,
        policy: UiPolicy,
    ) -> list[UiFormAction]:
        del tool_id, actor, policy
        return []


class FakePromotionApplier(PromotionApplierProtocol):
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def apply_session_promotions(
        self,
        *,
        run_id: UUID,
        tool_id: UUID,
        user_id: UUID,
        context: str,
        artifacts_manifest,
        promotions,
    ) -> None:
        self.calls.append(
            {
                "run_id": run_id,
                "tool_id": tool_id,
                "user_id": user_id,
                "context": context,
                "artifacts_manifest": artifacts_manifest,
                "promotions": promotions,
            }
        )


class FakeRunner(ToolRunnerProtocol):
    def __init__(self, *, result: ToolExecutionResult) -> None:
        self._result = result
        self.called = False

    async def execute(
        self,
        *,
        run_id: UUID,
        version: ToolVersion,
        context: RunContext,
        input_files: list[ResolvedInputFile],
        input_values: dict[str, JsonValue],
        memory_json: bytes,
        action_payload: dict[str, JsonValue] | None,
    ) -> ToolExecutionResult:
        del run_id, version, context, input_files, input_values, memory_json, action_payload
        self.called = True
        return self._result


class FakeRunnerAdoption(ToolRunnerAdoptionProtocol):
    def __init__(self, *, result: ToolExecutionResult | None) -> None:
        self._result = result
        self.called = False

    async def try_adopt(
        self,
        *,
        run_id: UUID,
        version: ToolVersion,
        context: RunContext,
    ) -> ToolExecutionResult | None:
        del run_id, version, context
        self.called = True
        return self._result
