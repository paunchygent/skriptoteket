"""Replay one exam's live recordings through the production DOCX conversion pipeline.

The pipeline is built by ``build_docx_conversion_pipeline``, the composition the DOCX job and
the exam-conversion eval use. Only the network is replaced: the Decisions first pass reads
``decisions_N.json`` in request order, and every Responses call (grouping, second-pass labels,
type batches) reads unmodified replies from
``tests/fixtures/exam_conversion/docx_key_provenance_v14/<exam>/``. All converter
batches are matched once by their source/facit anchors within the request's
visible chunks, as in the HTTP replay transport.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from types import TracebackType
from uuid import UUID, uuid4

import httpx
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_pipeline import (
    DocxConversionPipeline,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_run import (
    DocxConversionJob,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_serial_uow import (
    SerializedUnitOfWork,
)
from skriptoteket.config import Settings
from skriptoteket.di.docx_conversion import build_docx_conversion_pipeline
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
    StructuredLLMUsage,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    AnswerKeyTokenLease,
    AnswerKeyTokenLeaseDayUsage,
    AnswerKeyTokenLeaseState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.identity.models import User
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.protocols.docx_conversion_progress import (
    ConversionOutline,
    ConversionUpdate,
    DocxConversionProgressProtocol,
)
from skriptoteket.protocols.exam_answer_key import AnswerKeyTokenLeaseRepositoryProtocol
from tests.fixtures.time_fixtures import FixedClock

FIXTURES = Path("tests/fixtures/exam_conversion")
CORPUS = FIXTURES / "docx_corpus"
RECORDINGS = FIXTURES / "docx_key_provenance_v14"
WORKER = "replay-worker"
# The live run behind RECORDINGS packed 16 families per batch; batch request ids follow it.
RECORDED_FAMILIES_PER_BATCH = 16
_NOW = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)


def recorded_exams() -> tuple[str, ...]:
    """Every exam that has live recordings, which is every corpus exam."""
    return tuple(sorted(path.name for path in RECORDINGS.iterdir() if path.is_dir()))


def corpus_docx(exam: str, corpus: Path | None = None) -> bytes:
    return ((corpus or CORPUS) / f"{exam}.docx").read_bytes()


def corpus_chunks(exam: str) -> tuple[DocxChunk, ...]:
    return PythonDocxExamChunker().chunk(content=corpus_docx(exam))


def recording(exam: str, name: str, root: Path = RECORDINGS) -> dict[str, JsonValue]:
    """One recorded reply, such as ``docx_grouping_1`` or ``docx_w2-01-01``."""
    reply: dict[str, JsonValue] = json.loads((root / exam / f"{name}.json").read_text())
    return reply


class MissingRecording(AssertionError):
    """The pipeline made a request the live run never made."""


class ReplayProvider:
    """Replay current replies; match every converter batch once by visible source anchors."""

    def __init__(
        self,
        exam: str,
        failures: Mapping[str, Exception] | None = None,
        root: Path = RECORDINGS,
    ) -> None:
        self._exam = exam
        self._root = root
        self._failures = dict(failures or {})
        self.requests: list[StructuredLLMRequest] = []
        self.recording_ids: dict[str, str] = {}
        self.served: list[tuple[str, str]] = []
        self._served: set[str] = set()

    @property
    def request_ids(self) -> list[str]:
        return [request.item_id for request in self.requests]

    async def complete_structured(
        self, *, request: StructuredLLMRequest, profile: StructuredLLMProviderProfile
    ) -> StructuredLLMResponse:
        self.requests.append(request)
        if request.item_id in self._failures:
            raise self._failures[request.item_id]
        name = request.item_id.replace(":", "_")
        if request.output_spec.schema_name == "docx_exam_build":
            payload = json.loads(request.user_payload)
            pending = {chunk["anchor"] for chunk in payload["chunks"]}
            grouping = recording(self._exam, "docx_grouping_1", self._root)
            headers = grouping["header_anchors"]
            assert isinstance(headers, list)
            header_anchors = {
                anchor
                for entry in headers
                if isinstance(entry, dict)
                for anchor in [entry.get("anchor")]
                if isinstance(anchor, str)
            }
            visible = (
                pending | {chunk["anchor"] for chunk in payload["context_chunks"]} | header_anchors
            )
            fits = {}
            for candidate in sorted((self._root / self._exam).glob("docx_w*.json")):
                if candidate.stem in self._served:
                    continue
                anchors = _claimed(json.loads(candidate.read_text()))
                if anchors <= visible and anchors & pending:
                    fits[candidate.stem] = len(anchors & pending)
            if not fits:
                raise MissingRecording(f"{self._exam}: no unused batch reply for {sorted(pending)}")
            name = max(fits, key=lambda candidate: fits[candidate])
        path = self._root / self._exam / f"{name}.json"
        if not path.exists():
            raise MissingRecording(
                f"{self._exam}: no recording for request id {request.item_id!r} ({path.name})"
            )
        self.recording_ids[request.item_id] = name
        self.served.append((request.item_id, name))
        self._served.add(name)
        return StructuredLLMResponse(
            content=json.loads(path.read_text()),
            finish_reason="completed",
            usage=StructuredLLMUsage(),
        )


def _claimed(reply: Mapping[str, JsonValue]) -> set[str]:
    def anchors(node: JsonValue) -> set[str]:
        if isinstance(node, list):
            return set().union(*(anchors(value) for value in node))
        if not isinstance(node, dict):
            return set()
        found: set[str] = set()
        for key, value in node.items():
            if key in {"source_anchors", "answer_key_anchors"} and isinstance(value, list):
                found.update(anchor for anchor in value if isinstance(anchor, str))
            else:
                found.update(anchors(value))
        return found

    return anchors(dict(reply))


def decisions_client(exam: str, root: Path = RECORDINGS) -> httpx.AsyncClient:
    """Serve ``decisions_N.json`` in request order to POST .../decisions."""
    bodies = sorted(
        (root / exam).glob("decisions_*.json"),
        key=lambda path: int(path.stem.rsplit("_", 1)[1]),
    )
    served = iter(bodies)

    def handle(request: httpx.Request) -> httpx.Response:
        if request.method != "POST" or not request.url.path.endswith("/decisions"):
            raise MissingRecording(f"{exam}: unexpected request {request.method} {request.url}")
        path = next(served, None)
        if path is None:
            raise MissingRecording(f"{exam}: more Decisions requests than {len(bodies)} recordings")
        return httpx.Response(200, json=json.loads(path.read_text()))

    return httpx.AsyncClient(transport=httpx.MockTransport(handle))


class GrantingLeases:
    """Grant every reservation."""

    async def reserve(
        self,
        *,
        now: datetime,
        requested_tokens: int,
        job_id: UUID,
        item_id: str,
        provider_profile_id: str,
    ) -> AnswerKeyTokenLease:
        return AnswerKeyTokenLease(
            uuid4(), now.date(), requested_tokens, AnswerKeyTokenLeaseState.RESERVED
        )

    async def reconcile(self, *, lease_id: UUID, actual_tokens: int, now: datetime) -> None:
        return None

    async def day_usage(self, *, utc_day: date) -> AnswerKeyTokenLeaseDayUsage:
        raise NotImplementedError("The DOCX converter never reads daily usage.")


class NoTransaction:
    """A transaction that does nothing, for lease bookkeeping."""

    async def __aenter__(self) -> NoTransaction:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None


class NoSleep:
    async def sleep(self, seconds: float) -> None:
        return None


@dataclass
class RecordingProgress:
    """Count every port call; delegate to ``inner`` when given (e.g. the production port)."""

    inner: DocxConversionProgressProtocol | None = None
    calls: list[str] = field(default_factory=list)
    outlines: list[ConversionOutline] = field(default_factory=list)
    updates: list[ConversionUpdate] = field(default_factory=list)
    finals: list[ConversionUpdate] = field(default_factory=list)

    async def outline(self, *, worker_id: str, job_id: UUID, outline: ConversionOutline) -> None:
        self.calls.append("outline")
        self.outlines.append(outline)
        if self.inner is not None:
            await self.inner.outline(worker_id=worker_id, job_id=job_id, outline=outline)

    async def batch_ready(self, *, worker_id: str, job_id: UUID, update: ConversionUpdate) -> None:
        self.calls.append("batch_ready")
        self.updates.append(update)
        if self.inner is not None:
            await self.inner.batch_ready(worker_id=worker_id, job_id=job_id, update=update)

    async def publish_final(
        self,
        *,
        worker_id: str,
        job_id: UUID,
        lineage_id: UUID,
        actor: User,
        file_id: UUID,
        update: ConversionUpdate,
        notes: tuple[str, ...],
    ) -> None:
        self.calls.append("publish_final")
        self.finals.append(update)
        if self.inner is not None:
            await self.inner.publish_final(
                worker_id=worker_id,
                job_id=job_id,
                lineage_id=lineage_id,
                actor=actor,
                file_id=file_id,
                update=update,
                notes=notes,
            )

    async def abandon(self, *, worker_id: str, job_id: UUID, reason: str) -> None:
        self.calls.append("abandon")
        if self.inner is not None:
            await self.inner.abandon(worker_id=worker_id, job_id=job_id, reason=reason)


@dataclass(frozen=True)
class Replay:
    """The production pipeline of one exam and the doubles it was built with."""

    exam: str
    pipeline: DocxConversionPipeline
    provider: ReplayProvider
    progress: RecordingProgress
    corpus: Path | None = None

    def job(self) -> DocxConversionJob:
        content = corpus_docx(self.exam, self.corpus)
        return DocxConversionJob(
            job_id=uuid4(),
            worker_id=WORKER,
            document_id=uuid4(),
            filename=f"{self.exam}.docx",
            source_sha256=hashlib.sha256(content).hexdigest(),
            source_docx=content,
            chunks=PythonDocxExamChunker().chunk(content=content),
            course_key=None,
        )


def build_replay(
    exam: str,
    *,
    progress: RecordingProgress | None = None,
    failures: Mapping[str, Exception] | None = None,
    leases: AnswerKeyTokenLeaseRepositoryProtocol | None = None,
    enabled: bool = True,
    root: Path = RECORDINGS,
    corpus: Path | None = None,
    families_per_batch: int = RECORDED_FAMILIES_PER_BATCH,
    provider: ReplayProvider | None = None,
) -> Replay:
    """Build the production pipeline over ``exam``'s recordings at their batch size."""
    provider = provider or ReplayProvider(exam, failures, root)
    progress = progress or RecordingProgress()
    pipeline = build_docx_conversion_pipeline(
        client=decisions_client(exam, root),
        provider=provider,
        sleeper=NoSleep(),
        leases=leases or GrantingLeases(),
        uow=SerializedUnitOfWork(NoTransaction()),
        clock=FixedClock(_NOW),
        settings=Settings.model_construct(
            LLM_ANSWER_KEY_ENABLED=enabled,
            OPENAI_LLM_ANSWER_KEY_API_KEY="replay-key",
            LLM_DOCX_BATCH_FAMILIES=families_per_batch,
        ),
        progress=progress,
    )
    return Replay(exam=exam, pipeline=pipeline, provider=provider, progress=progress, corpus=corpus)
