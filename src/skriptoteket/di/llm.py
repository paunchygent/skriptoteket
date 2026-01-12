"""LLM providers and handlers for editor AI capabilities."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
from dishka import Provider, Scope, provide

from skriptoteket.application.editor.chat_handler import EditorChatHandler
from skriptoteket.application.editor.chat_history_handler import EditorChatHistoryHandler
from skriptoteket.application.editor.clear_chat_handler import EditorChatClearHandler
from skriptoteket.application.editor.completion_handler import InlineCompletionHandler
from skriptoteket.application.editor.edit_ops_handler import EditOpsHandler
from skriptoteket.application.editor.edit_ops_preview_handler import (
    EditOpsApplyHandler,
    EditOpsPreviewHandler,
)
from skriptoteket.config import Settings
from skriptoteket.infrastructure.editor.unified_diff_applier import SubprocessUnifiedDiffApplier
from skriptoteket.infrastructure.llm.capture_store import ArtifactsLlmCaptureStore
from skriptoteket.infrastructure.llm.chat_failover_router import InProcessChatFailoverRouter
from skriptoteket.infrastructure.llm.chat_inflight_guard import InProcessChatInFlightGuard
from skriptoteket.infrastructure.llm.chat_ops_budget_resolver import (
    SettingsBasedChatOpsBudgetResolver,
)
from skriptoteket.infrastructure.llm.openai_provider import (
    OpenAIChatOpsProvider,
    OpenAIChatStreamProvider,
    OpenAIInlineCompletionProvider,
)
from skriptoteket.infrastructure.llm.provider_sets import (
    ChatOpsProviders,
    ChatStreamProviders,
    is_remote_llm_endpoint,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.editor_patches import UnifiedDiffApplierProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.llm import (
    ChatFailoverRouterProtocol,
    ChatInFlightGuardProtocol,
    ChatOpsBudgetResolverProtocol,
    ChatOpsProvidersProtocol,
    ChatStreamProvidersProtocol,
    EditOpsApplyHandlerProtocol,
    EditOpsHandlerProtocol,
    EditOpsPreviewHandlerProtocol,
    EditorChatClearHandlerProtocol,
    EditorChatHandlerProtocol,
    EditorChatHistoryHandlerProtocol,
    InlineCompletionHandlerProtocol,
    InlineCompletionProviderProtocol,
)
from skriptoteket.protocols.llm_captures import LlmCaptureStoreProtocol
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class LlmProvider(Provider):
    @provide(scope=Scope.APP)
    def unified_diff_applier(self) -> UnifiedDiffApplierProtocol:
        return SubprocessUnifiedDiffApplier()

    @provide(scope=Scope.APP)
    def llm_capture_store(self, settings: Settings) -> LlmCaptureStoreProtocol:
        return ArtifactsLlmCaptureStore(settings=settings)

    @provide(scope=Scope.APP)
    async def llm_http_client(self, settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
        timeout = httpx.Timeout(settings.LLM_COMPLETION_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout) as client:
            yield client

    @provide(scope=Scope.APP)
    def inline_completion_provider(
        self,
        settings: Settings,
        client: httpx.AsyncClient,
    ) -> InlineCompletionProviderProtocol:
        return OpenAIInlineCompletionProvider(settings=settings, client=client)

    @provide(scope=Scope.APP)
    def chat_failover_router(self, settings: Settings) -> ChatFailoverRouterProtocol:
        return InProcessChatFailoverRouter(settings=settings)

    @provide(scope=Scope.APP)
    def chat_ops_budget_resolver(self, settings: Settings) -> ChatOpsBudgetResolverProtocol:
        return SettingsBasedChatOpsBudgetResolver(settings=settings)

    @provide(scope=Scope.APP)
    def chat_stream_providers(
        self,
        settings: Settings,
        client: httpx.AsyncClient,
    ) -> ChatStreamProvidersProtocol:
        primary = OpenAIChatStreamProvider(settings=settings, client=client)

        fallback = None
        fallback_base_url = settings.LLM_CHAT_FALLBACK_BASE_URL.strip()
        fallback_model = settings.LLM_CHAT_FALLBACK_MODEL.strip()
        if fallback_base_url and fallback_model:
            fallback = OpenAIChatStreamProvider(
                settings=settings,
                client=client,
                base_url=fallback_base_url,
                model=fallback_model,
                reasoning_effort=settings.LLM_CHAT_FALLBACK_REASONING_EFFORT,
            )

        return ChatStreamProviders(
            primary=primary,
            fallback=fallback,
            fallback_is_remote=is_remote_llm_endpoint(fallback_base_url) if fallback else False,
        )

    @provide(scope=Scope.APP)
    def chat_ops_providers(
        self,
        settings: Settings,
        client: httpx.AsyncClient,
    ) -> ChatOpsProvidersProtocol:
        primary = OpenAIChatOpsProvider(settings=settings, client=client)

        fallback = None
        fallback_base_url = settings.LLM_CHAT_OPS_FALLBACK_BASE_URL.strip()
        fallback_model = settings.LLM_CHAT_OPS_FALLBACK_MODEL.strip()
        if fallback_base_url and fallback_model:
            fallback = OpenAIChatOpsProvider(
                settings=settings,
                client=client,
                base_url=fallback_base_url,
                model=fallback_model,
                reasoning_effort=settings.LLM_CHAT_OPS_FALLBACK_REASONING_EFFORT,
            )

        return ChatOpsProviders(
            primary=primary,
            fallback=fallback,
            fallback_is_remote=is_remote_llm_endpoint(fallback_base_url) if fallback else False,
        )

    @provide(scope=Scope.APP)
    def chat_inflight_guard(self) -> ChatInFlightGuardProtocol:
        return InProcessChatInFlightGuard()

    @provide(scope=Scope.REQUEST)
    def inline_completion_handler(
        self,
        settings: Settings,
        provider: InlineCompletionProviderProtocol,
    ) -> InlineCompletionHandlerProtocol:
        return InlineCompletionHandler(settings=settings, provider=provider)

    @provide(scope=Scope.REQUEST)
    def edit_ops_handler(
        self,
        settings: Settings,
        providers: ChatOpsProvidersProtocol,
        budget_resolver: ChatOpsBudgetResolverProtocol,
        guard: ChatInFlightGuardProtocol,
        failover: ChatFailoverRouterProtocol,
        capture_store: LlmCaptureStoreProtocol,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        messages: ToolSessionMessageRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> EditOpsHandlerProtocol:
        return EditOpsHandler(
            settings=settings,
            providers=providers,
            budget_resolver=budget_resolver,
            guard=guard,
            failover=failover,
            capture_store=capture_store,
            uow=uow,
            sessions=sessions,
            messages=messages,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def edit_ops_preview_handler(
        self,
        settings: Settings,
        capture_store: LlmCaptureStoreProtocol,
        patch_applier: UnifiedDiffApplierProtocol,
    ) -> EditOpsPreviewHandlerProtocol:
        return EditOpsPreviewHandler(
            settings=settings,
            capture_store=capture_store,
            patch_applier=patch_applier,
        )

    @provide(scope=Scope.REQUEST)
    def edit_ops_apply_handler(
        self,
        preview: EditOpsPreviewHandlerProtocol,
    ) -> EditOpsApplyHandlerProtocol:
        return EditOpsApplyHandler(preview=preview)

    @provide(scope=Scope.REQUEST)
    def editor_chat_handler(
        self,
        settings: Settings,
        providers: ChatStreamProvidersProtocol,
        guard: ChatInFlightGuardProtocol,
        failover: ChatFailoverRouterProtocol,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        messages: ToolSessionMessageRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> EditorChatHandlerProtocol:
        return EditorChatHandler(
            settings=settings,
            providers=providers,
            guard=guard,
            failover=failover,
            uow=uow,
            sessions=sessions,
            messages=messages,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def editor_chat_clear_handler(
        self,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        messages: ToolSessionMessageRepositoryProtocol,
    ) -> EditorChatClearHandlerProtocol:
        return EditorChatClearHandler(uow=uow, sessions=sessions, messages=messages)

    @provide(scope=Scope.REQUEST)
    def editor_chat_history_handler(
        self,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        messages: ToolSessionMessageRepositoryProtocol,
        clock: ClockProtocol,
    ) -> EditorChatHistoryHandlerProtocol:
        return EditorChatHistoryHandler(
            uow=uow,
            sessions=sessions,
            messages=messages,
            clock=clock,
        )
