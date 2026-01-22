"""Infrastructure DI providers grouped by responsibility."""

from __future__ import annotations

from skriptoteket.di.infrastructure.curated_apps import InfrastructureCuratedAppsProvider
from skriptoteket.di.infrastructure.db import InfrastructureDatabaseProvider
from skriptoteket.di.infrastructure.repositories import InfrastructureRepositoryProvider
from skriptoteket.di.infrastructure.runner import InfrastructureRunnerProvider
from skriptoteket.di.infrastructure.scripting_ui import InfrastructureScriptingUiProvider
from skriptoteket.di.infrastructure.services import InfrastructureServicesProvider
from skriptoteket.di.infrastructure.session_files import InfrastructureSessionFilesProvider

__all__ = [
    "InfrastructureCuratedAppsProvider",
    "InfrastructureDatabaseProvider",
    "InfrastructureRepositoryProvider",
    "InfrastructureRunnerProvider",
    "InfrastructureScriptingUiProvider",
    "InfrastructureServicesProvider",
    "InfrastructureSessionFilesProvider",
]
