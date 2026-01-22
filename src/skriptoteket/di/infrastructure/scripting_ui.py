"""Infrastructure provider: scripting UI policy and payload normalization."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from skriptoteket.domain.scripting.ui.normalizer import DeterministicUiPayloadNormalizer
from skriptoteket.infrastructure.scripting_ui.backend_actions import NoopBackendActionProvider
from skriptoteket.infrastructure.scripting_ui.policy_provider import DefaultUiPolicyProvider
from skriptoteket.protocols.scripting_ui import (
    BackendActionProviderProtocol,
    UiPayloadNormalizerProtocol,
    UiPolicyProviderProtocol,
)


class InfrastructureScriptingUiProvider(Provider):
    """Provides scripting UI policy, backend actions, and payload normalizer."""

    @provide(scope=Scope.APP)
    def ui_policy_provider(self) -> UiPolicyProviderProtocol:
        return DefaultUiPolicyProvider()

    @provide(scope=Scope.APP)
    def backend_actions(self) -> BackendActionProviderProtocol:
        return NoopBackendActionProvider()

    @provide(scope=Scope.APP)
    def ui_normalizer(self) -> UiPayloadNormalizerProtocol:
        return DeterministicUiPayloadNormalizer()
