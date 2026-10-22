"""Synthetic stream replay checks locked receipt writes before saved batch publication."""

import asyncio
import json
from uuid import UUID

import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_serial_uow import (
    SerializedUnitOfWork,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.llm_door import AiDoorCaller
from skriptoteket.protocols.exam_answer_key import StructuredLLMTextObserver
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    NoTransaction,
    RecordingProgress,
    ReplayProvider,
    build_replay,
)

pytestmark = pytest.mark.asyncio
_EXAM = "chapter_4_poetry_and_lyrics_quiz_med_facit"


class StreamingReplay(ReplayProvider):
    """Replay content as synthetic text and suspend every batch's terminal response."""

    def __init__(self) -> None:
        super().__init__(_EXAM)
        self.started = asyncio.Event()
        self.allow_text = asyncio.Event()
        self.observed = asyncio.Event()
        self.allow_final = asyncio.Event()

    async def complete_structured(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
        caller: AiDoorCaller,
        on_text: StructuredLLMTextObserver | None = None,
    ) -> StructuredLLMResponse:
        response = await super().complete_structured(
            request=request, profile=profile, caller=caller
        )
        if on_text is not None:
            self.started.set()
            await self.allow_text.wait()
            # Keep the envelope unfinished. Receipt must not require terminal JSON parsing.
            text = json.dumps(response.content)[:-1]
            for offset in range(0, len(text), 37):
                await on_text(text[offset : offset + 37])
            self.observed.set()
            await self.allow_final.wait()
        return response


class LockedProgress(RecordingProgress):
    def __init__(self, lock: asyncio.Lock, failure: Exception | None = None) -> None:
        super().__init__()
        self.lock = lock
        self.failure = failure

    async def received(
        self, *, worker_id: str, job_id: UUID, question_ids: tuple[str, ...]
    ) -> None:
        assert self.lock.locked(), "receipt writes must serialize with publication"
        if self.failure is not None:
            raise self.failure
        await super().received(worker_id=worker_id, job_id=job_id, question_ids=question_ids)


async def test_receipt_waits_for_uow_lock_but_not_terminal_reply_or_batch_publication():
    uow = SerializedUnitOfWork(NoTransaction())
    progress = LockedProgress(uow.lock)
    provider = StreamingReplay()
    replay = build_replay(_EXAM, provider=provider, progress=progress, uow=uow)
    conversion = asyncio.create_task(replay.pipeline.convert(job=replay.job()))
    try:
        await asyncio.wait_for(provider.started.wait(), timeout=5)
        async with uow.lock:
            provider.allow_text.set()
            for _ in range(10):
                await asyncio.sleep(0)
            assert progress.receipts == []
        await asyncio.wait_for(provider.observed.wait(), timeout=5)
        assert progress.receipts
        assert progress.updates == [], "received output must not publish a saved revision"
        assert not conversion.done()
        grouped_ids = {q.question_id for q in progress.outlines[0].questions}
        assert set().union(*map(set, progress.receipts)) <= grouped_ids
    finally:
        provider.allow_text.set()
        provider.allow_final.set()
        outcome = await asyncio.wait_for(conversion, timeout=10)
    assert outcome.update.pending == ()
    assert progress.updates
    assert progress.trace.index("received") < progress.trace.index("batch_ready")


async def test_lost_lease_during_receipt_is_not_converted_to_source_review():
    error = DomainError(code=ErrorCode.CONFLICT, message="lease is no longer owned")
    uow = SerializedUnitOfWork(NoTransaction())
    progress = LockedProgress(uow.lock, error)
    provider = StreamingReplay()
    provider.allow_text.set()
    provider.allow_final.set()
    replay = build_replay(_EXAM, provider=provider, progress=progress, uow=uow)
    with pytest.raises(DomainError) as caught:
        await replay.pipeline.convert(job=replay.job())
    assert caught.value is error
    assert progress.updates == []


async def test_storage_io_fault_during_receipt_still_stops_conversion():
    error = OSError("progress store unavailable")
    uow = SerializedUnitOfWork(NoTransaction())
    provider = StreamingReplay()
    provider.allow_text.set()
    provider.allow_final.set()
    replay = build_replay(
        _EXAM, provider=provider, progress=LockedProgress(uow.lock, error), uow=uow
    )
    with pytest.raises(ExceptionGroup) as caught:
        await replay.pipeline.convert(job=replay.job())
    assert error in caught.value.exceptions
    assert replay.progress.updates == []
