"""Dependency injection container assembly.

Split into domain-specific providers for maintainability:
- infrastructure/: Database, repositories, core services
- identity.py: Authentication and user management
- catalog.py: Tool browsing and maintainer management
- scripting.py: Script execution and version management
- suggestions.py: Script suggestion workflow
- classroom_planner_*.py, conversion_hub*.py, document_converter.py, exam_*.py,
  flunk_out_frenzy.py, reagent_prep_chef.py: Curated app families
"""

from __future__ import annotations

from dishka import AsyncContainer, make_async_container
from starlette_dishka import StarletteProvider

from skriptoteket.config import Settings
from skriptoteket.di.catalog import CatalogProvider
from skriptoteket.di.classroom_planner_class_lists import ClassroomPlannerClassListProvider
from skriptoteket.di.classroom_planner_drafts import ClassroomPlannerDraftProvider
from skriptoteket.di.classroom_planner_exports import ClassroomPlannerExportProvider
from skriptoteket.di.classroom_planner_rosters import ClassroomPlannerRosterProvider
from skriptoteket.di.classroom_planner_shares import ClassroomPlannerShareProvider
from skriptoteket.di.classroom_planner_smart_rules import ClassroomPlannerSmartRuleProvider
from skriptoteket.di.conversion_hub import ConversionHubProvider
from skriptoteket.di.conversion_hub_transcripts import ConversionHubTranscriptProvider
from skriptoteket.di.document_converter import DocumentConverterProvider
from skriptoteket.di.editor import EditorProvider
from skriptoteket.di.exam_answer_key import ExamAnswerKeyProvider
from skriptoteket.di.exam_converter import ExamConverterProvider
from skriptoteket.di.exam_workspace import ExamWorkspaceProvider
from skriptoteket.di.favorites import FavoritesProvider
from skriptoteket.di.flunk_out_frenzy import FlunkOutFrenzyProvider
from skriptoteket.di.identity import IdentityProvider
from skriptoteket.di.infrastructure import (
    InfrastructureCuratedAppsProvider,
    InfrastructureDatabaseProvider,
    InfrastructureRepositoryProvider,
    InfrastructureRunnerProvider,
    InfrastructureScriptingUiProvider,
    InfrastructureServicesProvider,
    InfrastructureSessionFilesProvider,
)
from skriptoteket.di.llm import LlmProvider
from skriptoteket.di.reagent_prep_chef import ReagentPrepChefProvider
from skriptoteket.di.scripting import ScriptingProvider
from skriptoteket.di.suggestions import SuggestionsProvider

__all__ = [
    "CatalogProvider",
    "ClassroomPlannerRosterProvider",
    "ClassroomPlannerSmartRuleProvider",
    "ClassroomPlannerClassListProvider",
    "ClassroomPlannerDraftProvider",
    "ClassroomPlannerExportProvider",
    "ClassroomPlannerShareProvider",
    "ConversionHubProvider",
    "ConversionHubTranscriptProvider",
    "DocumentConverterProvider",
    "ExamAnswerKeyProvider",
    "ExamConverterProvider",
    "FlunkOutFrenzyProvider",
    "ReagentPrepChefProvider",
    "EditorProvider",
    "ExamWorkspaceProvider",
    "FavoritesProvider",
    "IdentityProvider",
    "InfrastructureCuratedAppsProvider",
    "InfrastructureDatabaseProvider",
    "InfrastructureRepositoryProvider",
    "InfrastructureRunnerProvider",
    "InfrastructureScriptingUiProvider",
    "InfrastructureServicesProvider",
    "InfrastructureSessionFilesProvider",
    "LlmProvider",
    "ScriptingProvider",
    "SuggestionsProvider",
    "create_container",
]


def create_container(settings: Settings) -> AsyncContainer:
    """Create the DI container with all domain providers."""
    return make_async_container(
        StarletteProvider(),
        InfrastructureDatabaseProvider(settings),
        InfrastructureRepositoryProvider(),
        InfrastructureRunnerProvider(),
        InfrastructureScriptingUiProvider(),
        InfrastructureServicesProvider(),
        InfrastructureSessionFilesProvider(),
        InfrastructureCuratedAppsProvider(),
        ClassroomPlannerClassListProvider(),
        ClassroomPlannerDraftProvider(),
        ClassroomPlannerExportProvider(),
        ClassroomPlannerShareProvider(),
        ConversionHubProvider(),
        ConversionHubTranscriptProvider(),
        DocumentConverterProvider(),
        ExamAnswerKeyProvider(),
        ExamConverterProvider(),
        FlunkOutFrenzyProvider(),
        ReagentPrepChefProvider(),
        ClassroomPlannerRosterProvider(),
        ClassroomPlannerSmartRuleProvider(),
        IdentityProvider(),
        CatalogProvider(),
        FavoritesProvider(),
        EditorProvider(),
        ExamWorkspaceProvider(),
        LlmProvider(),
        ScriptingProvider(),
        SuggestionsProvider(),
    )
