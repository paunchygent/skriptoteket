"""DI bindings for exam answer-key enrichment.

Enrichment job, token lease, and proposed overlay repositories, provider
selection, the structured provider, and the enrichment job and workspace
handlers.
"""

from __future__ import annotations

import httpx
from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_jobs import (
    ProcessExamAnswerKeyEnrichmentJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_answer_key_lease_status import (
    GetAnswerKeyLeaseStatusHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_jobs import (
    ProcessExamWorkspaceDocxJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_enrichment import (
    FindExamWorkspaceAnswerKeySuggestionsHandler,
    GetExamWorkspaceAnswerKeySuggestionsStatusHandler,
    RequestExamWorkspaceAnswerKeySuggestionsHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    AnswerKeyProviderRoute,
)
from skriptoteket.infrastructure.llm.answer_key_provider_dispatch import (
    EndpointRoutedAnswerKeyProvider,
)
from skriptoteket.infrastructure.llm.answer_key_provider_selection import (
    FixedRouteAnswerKeyProviderSelector,
)
from skriptoteket.infrastructure.llm.openai.answer_key_profiles import build_luna_answer_key_profile
from skriptoteket.infrastructure.llm.openai.answer_key_structured_provider import (
    OpenAIAnswerKeyStructuredProvider,
)
from skriptoteket.infrastructure.llm.openrouter.answer_key_chat_provider import (
    OpenRouterAnswerKeyChatProvider,
)
from skriptoteket.infrastructure.llm.openrouter.answer_key_profiles import (
    build_glm_failover_answer_key_profile,
)
from skriptoteket.infrastructure.repositories.exam_answer_key_enrichment_jobs import (
    PostgreSQLExamAnswerKeyEnrichmentJobRepository,
)
from skriptoteket.infrastructure.repositories.exam_answer_key_proposed_overlays import (
    PostgreSQLExamAnswerKeyProposedOverlayRepository,
)
from skriptoteket.infrastructure.repositories.exam_answer_key_token_leases import (
    PostgreSQLAnswerKeyTokenLeaseRepository,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.conversion_hub import ConversionHubJobRepositoryProtocol
from skriptoteket.protocols.exam_answer_key import (
    AnswerKeyLeaseStatusHandlerProtocol,
    AnswerKeyProviderSelectorProtocol,
    AnswerKeyStructuredProviderProtocol,
    AnswerKeyTokenLeaseRepositoryProtocol,
    ExamAnswerKeyEnrichmentJobRepositoryProtocol,
    ExamAnswerKeyProposedOverlayRepositoryProtocol,
    ExamWorkspaceSuggestionJobQueryProtocol,
)
from skriptoteket.protocols.exam_conversion import (
    ExamConversionArtifactStoreProtocol,
    InProcessExamConverterProtocol,
)
from skriptoteket.protocols.exam_workspace import (
    FindExamWorkspaceAnswerKeySuggestionsHandlerProtocol,
    GetExamWorkspaceAnswerKeySuggestionsStatusHandlerProtocol,
    RequestExamWorkspaceAnswerKeySuggestionsHandlerProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol


class ExamAnswerKeyProvider(Provider):
    """Provide answer-key enrichment repositories, providers, and handlers."""

    @provide(scope=Scope.REQUEST)
    def exam_answer_key_enrichment_job_repository(
        self, session: AsyncSession
    ) -> ExamAnswerKeyEnrichmentJobRepositoryProtocol:
        return PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)

    @provide(scope=Scope.REQUEST)
    def exam_workspace_suggestion_job_query(
        self, session: AsyncSession
    ) -> ExamWorkspaceSuggestionJobQueryProtocol:
        return PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)

    @provide(scope=Scope.REQUEST)
    def exam_answer_key_token_lease_repository(
        self,
        session: AsyncSession,
        settings: Settings,
    ) -> AnswerKeyTokenLeaseRepositoryProtocol:
        return PostgreSQLAnswerKeyTokenLeaseRepository(
            session,
            daily_token_limit=settings.LLM_ANSWER_KEY_DAILY_TOKEN_LIMIT,
        )

    @provide(scope=Scope.REQUEST)
    def exam_answer_key_proposed_overlay_repository(
        self, session: AsyncSession
    ) -> ExamAnswerKeyProposedOverlayRepositoryProtocol:
        return PostgreSQLExamAnswerKeyProposedOverlayRepository(session)

    @provide(scope=Scope.REQUEST)
    def answer_key_lease_status_handler(
        self,
        leases: AnswerKeyTokenLeaseRepositoryProtocol,
        clock: ClockProtocol,
    ) -> AnswerKeyLeaseStatusHandlerProtocol:
        return GetAnswerKeyLeaseStatusHandler(leases=leases, clock=clock)

    @provide(scope=Scope.APP)
    def answer_key_provider_selector(self, settings: Settings) -> AnswerKeyProviderSelectorProtocol:
        return FixedRouteAnswerKeyProviderSelector(
            route=AnswerKeyProviderRoute(
                primary=build_luna_answer_key_profile(settings),
                failover=build_glm_failover_answer_key_profile(settings),
            )
        )

    @provide(scope=Scope.APP)
    def answer_key_structured_provider(
        self,
        settings: Settings,
        client: httpx.AsyncClient,
    ) -> AnswerKeyStructuredProviderProtocol:
        return EndpointRoutedAnswerKeyProvider(
            responses_provider=OpenAIAnswerKeyStructuredProvider(
                client=client,
                base_url=settings.LLM_ANSWER_KEY_BASE_URL,
                api_key=settings.OPENAI_LLM_ANSWER_KEY_API_KEY,
                timeout_seconds=float(settings.LLM_ANSWER_KEY_TIMEOUT_SECONDS),
            ),
            chat_completions_provider=OpenRouterAnswerKeyChatProvider(
                client=client,
                base_url=settings.LLM_ANSWER_KEY_FAILOVER_BASE_URL,
                api_key=settings.OPENROUTER_LLM_ANSWER_KEY_API_KEY,
                timeout_seconds=float(settings.LLM_ANSWER_KEY_TIMEOUT_SECONDS),
            ),
        )

    @provide(scope=Scope.REQUEST)
    def process_exam_answer_key_enrichment_job_handler(
        self,
        enrichment_jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        conversion_jobs: ConversionHubJobRepositoryProtocol,
        leases: AnswerKeyTokenLeaseRepositoryProtocol,
        proposed_overlays: ExamAnswerKeyProposedOverlayRepositoryProtocol,
        provider: AnswerKeyStructuredProviderProtocol,
        provider_selector: AnswerKeyProviderSelectorProtocol,
        producer: InProcessExamConverterProtocol,
        artifacts: ExamConversionArtifactStoreProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        docx_handler: ProcessExamWorkspaceDocxJobHandler,
    ) -> ProcessExamAnswerKeyEnrichmentJobHandler:
        return ProcessExamAnswerKeyEnrichmentJobHandler(
            enrichment_jobs=enrichment_jobs,
            conversion_jobs=conversion_jobs,
            leases=leases,
            proposed_overlays=proposed_overlays,
            provider=provider,
            provider_selector=provider_selector,
            producer=producer,
            artifacts=artifacts,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
            docx_handler=docx_handler,
        )

    @provide(scope=Scope.REQUEST)
    def request_exam_workspace_answer_key_suggestions_handler(
        self,
        enrichment_jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        suggestion_jobs: ExamWorkspaceSuggestionJobQueryProtocol,
        settings: Settings,
        vault_files: VaultFileRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> RequestExamWorkspaceAnswerKeySuggestionsHandlerProtocol:
        return RequestExamWorkspaceAnswerKeySuggestionsHandler(
            enrichment_jobs=enrichment_jobs,
            suggestion_jobs=suggestion_jobs,
            enrichment_enabled=settings.LLM_ANSWER_KEY_ENABLED,
            vault_files=vault_files,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def exam_workspace_answer_key_suggestions_status_handler(
        self,
        enrichment_jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
    ) -> GetExamWorkspaceAnswerKeySuggestionsStatusHandlerProtocol:
        return GetExamWorkspaceAnswerKeySuggestionsStatusHandler(
            enrichment_jobs=enrichment_jobs,
        )

    @provide(scope=Scope.REQUEST)
    def find_exam_workspace_answer_key_suggestions_handler(
        self,
        suggestion_jobs: ExamWorkspaceSuggestionJobQueryProtocol,
        vault_files: VaultFileRepositoryProtocol,
    ) -> FindExamWorkspaceAnswerKeySuggestionsHandlerProtocol:
        return FindExamWorkspaceAnswerKeySuggestionsHandler(
            suggestion_jobs=suggestion_jobs,
            vault_files=vault_files,
        )
