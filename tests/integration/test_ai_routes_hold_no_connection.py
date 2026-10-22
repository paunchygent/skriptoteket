"""AI web routes release their database connection before the provider call runs.

TASK-SKRIPT-41-01-04 unit E. Production allows about 40 database connections across all
processes, so 1,000 concurrent AI calls are possible only while no AI call holds one. Each
test sends a real HTTP request through the real route, the real signed-identity dependency
and the production container, with a fake provider at the provider seam that samples the
connections held at the moment it is called (``ai_route_connection_support``).

The brief expected the editor routes to hold a connection through an auth or maintainer
read and the one-question retry route to hold its document-lineage lock across the call.
The measurements below show neither: the auth resolver and every editor handler end their
reads inside ``async with uow:``, ``require_tool_access`` returns before any read for the
admin and superuser roles that ``require_app_ai_api`` admits, and the retry handler closes
its ``store.transaction`` block (lock and payload guard) before ``_reconvert`` runs.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from dishka import Provider, Scope, provide
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.exam_workspace import RetryExamWorkspaceItemRequest
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_rounds import (
    DocxRoundReply,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_retry import (
    RetryExamWorkspaceItemHandler,
)
from skriptoteket.application.editor.chat_shared import STREAM_FLUSH_MIN_CHARS
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
    StructuredLLMUsage,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import ExamWorkspaceContainerContent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.llm_door import AiDoorCaller
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from skriptoteket.protocols.exam_workspace import (
    ExamWorkspaceContainerCodecProtocol,
    RetryExamWorkspaceItemHandlerProtocol,
)
from skriptoteket.protocols.llm import (
    ChatOpsProviderProtocol,
    ChatStreamProviderProtocol,
    InlineCompletionProviderProtocol,
    LLMChatOpsResponse,
    LLMChatRequest,
    LLMCompletionRequest,
    LLMCompletionResponse,
)
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol
from tests.integration.ai_route_connection_support import (
    ConnectionProbe,
    ai_route_harness,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    PROFILE,
    document,
    item,
    retry_reply,
    source,
)

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]

_VIRTUAL_FILES = {
    "tool.py": "print(1)\n",
    "entrypoint.txt": "run\n",
    "settings_schema.json": "null",
    "input_schema.json": "[]",
    "usage_instructions.md": "",
}
_EMPTY_EDIT_OPS = '{"assistant_message": "Klart.", "ops": []}'


class _ProbedInline:
    def __init__(self, probe: ConnectionProbe) -> None:
        self._probe = probe

    async def complete_inline(
        self, *, request: LLMCompletionRequest, system_prompt: str, caller: AiDoorCaller
    ) -> LLMCompletionResponse:
        await self._probe.sample("inline completion")
        return LLMCompletionResponse(completion="x = 1", finish_reason="stop")


class _ProbedChatStream:
    def __init__(self, probe: ConnectionProbe) -> None:
        self._probe = probe

    async def stream_chat(
        self, *, request: LLMChatRequest, system_prompt: str, caller: AiDoorCaller
    ) -> AsyncIterator[str]:
        # The orchestrator persists the partial answer between deltas, so sample at every
        # step: the orchestrator opens and closes its own transaction around each flush.
        await self._probe.sample("chat stream start")
        for index in range(3):
            yield "a" * (STREAM_FLUSH_MIN_CHARS + 1)
            await self._probe.sample(f"chat stream after delta {index}")


class _ProbedChatOps:
    def __init__(self, probe: ConnectionProbe) -> None:
        self._probe = probe

    async def complete_chat_ops(
        self, *, request: LLMChatRequest, system_prompt: str, caller: AiDoorCaller
    ) -> LLMChatOpsResponse:
        await self._probe.sample("edit ops")
        return LLMChatOpsResponse(content=_EMPTY_EDIT_OPS, finish_reason="stop")


class _ProbedExchange:
    def __init__(self, probe: ConnectionProbe) -> None:
        self._probe = probe

    async def exchange(
        self,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
        caller: AiDoorCaller,
    ) -> DocxRoundReply:
        await self._probe.sample("docx one-question retry")
        return DocxRoundReply(
            response=StructuredLLMResponse(
                content=retry_reply(), finish_reason="completed", usage=StructuredLLMUsage()
            )
        )


class FakeAiProviders(Provider):
    """Replace every AI provider seam the four routes reach with a connection-sampling fake."""

    def __init__(self, probe: ConnectionProbe) -> None:
        super().__init__()
        self._probe = probe

    @provide(scope=Scope.APP, override=True)
    def inline_completion_provider(self) -> InlineCompletionProviderProtocol:
        return _ProbedInline(self._probe)

    @provide(scope=Scope.APP, override=True)
    def chat_stream_provider(self) -> ChatStreamProviderProtocol:
        return _ProbedChatStream(self._probe)

    @provide(scope=Scope.APP, override=True)
    def chat_ops_provider(self) -> ChatOpsProviderProtocol:
        return _ProbedChatOps(self._probe)

    @provide(scope=Scope.REQUEST, override=True)
    def retry_item_handler(
        self,
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
    ) -> RetryExamWorkspaceItemHandlerProtocol:
        return RetryExamWorkspaceItemHandler(
            vault_files=vault_files,
            codec=codec,
            store=store,
            exchange=_ProbedExchange(self._probe),
            profile=PROFILE,
            enabled=True,
        )


def _assert_no_connection_held(probe: ConnectionProbe, *, at_least: int = 1) -> None:
    assert len(probe.samples) >= at_least, probe.samples
    assert probe.held_during_calls() == [0] * len(probe.samples), probe.samples


async def test_probe_counts_a_connection_that_a_request_leaves_open(
    migrated_db: str, tmp_path
) -> None:
    """Control: an open autobegun transaction shows in both counts, so a zero is meaningful."""
    probe = ConnectionProbe()
    async with ai_route_harness(
        database_url=migrated_db, work_dir=tmp_path, probe=probe, fakes=FakeAiProviders(probe)
    ) as harness:
        sessions = await harness.container.get(async_sessionmaker[AsyncSession])
        async with sessions() as session:
            await session.execute(text("SELECT 1"))
            await probe.sample("open read transaction")
        await probe.sample("after session close")
    assert (probe.samples[0].checked_out, probe.samples[0].idle_in_transaction) == (1, 1)
    assert probe.samples[1].held == 0


async def test_inline_completion_holds_no_connection_during_the_provider_call(
    migrated_db: str, tmp_path
) -> None:
    probe = ConnectionProbe()
    async with ai_route_harness(
        database_url=migrated_db, work_dir=tmp_path, probe=probe, fakes=FakeAiProviders(probe)
    ) as harness:
        response = await harness.client.post(
            "/api/v1/editor/completions",
            json={"prefix": "def f():\n    ", "suffix": "", "active_file": "tool.py"},
            headers=harness.headers,
        )
        assert response.status_code == 200, response.text
        assert response.json()["completion"]
    _assert_no_connection_held(probe)


async def test_chat_stream_holds_no_connection_while_the_provider_streams(
    migrated_db: str, tmp_path
) -> None:
    probe = ConnectionProbe()
    async with ai_route_harness(
        database_url=migrated_db, work_dir=tmp_path, probe=probe, fakes=FakeAiProviders(probe)
    ) as harness:
        response = await harness.client.post(
            f"/api/v1/editor/tools/{harness.tool_id}/chat",
            json={"message": "Hej"},
            headers=harness.headers,
        )
        assert response.status_code == 200, response.text
        assert "event: done" in response.text, response.text
    _assert_no_connection_held(probe, at_least=4)


async def test_edit_ops_holds_no_connection_during_the_provider_call(
    migrated_db: str, tmp_path
) -> None:
    probe = ConnectionProbe()
    async with ai_route_harness(
        database_url=migrated_db, work_dir=tmp_path, probe=probe, fakes=FakeAiProviders(probe)
    ) as harness:
        response = await harness.client.post(
            "/api/v1/editor/edit-ops",
            json={
                "tool_id": str(harness.tool_id),
                "message": "Byt namn",
                "active_file": "tool.py",
                "virtual_files": _VIRTUAL_FILES,
            },
            headers=harness.headers,
        )
        assert response.status_code == 200, response.text
        assert response.json()["enabled"] is True, response.text
    _assert_no_connection_held(probe)


async def test_one_question_retry_holds_no_connection_during_the_converter_call(
    migrated_db: str, tmp_path
) -> None:
    """The handler closes its lineage lock, payload guard and transaction before converting."""
    probe = ConnectionProbe()
    async with ai_route_harness(
        database_url=migrated_db, work_dir=tmp_path, probe=probe, fakes=FakeAiProviders(probe)
    ) as harness:
        lineage_id = uuid4()
        saved = document(
            lineage_id=lineage_id,
            items=(item("item_001", 1, anchor="body:0001", source=source()),),
        )
        async with harness.container() as scope:
            store = await scope.get(ExamWorkspaceDocumentStore)
            await store.save(
                actor=harness.actor,
                file_id=uuid4(),
                name="omprov.provdokument.zip",
                content=ExamWorkspaceContainerCodec().build(
                    content=ExamWorkspaceContainerContent(document=saved, assets_by_id={})
                ),
                lineage_id=lineage_id,
                version=saved.revision,
            )
        request = RetryExamWorkspaceItemRequest(
            document=saved, item_id="item_001", kind=NativeExamItemKind.FREE_TEXT
        )
        response = await harness.client.post(
            f"/api/v1/apps/documents.conversion_hub/exam-workspace/documents/{lineage_id}"
            "/items/retry",
            json=request.model_dump(mode="json"),
            headers=harness.headers,
        )
        assert response.status_code == 200, response.text
    _assert_no_connection_held(probe)
