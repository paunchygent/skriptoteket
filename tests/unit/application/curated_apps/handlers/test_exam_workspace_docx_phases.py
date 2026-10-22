"""The conversion reports each phase once, before the work the phase names (D1, D6)."""

from __future__ import annotations

import asyncio
from uuid import UUID

import pytest

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.protocols.docx_conversion_progress import ConversionPhase
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    RecordingProgress,
    build_replay,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_docx_jobs import (
    _QUIZ_EXAM,
    claim,
    environment,
)

pytestmark = pytest.mark.asyncio


def _first(trace: list[str], entry: str) -> int:
    return trace.index(entry)


async def test_a_conversion_reports_finding_sorting_and_converting_once_each_in_order():
    replay = build_replay(_QUIZ_EXAM)
    await replay.pipeline.convert(job=replay.job())
    progress = replay.progress
    trace = progress.trace

    assert progress.phases == [
        ConversionPhase.FINDING,
        ConversionPhase.SORTING,
        ConversionPhase.CONVERTING,
    ]
    assert progress.calls.count("batch_ready") > 1, "the proof needs several batches"
    # Each phase is reported before the work it names starts.
    assert _first(trace, "phase:finding") < _first(trace, "provider:exam_source_manifest")
    assert _first(trace, "phase:sorting") > _first(trace, "outline")
    assert _first(trace, "phase:sorting") < _first(trace, "door:decisions")
    assert _first(trace, "phase:converting") > _first(trace, "phase:sorting")
    assert _first(trace, "phase:converting") < _first(trace, "provider:docx_exam_build")
    assert _first(trace, "phase:converting") < _first(trace, "batch_ready")


class _SuspendedConvertingProgress(RecordingProgress):
    """Holds the converting phase write open, as unfinished database IO would."""

    def __init__(self) -> None:
        super().__init__()
        self.converting_entered = asyncio.Event()
        self.release_converting = asyncio.Event()

    async def phase(self, *, worker_id: str, job_id: UUID, phase: ConversionPhase) -> None:
        await super().phase(worker_id=worker_id, job_id=job_id, phase=phase)
        if phase is ConversionPhase.CONVERTING:
            self.converting_entered.set()
            await self.release_converting.wait()


async def test_no_converter_calls_the_provider_before_the_converting_write_completes():
    progress = _SuspendedConvertingProgress()
    replay = build_replay(_QUIZ_EXAM, progress=progress)
    conversion = asyncio.create_task(replay.pipeline.convert(job=replay.job()))

    await asyncio.wait_for(progress.converting_entered.wait(), timeout=5)
    # Let every dispatched converter run as far as it can while the write is open.
    for _ in range(50):
        await asyncio.sleep(0)
    assert "phase:converting" in progress.trace
    assert "provider:docx_exam_build" not in progress.trace
    assert "batch_ready" not in progress.trace

    progress.release_converting.set()
    await asyncio.wait_for(conversion, timeout=10)

    trace = progress.trace
    assert _first(trace, "phase:converting") < _first(trace, "provider:docx_exam_build")
    assert _first(trace, "phase:converting") < _first(trace, "batch_ready")
    assert progress.calls.count("batch_ready") > 1, "every batch still converts and delivers"


@pytest.mark.parametrize("enabled", [False])
async def test_a_disabled_conversion_reports_no_ai_phase(enabled: bool):
    replay = build_replay(_QUIZ_EXAM, enabled=enabled)
    await replay.pipeline.convert(job=replay.job())
    assert replay.progress.phases == []
    assert replay.provider.requests == []


async def test_a_reclaimed_conversion_reports_no_ai_phase():
    replay = build_replay(_QUIZ_EXAM)
    await replay.pipeline.convert(job=replay.job(), fallback_reason="Arbetaren avbröts.")
    assert replay.progress.phases == []
    assert replay.provider.requests == []


class _TracingChunker:
    """The production chunker, noting in the shared trace when it reads the file."""

    def __init__(self, trace: list[str]) -> None:
        self._trace = trace
        self._chunker = PythonDocxExamChunker()

    def chunk(self, *, content: bytes) -> tuple[DocxChunk, ...]:
        self._trace.append("chunk")
        return self._chunker.chunk(content=content)


@pytest.mark.parametrize("fallback_reason", [None, "Arbetaren avbröts."])
async def test_the_job_reports_reading_before_it_chunks_the_file(fallback_reason: str | None):
    env = environment()
    running = await claim(env)
    trace = env.replay.progress.trace
    env.processor._chunker = _TracingChunker(trace)  # noqa: SLF001 - trace the chunker

    finished = await env.processor.handle(job=running, fallback_reason=fallback_reason)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert trace[:2] == ["phase:reading", "chunk"], "reading is reported before the file is read"
    assert trace.count("phase:reading") == 1
    stored = env.jobs.jobs[running.id]
    if fallback_reason is None:
        assert stored.conversion_phase is ConversionPhase.CONVERTING
        assert stored.conversion_phase_started_at is not None
    else:
        # A lease-reclaimed run keeps the file source-only: reading is the only phase it reports.
        assert env.replay.progress.phases == [ConversionPhase.READING]
        assert stored.conversion_phase is ConversionPhase.READING
