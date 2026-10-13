"""Recorded transport and production composition for the DOCX background job proofs.

``RecordedTransport`` serves the live replies recorded in
``tests/fixtures/exam_conversion/docx_build_v10/<exam>/`` to the real HTTP adapters, so the
job handler, ``build_docx_conversion_pipeline`` composition, progress port, job queue, token
ledger, vault storage and QTI validators run unchanged around it.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, JsonValue
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_progress import (
    ExamWorkspaceConversionProgress,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_pipeline import (
    DocxConversionPipeline,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_serial_uow import (
    SerializedUnitOfWork,
)
from skriptoteket.config import Settings
from skriptoteket.di.docx_conversion import build_docx_conversion_pipeline
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    manifest_from_output,
    question_source,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_labeler_markdown import (  # noqa: E501
    PythonDocxLabelerMarkdown,
)
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.llm.openai.answer_key_structured_provider import (
    OpenAIAnswerKeyStructuredProvider,
)
from skriptoteket.infrastructure.repositories.user_vault_file_repository import (
    PostgreSQLUserVaultFileRepository,
)
from skriptoteket.infrastructure.repositories.user_vault_usage_repository import (
    PostgreSQLUserVaultUsageRepository,
)
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.docx_conversion_progress import (
    ConversionOutline,
    ConversionUpdate,
    DocxConversionProgressProtocol,
)
from skriptoteket.protocols.exam_answer_key import AnswerKeyTokenLeaseRepositoryProtocol
from skriptoteket.protocols.sleeper import SleeperProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    RECORDINGS,
    corpus_docx,
)

API_KEY = "fixture-key"


class _ResponseFormat(BaseModel):
    name: str
    strict: bool


class _ResponseText(BaseModel):
    format: _ResponseFormat


class _InputContent(BaseModel):
    text: str


class _InputMessage(BaseModel):
    content: list[_InputContent]


class _ResponsesRequest(BaseModel):
    """The parts of a Responses request body the transport keys a recording by."""

    model_config = ConfigDict(extra="allow")

    text: _ResponseText
    input: list[_InputMessage]


class _AnchoredChunk(BaseModel):
    anchor: str


class _BuildRequestBody(BaseModel):
    """The ``docx_exam_build`` user payload: pending chunks and the context around them."""

    chunks: list[_AnchoredChunk]
    context_chunks: list[_AnchoredChunk]


def _anchors(node: JsonValue) -> set[str]:
    """Every source or answer-key anchor a recorded converter reply cites."""
    found: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            if key in {"source_anchors", "answer_key_anchors"} and isinstance(value, list):
                found.update(a for a in value if isinstance(a, str))
            else:
                found |= _anchors(value)
    elif isinstance(node, list):
        for value in node:
            found |= _anchors(value)
    return found


class RecordedTransport:
    """Serve each real HTTP request the recording the live run got for the same request."""

    def __init__(self, exam: str) -> None:
        self._dir = RECORDINGS / exam
        self._decisions = sorted(
            self._dir.glob("decisions_*.json"), key=lambda p: int(p.stem.rsplit("_", 1)[1])
        )
        self._batches: dict[str, JsonValue] = {
            p.stem: json.loads(p.read_text()) for p in self._dir.glob("docx_w*.json")
        }
        self._label_texts = self._label_b_source_texts(exam)
        self._groupings = 0
        self.served: list[str] = []
        self.unmatched: list[str] = []
        self.decisions_requests = 0
        self.responses_requests = 0

    def _label_b_source_texts(self, exam: str) -> dict[str, str]:
        """The second-pass source text of each recorded label_b question."""
        content = corpus_docx(exam)
        chunks = PythonDocxExamChunker().chunk(content=content)
        try:
            source = PythonDocxLabelerMarkdown().source(content=content).chunks
        except ValueError:
            source = chunks
        manifest = manifest_from_output(
            json.loads((self._dir / "docx_grouping_1.json").read_text()), chunks
        )
        return {
            p.stem: question_source(manifest, source, p.stem.removeprefix("label_b_"))
            for p in self._dir.glob("label_b_*.json")
        }

    def __call__(self, request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == f"Bearer {API_KEY}"
        if request.url.path.endswith("/decisions"):
            self.decisions_requests += 1
            if len(self.served_decisions) >= len(self._decisions):
                return self._unmatched("more Decisions requests than recordings")
            path = self._decisions[len(self.served_decisions)]
            self.served.append(path.stem)
            return httpx.Response(200, json=json.loads(path.read_text()))
        assert request.url.path == "/v1/responses"
        self.responses_requests += 1
        payload = _ResponsesRequest.model_validate_json(request.content)
        assert payload.text.format.strict is True and "tools" not in (payload.model_extra or {})
        name = self._resolve(payload)
        if name is None:
            return self._unmatched(f"no recording for {payload.text.format.name}")
        self.served.append(name)
        body = (self._dir / f"{name}.json").read_text()
        output = [{"type": "message", "content": [{"type": "output_text", "text": body}]}]
        return httpx.Response(200, json={"status": "completed", "output": output})

    @property
    def served_decisions(self) -> list[str]:
        return [name for name in self.served if name.startswith("decisions_")]

    def _unmatched(self, why: str) -> httpx.Response:
        self.unmatched.append(why)
        return httpx.Response(500, json={"error": why})

    def _resolve(self, payload: _ResponsesRequest) -> str | None:
        schema_name = payload.text.format.name
        text = payload.input[0].content[0].text
        if schema_name == "exam_source_manifest":
            self._groupings += 1
            return f"docx_grouping_{self._groupings}"
        if schema_name == "item_type_label":
            return next(
                (
                    n
                    for n, src in self._label_texts.items()
                    if n not in self.served and text.endswith(f"### Question q1\n{src}")
                ),
                None,
            )
        assert schema_name == "docx_exam_build"
        body = _BuildRequestBody.model_validate_json(text)
        pending = {c.anchor for c in body.chunks}
        visible = pending | {c.anchor for c in body.context_chunks}
        fits = {
            n: len(_anchors(r) & pending)
            for n, r in self._batches.items()
            if n not in self.served and _anchors(r) <= visible and _anchors(r) & pending
        }
        return max(sorted(fits), key=lambda n: fits[n], default=None)

    def all_recordings(self) -> list[str]:
        return sorted(p.stem for p in self._dir.glob("*.json"))


class SavedRevisions(ExamWorkspaceConversionProgress):
    """The production progress port; after each save it reads the saved head back."""

    observe: Callable[[str, UUID], Awaitable[None]]  # set by the test before use

    async def outline(self, *, worker_id: str, job_id: UUID, outline: ConversionOutline) -> None:
        await super().outline(worker_id=worker_id, job_id=job_id, outline=outline)
        await self.observe("outline", job_id)

    async def batch_ready(self, *, worker_id: str, job_id: UUID, update: ConversionUpdate) -> None:
        await super().batch_ready(worker_id=worker_id, job_id=job_id, update=update)
        await self.observe("batch_ready", job_id)


def build_pipeline(
    client: httpx.AsyncClient,
    *,
    settings: Settings,
    leases: AnswerKeyTokenLeaseRepositoryProtocol,
    uow: UnitOfWorkProtocol,
    clock: ClockProtocol,
    progress: DocxConversionProgressProtocol,
    sleeper: SleeperProtocol,
) -> DocxConversionPipeline:
    """The production composition over real Responses and Decisions adapters."""
    return build_docx_conversion_pipeline(
        client=client,
        provider=OpenAIAnswerKeyStructuredProvider(
            client=client,
            base_url=settings.LLM_ANSWER_KEY_BASE_URL,
            api_key=API_KEY,
            timeout_seconds=30,
        ),
        sleeper=sleeper,
        leases=leases,
        uow=SerializedUnitOfWork(uow),
        clock=clock,
        settings=settings,
        progress=progress,
    )


def document_store(
    session: AsyncSession,
    *,
    storage: LocalVaultStorage,
    clock: ClockProtocol,
    settings: Settings,
    uow: SQLAlchemyUnitOfWork | None = None,
) -> ExamWorkspaceDocumentStore:
    return ExamWorkspaceDocumentStore(
        vault_files=PostgreSQLUserVaultFileRepository(session),
        vault_usage=PostgreSQLUserVaultUsageRepository(session),
        vault_storage=storage,
        uow=uow or SQLAlchemyUnitOfWork(session),
        clock=clock,
        settings=settings,
    )
