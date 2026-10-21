"""DI bindings for exam answer-key enrichment.

Enrichment job repository, the structured provider, and the enrichment job
and workspace handlers.
"""

from __future__ import annotations

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_jobs import (
    ProcessExamAnswerKeyEnrichmentJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_content_tags import (
    ProcessExamContentSuggestionsHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_digiexam_jobs import (
    ProcessExamWorkspaceDigiExamJobHandler,
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
from skriptoteket.infrastructure.llm.openai.answer_key_profiles import build_luna_answer_key_profile
from skriptoteket.infrastructure.llm.openai.answer_key_structured_provider import (
    OpenAIAnswerKeyStructuredProvider,
)
from skriptoteket.infrastructure.repositories.exam_answer_key_enrichment_jobs import (
    PostgreSQLExamAnswerKeyEnrichmentJobRepository,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import (
    AnswerKeyStructuredProviderProtocol,
    ExamAnswerKeyEnrichmentJobRepositoryProtocol,
    ExamWorkspaceSuggestionJobQueryProtocol,
)
from skriptoteket.protocols.exam_workspace import (
    FindExamWorkspaceAnswerKeySuggestionsHandlerProtocol,
    GetExamWorkspaceAnswerKeySuggestionsStatusHandlerProtocol,
    RequestExamWorkspaceAnswerKeySuggestionsHandlerProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import UserRepositoryProtocol
from skriptoteket.protocols.llm_door import LlmDoorClientProtocol
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

    @provide(scope=Scope.APP)
    def answer_key_structured_provider(
        self,
        settings: Settings,
        door: LlmDoorClientProtocol,
    ) -> AnswerKeyStructuredProviderProtocol:
        return OpenAIAnswerKeyStructuredProvider(
            door=door,
            timeout_seconds=float(settings.LLM_ANSWER_KEY_TIMEOUT_SECONDS),
        )

    @provide(scope=Scope.REQUEST)
    def process_exam_answer_key_enrichment_job_handler(
        self,
        enrichment_jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        provider: AnswerKeyStructuredProviderProtocol,
        users: UserRepositoryProtocol,
        settings: Settings,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        docx_handler: ProcessExamWorkspaceDocxJobHandler,
        digiexam_handler: ProcessExamWorkspaceDigiExamJobHandler,
        content_tags_handler: ProcessExamContentSuggestionsHandler,
    ) -> ProcessExamAnswerKeyEnrichmentJobHandler:
        return ProcessExamAnswerKeyEnrichmentJobHandler(
            enrichment_jobs=enrichment_jobs,
            provider=provider,
            users=users,
            answer_key_profile=build_luna_answer_key_profile(settings),
            uow=uow,
            clock=clock,
            docx_handler=docx_handler,
            digiexam_handler=digiexam_handler,
            content_tags_handler=content_tags_handler,
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
