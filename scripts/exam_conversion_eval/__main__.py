"""Convert every corpus DOCX like the DOCX import job and report each item that differs from gold.

Recorded mode replays the recorded live provider responses; live mode calls the
configured provider and stores each round's response next to the report.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from pydantic import JsonValue
from pydantic_core import to_jsonable_python

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build import DocxAIConverter
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    AnswerKeyTokenLease,
    AnswerKeyTokenLeaseDayUsage,
    AnswerKeyTokenLeaseState,
)
from skriptoteket.infrastructure.clock import UTCClock
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.infrastructure.llm.openai.answer_key_structured_provider import (
    OpenAIAnswerKeyStructuredProvider,
)
from skriptoteket.infrastructure.llm.openai.docx_conversion_profiles import (
    build_luna_docx_conversion_profile,
)
from skriptoteket.protocols.exam_answer_key import AnswerKeyStructuredProviderProtocol

from .compare import ExamComparison, compare_exam, compare_native_exam
from .gold import GoldExam

_CORPUS = Path("tests/fixtures/exam_conversion/docx_corpus")
_RECORDINGS = Path("tests/fixtures/exam_conversion")
# Each exam's recorded provider responses, one file per round, from a prompt v7 live run.
_RECORDED_RUN = _RECORDINGS / "docx_build_v7"


def _recorded_rounds(exam: str) -> list[Path]:
    return sorted((_RECORDED_RUN / exam).glob("round*.json"))


@dataclass(frozen=True)
class _ExamReport:
    exam: str
    gold_title: str
    title: str | None
    gold_items: int
    converted_items: int
    input_tokens: int | None
    output_tokens: int | None
    events: tuple[dict[str, JsonValue], ...]
    crash: str | None
    comparison: ExamComparison


class RecordedRoundMissing(Exception):
    """The converter asked for a round the recording does not contain."""


class _ReplayedProvider:
    """Serve one exam's recorded responses in round order."""

    def __init__(self, rounds: Sequence[dict[str, JsonValue]]) -> None:
        self._rounds = iter(rounds)

    async def complete_structured(
        self, *, request: StructuredLLMRequest, profile: StructuredLLMProviderProfile
    ) -> StructuredLLMResponse:
        content = next(self._rounds, None)
        if content is None:
            raise RecordedRoundMissing(request.item_id)
        return StructuredLLMResponse(content, "completed")


class _RecordingProvider:
    """Keep each live round's validated response in the recorded fixture format."""

    def __init__(self, provider: AnswerKeyStructuredProviderProtocol) -> None:
        self._provider = provider
        self.rounds: list[dict[str, JsonValue]] = []

    async def complete_structured(
        self, *, request: StructuredLLMRequest, profile: StructuredLLMProviderProfile
    ) -> StructuredLLMResponse:
        response = await self._provider.complete_structured(request=request, profile=profile)
        self.rounds.append(response.content)
        return response


class _UnmeteredLeases:
    """Grant every reservation; the eval reports provider usage instead of a daily budget."""

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


class _NoTransaction:
    """The eval persists nothing, so lease bookkeeping needs no transaction."""

    async def __aenter__(self) -> _NoTransaction:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


async def _evaluate(
    docx: Path, provider: AnswerKeyStructuredProviderProtocol, settings: Settings
) -> _ExamReport:
    """Run the DOCX job's chunk-and-convert step and compare the document with its gold.

    A conversion crash fails the import job, so it is reported as an exam that converted no items.
    """
    gold = GoldExam.model_validate_json((_CORPUS / "gold" / f"{docx.stem}.json").read_text())
    content = docx.read_bytes()
    source_sha256 = hashlib.sha256(content).hexdigest()
    if gold.source_sha256 != source_sha256:
        raise SystemExit(f"{docx.name}: gold source_sha256 does not match the DOCX")
    converter = DocxAIConverter(
        provider=provider,
        profile=build_luna_docx_conversion_profile(settings),
        leases=_UnmeteredLeases(),
        uow=_NoTransaction(),
        clock=UTCClock(),
        enabled=True,
    )
    chunks = PythonDocxExamChunker().chunk(content=content)
    try:
        result = await converter.convert(
            job_id=uuid4(),
            document_id=uuid4(),
            filename=docx.name,
            source_sha256=source_sha256,
            chunks=chunks,
        )
    except Exception as error:
        return _ExamReport(
            exam=docx.stem,
            gold_title=gold.title,
            title=None,
            gold_items=len(gold.questions),
            converted_items=0,
            input_tokens=None,
            output_tokens=None,
            events=(),
            crash=f"{type(error).__name__}: {error}",
            comparison=compare_exam(gold, ()),
        )
    return _ExamReport(
        exam=docx.stem,
        gold_title=gold.title,
        title=result.document.title,
        gold_items=len(gold.questions),
        converted_items=len(result.document.items),
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        events=tuple(event.as_json() for event in result.events),
        crash=None,
        comparison=compare_native_exam(gold, result.document, [chunk.text for chunk in chunks]),
    )


async def _recorded(settings: Settings) -> list[_ExamReport]:
    exams = sorted(_CORPUS.glob("*.docx"))
    providers = [
        _ReplayedProvider([json.loads(path.read_text()) for path in _recorded_rounds(docx.stem)])
        for docx in exams
    ]
    return list(
        await asyncio.gather(
            *(_evaluate(docx, provider, settings) for docx, provider in zip(exams, providers))
        )
    )


async def _live(settings: Settings, evidence_dir: Path) -> list[_ExamReport]:
    exams = sorted(_CORPUS.glob("*.docx"))
    async with httpx.AsyncClient() as client:
        live = OpenAIAnswerKeyStructuredProvider(
            client=client,
            base_url=settings.LLM_ANSWER_KEY_BASE_URL,
            api_key=settings.OPENAI_LLM_ANSWER_KEY_API_KEY,
            timeout_seconds=float(settings.LLM_DOCX_CONVERSION_TIMEOUT_SECONDS),
        )
        recorders = [_RecordingProvider(live) for _ in exams]
        reports = await asyncio.gather(
            *(_evaluate(docx, recorder, settings) for docx, recorder in zip(exams, recorders))
        )
    for docx, recorder in zip(exams, recorders):
        for round_number, content in enumerate(recorder.rounds, start=1):
            path = evidence_dir / "recordings" / docx.stem / f"round{round_number}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n")
    return list(reports)


def _print_report(reports: Sequence[_ExamReport]) -> None:
    for report in reports:
        items = report.comparison.items
        failed = [item for item in items if not item.passed]
        print(
            f"{report.exam}: {len(items) - len(failed)}/{len(items)} items match;"
            f" gold {report.gold_items}, converted {report.converted_items};"
            f" tokens in {report.input_tokens} out {report.output_tokens};"
            f" events {len(report.events)}"
        )
        failures = report.comparison.failures_by_principle()
        print(
            "  failing items per principle: " + ", ".join(f"{p} {n}" for p, n in failures.items())
        )
        if not report.comparison.title.passed:
            print(f"  title fails: gold={report.gold_title!r} actual={report.title!r}")
        if report.crash:
            print(f"  conversion crashed: {report.crash[:300]}")
        for item in failed:
            for mismatch in item.mismatches:
                detail = f"expected={mismatch.expected!r} actual={mismatch.actual!r}"
                print(
                    f"  [{item.index}] {item.source_label} {mismatch.principle} {mismatch.reason}:"
                    f" {detail[:400]}"
                )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("recorded", "live"), required=True)
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        required=True,
        help="Retained-root evidence directory that receives report.json and live recordings.",
    )
    args = parser.parse_args(argv)
    settings = Settings()
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    reports = asyncio.run(
        _recorded(settings) if args.mode == "recorded" else _live(settings, args.evidence_dir)
    )
    _print_report(reports)
    failed = [report.exam for report in reports if not report.comparison.passed]
    (args.evidence_dir / "report.json").write_text(
        json.dumps(
            {"mode": args.mode, "failed_exams": failed, "exams": to_jsonable_python(reports)},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    print(f"{len(reports) - len(failed)}/{len(reports)} exams match gold")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
