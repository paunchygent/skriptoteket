"""Convert every corpus DOCX through the DOCX import job's conversion pipeline and compare with gold.

The eval composes the converter with ``skriptoteket.di.docx_conversion``, as the job does, and
calls the configured live providers. Each Responses reply is stored next to the report under
its request id, and each exam reports the elapsed seconds of every pipeline stage. With
``--grouping-only`` the eval runs only the grouping pass and stores its replies, so a grouping
recording can be refreshed without a new build recording.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import traceback
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from pydantic import JsonValue
from pydantic_core import to_jsonable_python

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_rounds import (
    DocxBuildRoundExchange,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_grouping import (
    ResponsesExamGrouper,
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
)
from skriptoteket.domain.curated_apps.exam_workspace.import_file_format import (
    import_origin_kind,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.llm_door import (
    AiDailyLimit,
    AiDailyLimitReached,
    AiDoorCaller,
    tooling_caller,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.infrastructure.llm.door.client import DoorBounds, HuleEduLlmDoorClient
from skriptoteket.infrastructure.llm.openai.answer_key_structured_provider import (
    OpenAIAnswerKeyStructuredProvider,
)
from skriptoteket.infrastructure.llm.openai.docx_conversion_profiles import (
    build_luna_docx_grouping_profile,
)
from skriptoteket.infrastructure.time.asyncio_sleeper import AsyncioSleeper
from skriptoteket.protocols.docx_conversion_progress import (
    ConversionOutline,
    ConversionPhase,
    ConversionUpdate,
)
from skriptoteket.protocols.exam_answer_key import (
    AnswerKeyStructuredProviderProtocol,
    StructuredLLMTextObserver,
)

from .compare import ExamComparison, compare_exam, compare_native_exam
from .gold import GoldExam
from .report import print_comparison

_CORPUS = Path("tests/fixtures/exam_conversion/docx_corpus")
_WORKER = "exam-conversion-eval"


@dataclass(frozen=True)
class _ExamReport:
    exam: str
    gold_title: str
    title: str | None
    gold_items: int
    converted_items: int
    input_tokens: int | None
    output_tokens: int | None
    timings: dict[str, tuple[float, float]]
    batches_ready: int
    events: tuple[dict[str, JsonValue], ...]
    crash: tuple[str, ...]
    comparison: ExamComparison


def _crash_lines(error: BaseException) -> tuple[str, ...]:
    """Describe every leaf exception of a crash with its message and raising frame."""
    if isinstance(error, BaseExceptionGroup):
        return tuple(line for inner in error.exceptions for line in _crash_lines(inner))
    line = f"{type(error).__name__}: {error}"
    frames = traceback.extract_tb(error.__traceback__)
    if frames:
        frame = frames[-1]
        line += f" (at {frame.filename}:{frame.lineno} in {frame.name})"
    return (line,)


class _RecordingProvider:
    """Keep each live Responses reply under its request id and each Decisions reply in order."""

    def __init__(self, provider: AnswerKeyStructuredProviderProtocol) -> None:
        self._provider = provider
        self.replies: dict[str, dict[str, JsonValue]] = {}
        self.decisions: list[JsonValue] = []

    async def on_response(self, response: httpx.Response) -> None:
        if response.request.url.path.endswith("/decisions") and response.status_code == 200:
            await response.aread()
            self.decisions.append(response.json())

    async def complete_structured(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
        caller: AiDoorCaller,
        on_text: StructuredLLMTextObserver | None = None,
    ) -> StructuredLLMResponse:
        response = await self._provider.complete_structured(
            request=request, profile=profile, caller=caller, on_text=on_text
        )
        self.replies[request.item_id] = response.content
        return response


class _CountedProgress:
    """Count the provisional documents the job would save; the eval persists nothing."""

    def __init__(self) -> None:
        self.batches_ready = 0

    async def phase(self, *, worker_id: str, job_id: UUID, phase: ConversionPhase) -> None:
        return None

    async def received(
        self, *, worker_id: str, job_id: UUID, question_ids: tuple[str, ...]
    ) -> None:
        return None

    async def outline(self, *, worker_id: str, job_id: UUID, outline: ConversionOutline) -> None:
        return None

    async def batch_ready(
        self,
        *,
        worker_id: str,
        job_id: UUID,
        update: ConversionUpdate,
        notes: tuple[str, ...],
    ) -> None:
        self.batches_ready += 1

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
        raise NotImplementedError("The pipeline never publishes; the job does.")

    async def abandon(self, *, worker_id: str, job_id: UUID, reason: str) -> None:
        return None


class _NoTransaction:
    """The eval persists nothing, so lease bookkeeping needs no transaction."""

    async def __aenter__(self) -> _NoTransaction:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


def _limit_exit(error: AiDailyLimitReached) -> int:
    """Stop the run on a door limit; a pool refusal needs the user's overage approval."""

    if error.limit is AiDailyLimit.POOL:
        print(
            "The OpenAI pool for today is exhausted. Paying overage needs the user's approval; "
            "rerun with --allow-paid-overage only after the user says yes."
        )
        return 2
    print(error.limit.value)
    return 1


async def _evaluate(
    docx: Path,
    door: HuleEduLlmDoorClient,
    settings: Settings,
    recorder: _RecordingProvider,
    caller: AiDoorCaller,
) -> _ExamReport:
    """Run the DOCX job's chunk-and-convert step and compare the document with its gold.

    A conversion crash fails the import job, so it is reported as an exam that converted no items.
    """
    gold = GoldExam.model_validate_json((_CORPUS / "gold" / f"{docx.stem}.json").read_text())
    content = docx.read_bytes()
    source_sha256 = hashlib.sha256(content).hexdigest()
    if gold.source_sha256 != source_sha256:
        raise SystemExit(f"{docx.name}: gold source_sha256 does not match the DOCX")
    progress = _CountedProgress()
    pipeline = build_docx_conversion_pipeline(
        door=door,
        provider=recorder,
        sleeper=AsyncioSleeper(),
        uow=SerializedUnitOfWork(_NoTransaction()),
        settings=settings,
        progress=progress,
    )
    source = PythonDocxExamChunker().chunk(content=content)
    try:
        outcome = await pipeline.convert(
            job=DocxConversionJob(
                job_id=uuid4(),
                worker_id=_WORKER,
                document_id=uuid4(),
                filename=docx.name,
                source_sha256=source_sha256,
                source_docx=content,
                chunks=source.chunks,
                source_notes=source.notes,
                course_key=None,
                caller=caller,
                origin_kind=import_origin_kind(content),
            )
        )
    except AiDailyLimitReached:
        raise
    except Exception as error:
        return _ExamReport(
            exam=docx.stem,
            gold_title=gold.title,
            title=None,
            gold_items=len(gold.questions),
            converted_items=0,
            input_tokens=None,
            output_tokens=None,
            timings={},
            batches_ready=progress.batches_ready,
            events=(),
            crash=_crash_lines(error),
            comparison=compare_exam(gold, ()),
        )
    if outcome.ai_limit is not None:
        raise AiDailyLimitReached(limit=outcome.ai_limit)
    result = outcome.result
    return _ExamReport(
        exam=docx.stem,
        gold_title=gold.title,
        title=result.document.title,
        gold_items=len(gold.questions),
        converted_items=len(result.document.items),
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        timings={
            t.stage: (round(t.started_seconds, 1), round(t.finished_seconds, 1))
            for t in result.timings
        },
        batches_ready=progress.batches_ready,
        events=tuple(event.as_json() for event in result.events),
        crash=(),
        comparison=compare_native_exam(
            gold, result.document, [chunk.text for chunk in source.chunks]
        ),
    )


def _live_provider(
    client: httpx.AsyncClient, settings: Settings
) -> tuple[HuleEduLlmDoorClient, _RecordingProvider]:
    door = HuleEduLlmDoorClient(
        client=client,
        base_url=settings.HULEEDU_LLM_PROVIDER_BASE_URL,
        internal_api_key=settings.HULEEDU_INTERNAL_API_KEY,
        job_overage_cap_usd_micros=round(settings.LLM_JOB_OVERAGE_CAP_USD * 1_000_000),
        sleeper=AsyncioSleeper(),
        bounds=DoorBounds.from_settings(settings),
    )
    recorder = _RecordingProvider(
        OpenAIAnswerKeyStructuredProvider(
            door=door,
            timeout_seconds=float(settings.LLM_DOCX_CONVERSION_TIMEOUT_SECONDS),
        )
    )
    client.event_hooks["response"] = [recorder.on_response]
    return door, recorder


async def _live_grouping(
    docx: Path, settings: Settings, caller: AiDoorCaller, evidence_dir: Path
) -> str:
    """Run only the job's grouping pass and store its replies; return a one-line summary."""
    async with httpx.AsyncClient() as client:
        _, recorder = _live_provider(client, settings)
        grouper = ResponsesExamGrouper(
            exchange=DocxBuildRoundExchange(recorder),
            profile=build_luna_docx_grouping_profile(settings),
        )
        source = PythonDocxExamChunker().chunk(content=docx.read_bytes())
        grouping = await grouper.group(job_id=uuid4(), chunks=source.chunks, caller=caller)
    _write_recordings(recorder, evidence_dir / "recordings" / docx.stem)
    manifest = grouping.manifest
    header = ", ".join(f"{h.kind}:{h.anchor}" for h in manifest.header) or "none"
    return (
        f"{docx.stem}: {len(manifest.questions)} questions, {len(recorder.replies)} grouping"
        f" calls, unplaced {list(manifest.unplaced_anchors)}, header {header}"
    )


async def _live_exam(
    docx: Path, settings: Settings, caller: AiDoorCaller, evidence_dir: Path
) -> _ExamReport:
    """One client per exam, so each exam's Decisions replies are recorded with that exam."""
    async with httpx.AsyncClient() as client:
        door, recorder = _live_provider(client, settings)
        report = await _evaluate(docx, door, settings, recorder, caller)
    _write_recordings(recorder, evidence_dir / "recordings" / docx.stem)
    return report


def _write_recordings(recorder: _RecordingProvider, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for request_id, content in recorder.replies.items():
        path = directory / f"{request_id.replace(':', '_')}.json"
        path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n")
    for number, body in enumerate(recorder.decisions, start=1):
        path = directory / f"decisions_{number}.json"
        path.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n")


async def _live(
    settings: Settings, caller: AiDoorCaller, evidence_dir: Path, exams: list[Path]
) -> list[_ExamReport]:
    return list(
        await asyncio.gather(*(_live_exam(docx, settings, caller, evidence_dir) for docx in exams))
    )


async def _live_groupings(
    settings: Settings, caller: AiDoorCaller, evidence_dir: Path, exams: list[Path]
) -> list[str]:
    return list(
        await asyncio.gather(
            *(_live_grouping(docx, settings, caller, evidence_dir) for docx in exams)
        )
    )


def _print_report(reports: Sequence[_ExamReport]) -> None:
    for report in reports:
        items = report.comparison.items
        failed = [item for item in items if not item.passed]
        print(
            f"{report.exam}: {len(items) - len(failed)}/{len(items)} items match;"
            f" gold {report.gold_items}, converted {report.converted_items};"
            f" tokens in {report.input_tokens} out {report.output_tokens};"
            f" events {len(report.events)}; batches ready {report.batches_ready}"
        )
        print(
            "  stage seconds: "
            + ", ".join(f"{stage} {a}-{b}" for stage, (a, b) in report.timings.items())
        )
        print_comparison(report.comparison, crashed=bool(report.crash))
        for line in report.crash:
            print(f"  conversion crashed: {line}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        required=True,
        help="Retained-root evidence directory that receives report.json and the recordings.",
    )
    parser.add_argument(
        "--exam",
        action="append",
        default=[],
        help="Corpus DOCX stem to convert; repeat for several. Every corpus exam by default.",
    )
    parser.add_argument(
        "--grouping-only",
        action="store_true",
        help="Run and record only the grouping pass; no build, no gold comparison.",
    )
    parser.add_argument(
        "--user-id",
        type=UUID,
        required=True,
        help="User the door calls run for; the run is recorded as their exempt agent run.",
    )
    parser.add_argument(
        "--allow-paid-overage",
        action="store_true",
        help="Run as approved paid overage for this one run (C6: only after the user says yes).",
    )
    args = parser.parse_args(argv)
    # The eval runs conversion with the job's composition whatever the local enable flag says.
    settings = Settings().model_copy(update={"LLM_ANSWER_KEY_ENABLED": True})
    caller = tooling_caller(user_id=args.user_id, paid_overage_approved=args.allow_paid_overage)
    exams = sorted(_CORPUS.glob("*.docx"))
    if args.exam:
        exams = [docx for docx in exams if docx.stem in set(args.exam)]
        missing = set(args.exam) - {docx.stem for docx in exams}
        if missing:
            raise SystemExit(f"not in the corpus: {sorted(missing)}")
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    try:
        if args.grouping_only:
            for line in asyncio.run(_live_groupings(settings, caller, args.evidence_dir, exams)):
                print(line)
            return 0
        reports = asyncio.run(_live(settings, caller, args.evidence_dir, exams))
    except AiDailyLimitReached as error:
        return _limit_exit(error)
    _print_report(reports)
    failed = [report.exam for report in reports if not report.comparison.passed]
    (args.evidence_dir / "report.json").write_text(
        json.dumps(
            {"failed_exams": failed, "exams": to_jsonable_python(reports)},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    print(f"{len(reports) - len(failed)}/{len(reports)} exams match gold")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
