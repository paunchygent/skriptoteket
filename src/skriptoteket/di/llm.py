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
from skriptoteket.infrastructure.llm.chat_inflight_guard import InProcessChatInFlightGuard
from skriptoteket.infrastructure.llm.chat_ops_budget_resolver import (
    SettingsBasedChatOpsBudgetResolver,
)
from skriptoteket.infrastructure.llm.door.client import DoorBounds, HuleEduLlmDoorClient
from skriptoteket.infrastructure.llm.openai_provider import (
    OpenAIChatOpsProvider,
    OpenAIChatStreamProvider,
    OpenAIInlineCompletionProvider,
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
    ChatInFlightGuardProtocol,
    ChatOpsBudgetResolverProtocol,
    ChatOpsProviderProtocol,
    ChatStreamProviderProtocol,
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
from skriptoteket.protocols.llm_door import LlmDoorClientProtocol
from skriptoteket.protocols.sleeper import SleeperProtocol
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
    async def llm_door_client(
        self,
        settings: Settings,
        sleeper: SleeperProtocol,
    ) -> AsyncIterator[LlmDoorClientProtocol]:
        """The door's own bounded connection pool, closed with the app."""

        limits = httpx.Limits(
            max_connections=settings.LLM_DOOR_MAX_CONNECTIONS,
            max_keepalive_connections=settings.LLM_DOOR_MAX_KEEPALIVE_CONNECTIONS,
        )
        timeout = httpx.Timeout(
            settings.LLM_COMPLETION_TIMEOUT_SECONDS,
            pool=settings.LLM_DOOR_POOL_TIMEOUT_SECONDS,
        )
        async with httpx.AsyncClient(
            transport=httpx.AsyncHTTPTransport(limits=limits), timeout=timeout
        ) as client:
            yield HuleEduLlmDoorClient(
                client=client,
                base_url=settings.HULEEDU_LLM_PROVIDER_BASE_URL,
                internal_api_key=settings.HULEEDU_INTERNAL_API_KEY,
                job_overage_cap_usd_micros=round(settings.LLM_JOB_OVERAGE_CAP_USD * 1_000_000),
                sleeper=sleeper,
                bounds=DoorBounds.from_settings(settings),
            )

    @provide(scope=Scope.APP)
    def inline_completion_provider(
        self,
        settings: Settings,
        door: LlmDoorClientProtocol,
    ) -> InlineCompletionProviderProtocol:
        return OpenAIInlineCompletionProvider(settings=settings, door=door)

    @provide(scope=Scope.APP)
    def chat_ops_budget_resolver(self, settings: Settings) -> ChatOpsBudgetResolverProtocol:
        return SettingsBasedChatOpsBudgetResolver(settings=settings)

    @provide(scope=Scope.APP)
    def chat_budget_resolver(self, settings: Settings) -> ChatBudgetResolverProtocol:
        return SettingsBasedChatBudgetResolver(settings=settings)

    @provide(scope=Scope.APP)
    def chat_stream_provider(
        self,
        settings: Settings,
        door: LlmDoorClientProtocol,
    ) -> ChatStreamProviderProtocol:
        return OpenAIChatStreamProvider(settings=settings, door=door)

    @provide(scope=Scope.APP)
    def chat_ops_provider(
        self,
        settings: Settings,
        door: LlmDoorClientProtocol,
    ) -> ChatOpsProviderProtocol:
        return OpenAIChatOpsProvider(settings=settings, door=door)

    @provide(scope=Scope.APP)
    def chat_inflight_guard(self) -> ChatInFlightGuardProtocol:
        return InProcessChatInFlightGuard()

    @provide(scope=Scope.REQUEST)
    def inline_completion_handler(
        self,
        settings: Settings,
        provider: InlineCompletionProviderProtocol,
        capture_store: LlmCaptureStoreProtocol,
        token_counters: TokenCounterResolverProtocol,
    ) -> InlineCompletionHandlerProtocol:
        return InlineCompletionHandler(
            settings=settings,
            provider=provider,
            capture_store=capture_store,
            token_counters=token_counters,
        )

    @provide(scope=Scope.REQUEST)
    def edit_ops_handler(
        self,
        settings: Settings,
        provider: ChatOpsProviderProtocol,
        budget_resolver: ChatOpsBudgetResolverProtocol,
        payload_parser: EditOpsPayloadParserProtocol,
        guard: ChatInFlightGuardProtocol,
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
            provider=provider,
            budget_resolver=budget_resolver,
            payload_parser=payload_parser,
            guard=guard,
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
        guard: ChatInFlightGuardProtocol,
        budget_resolver: ChatBudgetResolverProtocol,
        turn_preparer: EditorChatTurnPreparerProtocol,
        stream_orchestrator: EditorChatStreamOrchestratorProtocol,
        token_counters: TokenCounterResolverProtocol,
    ) -> EditorChatHandlerProtocol:
        return EditorChatHandler(
            settings=settings,
            guard=guard,
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
        provider: ChatStreamProviderProtocol,
        uow: UnitOfWorkProtocol,
        turns: ToolSessionTurnRepositoryProtocol,
        messages: ToolSessionMessageRepositoryProtocol,
    ) -> EditorChatStreamOrchestratorProtocol:
        return EditorChatStreamOrchestrator(
            settings=settings,
            capture_store=capture_store,
            provider=provider,
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
