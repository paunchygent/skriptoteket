"""Recorded transport and production composition for the DOCX background job proofs.

``RecordedTransport`` serves the live replies recorded in
``tests/fixtures/exam_conversion/docx_key_provenance_v14/<exam>/`` to the real HTTP adapters, so the
job handler, ``build_docx_conversion_pipeline`` composition, progress port, job queue,
vault storage and QTI validators run unchanged around it. Each ``label_b`` recording
carries its capture-time request key in ``label_b_<qid>.request.txt``, followed by one final
newline.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from pathlib import Path
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
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.llm.door.client import HuleEduLlmDoorClient
from skriptoteket.infrastructure.llm.openai.answer_key_structured_provider import (
    OpenAIAnswerKeyStructuredProvider,
)
from skriptoteket.infrastructure.repositories.exam_index_repository import (
    PostgreSQLExamIndexRepository,
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
from skriptoteket.protocols.sleeper import SleeperProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.label_b_request_keys import label_b_request_keys, matching_label_b

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

    def __init__(self, recordings: Path) -> None:
        self._dir = recordings
        self._decisions = sorted(
            self._dir.glob("decisions_*.json"), key=lambda p: int(p.stem.rsplit("_", 1)[1])
        )
        self._batches: dict[str, JsonValue] = {
            p.stem: json.loads(p.read_text()) for p in self._dir.glob("docx_w*.json")
        }
        self._label_keys = label_b_request_keys(self._dir)
        self._groupings = 0
        self.served: list[str] = []
        self.unmatched: list[str] = []
        self.decisions_requests = 0
        self.responses_requests = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/decisions"):
            assert request.headers["Authorization"] == f"Bearer {API_KEY}"
            self.decisions_requests += 1
            if len(self.served_decisions) >= len(self._decisions):
                return self._unmatched("more Decisions requests than recordings")
            path = self._decisions[len(self.served_decisions)]
            self.served.append(path.stem)
            return httpx.Response(200, json=json.loads(path.read_text()))
        assert request.url.path == "/internal/v1/openai/responses"
        assert request.headers["X-Internal-API-Key"] == API_KEY
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
            return matching_label_b(self._label_keys, text, self.served)
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
    uow: UnitOfWorkProtocol,
    progress: DocxConversionProgressProtocol,
    sleeper: SleeperProtocol,
) -> DocxConversionPipeline:
    """The production composition over the door client and the Decisions adapter."""
    door = HuleEduLlmDoorClient(
        client=client,
        base_url="https://door.test",
        internal_api_key=API_KEY,
        job_overage_cap_usd_micros=1_000_000,
    )
    return build_docx_conversion_pipeline(
        client=client,
        provider=OpenAIAnswerKeyStructuredProvider(
            door=door,
            timeout_seconds=30,
        ),
        sleeper=sleeper,
        uow=SerializedUnitOfWork(uow),
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
        index=PostgreSQLExamIndexRepository(session),
        codec=ExamWorkspaceContainerCodec(),
        uow=uow or SQLAlchemyUnitOfWork(session),
        clock=clock,
        settings=settings,
    )
