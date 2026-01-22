"""Infrastructure provider: curated app registry and executor."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from skriptoteket.config import Settings
from skriptoteket.infrastructure.curated_apps.executor import InMemoryCuratedAppExecutor
from skriptoteket.infrastructure.curated_apps.registry import InMemoryCuratedAppRegistry
from skriptoteket.protocols.curated_apps import (
    CuratedAppExecutorProtocol,
    CuratedAppRegistryProtocol,
)


class InfrastructureCuratedAppsProvider(Provider):
    """Provides curated app registry and executor bindings."""

    @provide(scope=Scope.APP)
    def curated_app_registry(self, settings: Settings) -> CuratedAppRegistryProtocol:
        return InMemoryCuratedAppRegistry(settings=settings)

    @provide(scope=Scope.APP)
    def curated_app_executor(self, settings: Settings) -> CuratedAppExecutorProtocol:
        return InMemoryCuratedAppExecutor(artifacts_root=settings.ARTIFACTS_ROOT)
