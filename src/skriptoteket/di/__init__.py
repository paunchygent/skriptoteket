"""Dependency injection container assembly.

Split into domain-specific providers for maintainability:
- infrastructure.py: Database, repositories, core services
- identity.py: Authentication and user management
- catalog.py: Tool browsing and maintainer management
- scripting.py: Script execution and version management
- suggestions.py: Script suggestion workflow
"""

from __future__ import annotations

from dishka import make_async_container

from skriptoteket.config import Settings
from skriptoteket.di.catalog import CatalogProvider
from skriptoteket.di.identity import IdentityProvider
from skriptoteket.di.infrastructure import InfrastructureProvider
from skriptoteket.di.scripting import ScriptingProvider
from skriptoteket.di.suggestions import SuggestionsProvider

__all__ = [
    "CatalogProvider",
    "IdentityProvider",
    "InfrastructureProvider",
    "ScriptingProvider",
    "SuggestionsProvider",
    "create_container",
]


def create_container(settings: Settings):
    """Create the DI container with all domain providers."""
    return make_async_container(
        InfrastructureProvider(settings),
        IdentityProvider(),
        CatalogProvider(),
        ScriptingProvider(),
        SuggestionsProvider(),
    )
