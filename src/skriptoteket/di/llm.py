"""LLM providers and handlers for editor AI capabilities."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
from dishka import Provider, Scope, provide

from skriptoteket.application.editor.chat_handler import EditorChatHandler
from skriptoteket.application.editor.chat_history_handler import EditorChatHistoryHandler
from skriptoteket.application.editor.chat_prompt_builder import SettingsBasedEditorChatPromptBuilder
from skriptoteket.application.editor.chat_stream_orchestrator import EditorChatStreamOrchestrator
from skriptoteket.application.editor.chat_turn_preparer import EditorChatTurnPreparer
from skriptoteket.application.editor.clear_chat_handler import EditorChatClearHandler
from skriptoteket.application.editor.completion_handler import InlineCompletionHandler
from skriptoteket.application.editor.edit_ops_handler import EditOpsHandler
from skriptoteket.application.editor.edit_ops_payload_parser import DefaultEditOpsPayloadParser
from skriptoteket.application.editor.edit_ops_preview_handler import (
    EditOpsApplyHandler,
    EditOpsPreviewHandler,
)
from skriptoteket.config import Settings
from skriptoteket.infrastructure.editor.unified_diff_applier import NativeUnifiedDiffApplier
from skriptoteket.infrastructure.llm.capture_store import ArtifactsLlmCaptureStore
from skriptoteket.infrastructure.llm.chat_budget_resolver import SettingsBasedChatBudgetResolver
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
from skriptoteket.infrastructure.llm.token_counter_resolver import SettingsBasedTokenCounterResolver
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.edit_ops_payload_parser import EditOpsPayloadParserProtocol
from skriptoteket.protocols.editor_chat import (
    EditorChatPromptBuilderProtocol,
    EditorChatStreamOrchestratorProtocol,
    EditorChatTurnPreparerProtocol,
)
from skriptoteket.protocols.editor_patches import UnifiedDiffApplierProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.llm import (
    ChatBudgetResolverProtocol,
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
from skriptoteket.protocols.token_counter import TokenCounterResolverProtocol
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_session_turns import ToolSessionTurnRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class LlmProvider(Provider):
    @provide(scope=Scope.APP)
    def unified_diff_applier(self) -> UnifiedDiffApplierProtocol:
        return NativeUnifiedDiffApplier()

    @provide(scope=Scope.APP)
    def llm_capture_store(self, settings: Settings) -> LlmCaptureStoreProtocol:
        return ArtifactsLlmCaptureStore(settings=settings)

    @provide(scope=Scope.APP)
    def token_counter_resolver(self, settings: Settings) -> TokenCounterResolverProtocol:
        return SettingsBasedTokenCounterResolver(settings=settings)

    @provide(scope=Scope.APP)
    def edit_ops_payload_parser(self) -> EditOpsPayloadParserProtocol:
        return DefaultEditOpsPayloadParser()

    @provide(scope=Scope.APP)
    def editor_chat_prompt_builder(self, settings: Settings) -> EditorChatPromptBuilderProtocol:
        return SettingsBasedEditorChatPromptBuilder(settings=settings)

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
    def chat_budget_resolver(self, settings: Settings) -> ChatBudgetResolverProtocol:
        return SettingsBasedChatBudgetResolver(settings=settings)

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
        token_counters: TokenCounterResolverProtocol,
    ) -> InlineCompletionHandlerProtocol:
        return InlineCompletionHandler(
            settings=settings,
            provider=provider,
            token_counters=token_counters,
        )

    @provide(scope=Scope.REQUEST)
    def edit_ops_handler(
        self,
        settings: Settings,
        providers: ChatOpsProvidersProtocol,
        budget_resolver: ChatOpsBudgetResolverProtocol,
        payload_parser: EditOpsPayloadParserProtocol,
        guard: ChatInFlightGuardProtocol,
        failover: ChatFailoverRouterProtocol,
        capture_store: LlmCaptureStoreProtocol,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        turns: ToolSessionTurnRepositoryProtocol,
        messages: ToolSessionMessageRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        token_counters: TokenCounterResolverProtocol,
    ) -> EditOpsHandlerProtocol:
        return EditOpsHandler(
            settings=settings,
            providers=providers,
            budget_resolver=budget_resolver,
            payload_parser=payload_parser,
            guard=guard,
            failover=failover,
            capture_store=capture_store,
            uow=uow,
            sessions=sessions,
            turns=turns,
            messages=messages,
            clock=clock,
            id_generator=id_generator,
            token_counters=token_counters,
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
        budget_resolver: ChatBudgetResolverProtocol,
        turn_preparer: EditorChatTurnPreparerProtocol,
        stream_orchestrator: EditorChatStreamOrchestratorProtocol,
        token_counters: TokenCounterResolverProtocol,
    ) -> EditorChatHandlerProtocol:
        return EditorChatHandler(
            settings=settings,
            providers=providers,
            guard=guard,
            failover=failover,
            budget_resolver=budget_resolver,
            turn_preparer=turn_preparer,
            stream_orchestrator=stream_orchestrator,
            token_counters=token_counters,
        )

    @provide(scope=Scope.REQUEST)
    def editor_chat_turn_preparer(
        self,
        settings: Settings,
        prompt_builder: EditorChatPromptBuilderProtocol,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        turns: ToolSessionTurnRepositoryProtocol,
        messages: ToolSessionMessageRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> EditorChatTurnPreparerProtocol:
        return EditorChatTurnPreparer(
            settings=settings,
            prompt_builder=prompt_builder,
            uow=uow,
            sessions=sessions,
            turns=turns,
            messages=messages,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def editor_chat_stream_orchestrator(
        self,
        settings: Settings,
        capture_store: LlmCaptureStoreProtocol,
        providers: ChatStreamProvidersProtocol,
        failover: ChatFailoverRouterProtocol,
        uow: UnitOfWorkProtocol,
        turns: ToolSessionTurnRepositoryProtocol,
        messages: ToolSessionMessageRepositoryProtocol,
    ) -> EditorChatStreamOrchestratorProtocol:
        return EditorChatStreamOrchestrator(
            settings=settings,
            capture_store=capture_store,
            providers=providers,
            failover=failover,
            uow=uow,
            turns=turns,
            messages=messages,
        )

    @provide(scope=Scope.REQUEST)
    def editor_chat_clear_handler(
        self,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        turns: ToolSessionTurnRepositoryProtocol,
        messages: ToolSessionMessageRepositoryProtocol,
    ) -> EditorChatClearHandlerProtocol:
        return EditorChatClearHandler(uow=uow, sessions=sessions, turns=turns, messages=messages)

    @provide(scope=Scope.REQUEST)
    def editor_chat_history_handler(
        self,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        turns: ToolSessionTurnRepositoryProtocol,
        messages: ToolSessionMessageRepositoryProtocol,
        clock: ClockProtocol,
    ) -> EditorChatHistoryHandlerProtocol:
        return EditorChatHistoryHandler(
            uow=uow,
            sessions=sessions,
            turns=turns,
            messages=messages,
            clock=clock,
        )
