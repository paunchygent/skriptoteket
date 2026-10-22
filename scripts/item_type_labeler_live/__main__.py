"""Live run of the production item-type labeler over the DOCX corpus (TASK-SKRIPT-39-05-04).

Questions come from source chunks plus a saved provider grouping (never gold).
Every HTTP exchange of the production adapter is recorded with an allowlist of
response headers; the Authorization header is never recorded. The door's
internal key is read from Settings and never written or printed.

Usage:
    python -m scripts.item_type_labeler_live --groupings <dir> --out <dir> --user-id <uuid>
        [--corpus <dir>] [--split-exams <stem> ...] [--allow-paid-overage]

Every escalation is re-asked alone using its own tight source context.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
import uuid
from pathlib import Path
from uuid import UUID

import httpx
from pydantic import JsonValue, TypeAdapter

from scripts.item_type_labeler_live.records import (
    CorpusSummary,
    ExchangeRecord,
    GroupingRecord,
    ItemRecord,
    LabelingRecord,
    RequestRecord,
    ResultRecord,
    RunRecord,
    RunSummary,
    SavedGrouping,
)
from skriptoteket.config import Settings
from skriptoteket.domain.llm_door import (
    AiDailyLimit,
    AiDailyLimitReached,
    AiDoorCaller,
    tooling_caller,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_labeler_markdown import (  # noqa: E501
    PythonDocxLabelerMarkdown,
)
from skriptoteket.infrastructure.llm.door.client import HuleEduLlmDoorClient
from skriptoteket.infrastructure.llm.openai.decisions_item_labeler import (
    OpenAIDecisionsItemTypeLabeler,
    build_decisions_payload,
    split_items,
)
from skriptoteket.infrastructure.time.asyncio_sleeper import AsyncioSleeper
from skriptoteket.protocols.item_type_labeler import (
    ItemTypeLabelerError,
    ItemTypeLabeling,
    ItemTypeLabelResult,
    LabelingItem,
    LabelingRequest,
)

CORPUS = Path("tests/fixtures/exam_conversion/docx_corpus")
KEPT_HEADERS = (
    "x-request-id",
    "openai-processing-ms",
    "openai-model",
    "retry-after",
    "x-ratelimit-limit-requests",
    "x-ratelimit-limit-tokens",
    "x-ratelimit-remaining-requests",
    "x-ratelimit-remaining-tokens",
)
DECISIONS_INPUT_USD_PER_MILLION = 0.10  # gpt-6-luna Decisions input price, read 2026-10-11.
GROUPING_RECORD = TypeAdapter(GroupingRecord)
REQUEST_RECORD = TypeAdapter(RequestRecord)


class RecordingTransport(httpx.AsyncBaseTransport):
    """Forward to the real transport and keep each exchange without credentials."""

    def __init__(self, run_started: float) -> None:
        self._inner = httpx.AsyncHTTPTransport()
        self._run_started = run_started
        self.exchanges: list[ExchangeRecord] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        started = time.perf_counter()
        response = await self._inner.handle_async_request(request)
        content = await response.aread()
        try:
            body: JsonValue = json.loads(content)
        except ValueError:
            body = content.decode("utf-8", errors="replace")
        sent = REQUEST_RECORD.validate_json(request.content, strict=True)
        finished = time.perf_counter()
        self.exchanges.append(
            {
                "request": sent,
                "status_code": response.status_code,
                "duration_seconds": round(finished - started, 3),
                "start_seconds": started - self._run_started,
                "finished_seconds": finished - self._run_started,
                "headers": {k: response.headers[k] for k in KEPT_HEADERS if k in response.headers},
                "body": body,
            }
        )
        # aread() already decoded the body, so the rebuilt response drops the encoding headers.
        headers = {
            k: v
            for k, v in response.headers.items()
            if k.lower() not in {"content-encoding", "content-length", "transfer-encoding"}
        }
        return httpx.Response(
            response.status_code, headers=headers, content=content, request=request
        )

    async def aclose(self) -> None:
        await self._inner.aclose()


def corpus_items(
    corpus: Path,
    stem: str,
    grouping: SavedGrouping,
) -> list[LabelingItem]:
    """Each question's own chunks, governing instructions and section heading as source markdown."""

    chunks = (
        PythonDocxLabelerMarkdown().source(content=(corpus / f"{stem}.docx").read_bytes()).chunks
    )
    positions = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    all_keys = frozenset(a for q in grouping["questions"] for a in q["key_anchors"])
    all_questions = frozenset(a for q in grouping["questions"] for a in q["anchors"])
    titles = frozenset(grouping["title"])
    items = []
    for question in grouping["questions"]:
        qid = question["id"]
        governing = sorted(
            {
                c["anchor"]
                for c in grouping["contexts"]
                if qid in c["governs"]
                and c["scope"] != "exam_metadata"
                and c["anchor"] not in titles | all_keys
            },
            key=positions.__getitem__,
        )
        own = set(question["anchors"]) | set(question["key_anchors"])
        start = min(positions[anchor] for anchor in question["anchors"])
        heading_anchor = next(
            (
                chunk.anchor
                for chunk in reversed(chunks[:start])
                if chunk.kind == "heading" and chunk.anchor not in titles | all_questions | all_keys
            ),
            None,
        )
        included = own | set(governing)
        if heading_anchor is not None:
            included.add(heading_anchor)
        selected: dict[str, str] = {}
        for chunk in chunks:
            if chunk.anchor in included:
                selected.setdefault(chunk.anchor, chunk.marked_text)
        items.append(
            LabelingItem(
                item_id=f"{stem}/{qid}",
                source_text="\n".join(selected.values()),
            )
        )
    return items


def item_json(item: LabelingItem) -> ItemRecord:
    return {
        "item_id": item.item_id,
        "source_text": item.source_text,
    }


def result_json(result: ItemTypeLabelResult) -> ResultRecord:
    return {
        "item_id": result.item_id,
        "label": result.label.value,
        "probability": result.probability,
        "threshold": result.threshold,
        "route": result.route.value,
        "refused": result.refused,
        "probabilities": {k.value: v for k, v in result.probabilities.items()},
        "first_pass": None if result.first_pass is None else result_json(result.first_pass),
    }


def labeling_json(labeling: ItemTypeLabeling) -> LabelingRecord:
    tokens = labeling.usage.input_tokens
    return {
        "usage": {
            "input_tokens": tokens,
            "requests": labeling.usage.requests,
            "attempts": labeling.usage.attempts,
            "cost_usd": None if tokens is None else tokens * DECISIONS_INPUT_USD_PER_MILLION / 1e6,
        },
        "results": [result_json(r) for r in labeling.results],
    }


async def run_one(
    name: str,
    items: list[LabelingItem],
    out: Path,
    settings: Settings,
    caller: AiDoorCaller,
    *,
    corpus_started: float,
) -> RunSummary:
    run_started = time.perf_counter()
    transport = RecordingTransport(run_started)
    record: RunRecord = {
        "name": name,
        "items": [item_json(item) for item in items],
        "exchanges": transport.exchanges,
        "wall_seconds": 0.0,
        "start_offset": run_started - corpus_started,
        "first_pass_wall_seconds": 0.0,
    }
    async with httpx.AsyncClient(transport=transport) as client:
        # RecordingTransport wraps the httpx transport under the door client, so the
        # recorded relayed OpenAI bodies are the same shapes the job sees.
        door = HuleEduLlmDoorClient(
            client=client,
            base_url=settings.HULEEDU_LLM_PROVIDER_BASE_URL,
            internal_api_key=settings.HULEEDU_INTERNAL_API_KEY,
            job_overage_cap_usd_micros=round(settings.LLM_JOB_OVERAGE_CAP_USD * 1_000_000),
        )
        labeler = OpenAIDecisionsItemTypeLabeler(
            door=door,
            timeout_seconds=float(settings.LLM_ITEM_LABELER_TIMEOUT_SECONDS),
            sleeper=AsyncioSleeper(),
        )
        request = LabelingRequest(job_id=uuid.uuid4(), items=tuple(items), caller=caller)
        started = time.perf_counter()
        try:
            outcome = labeling_json(await labeler.label(request=request))
            record["usage"] = outcome["usage"]
            record["results"] = outcome["results"]
        except ItemTypeLabelerError as error:
            record["error"] = {"code": error.code, "status_code": error.status_code}
        record["wall_seconds"] = round(time.perf_counter() - started, 3)
    record["first_pass_wall_seconds"] = max(
        (
            min(
                (
                    exchange["finished_seconds"]
                    for exchange in transport.exchanges
                    if exchange["request"] == REQUEST_RECORD.validate_python(payload)
                    and exchange["status_code"] == 200
                ),
                default=0.0,
            )
            for payload in (build_decisions_payload(chunk) for chunk in split_items(items))
        ),
        default=0.0,
    )
    (out / f"{name}.json").write_text(json.dumps(record, ensure_ascii=False, indent=1))
    summary: RunSummary = {
        "name": name,
        "items": len(items),
        "wall_seconds": record["wall_seconds"],
        "start_offset": record["start_offset"],
        "first_pass_wall_seconds": record["first_pass_wall_seconds"],
    }
    if "usage" in record:
        summary["usage"] = record["usage"]
    if "error" in record:
        summary["error"] = record["error"]
    return summary


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


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--groupings", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--split-exams", nargs="*", default=[])
    parser.add_argument("--corpus", type=Path, default=CORPUS)
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
    args = parser.parse_args()
    settings = Settings()
    caller = tooling_caller(user_id=args.user_id, paid_overage_approved=args.allow_paid_overage)
    args.out.mkdir(parents=True, exist_ok=True)
    stems = sorted(path.stem for path in args.corpus.glob("*.docx"))
    items = {
        stem: corpus_items(
            args.corpus,
            stem,
            GROUPING_RECORD.validate_json(
                (args.groupings / stem / "grouping_a.json").read_text(), strict=True
            )["output"],
        )
        for stem in stems
    }
    started = time.perf_counter()
    try:
        summaries = await asyncio.gather(
            *(
                run_one(stem, items[stem], args.out, settings, caller, corpus_started=started)
                for stem in stems
            )
        )
    except AiDailyLimitReached as error:
        return _limit_exit(error)
    corpus_wall = round(time.perf_counter() - started, 3)
    first_pass_wall = max(
        (run["start_offset"] + run["first_pass_wall_seconds"] for run in summaries),
        default=0.0,
    )
    if args.split_exams:
        combined = [item for stem in args.split_exams for item in items[stem]]
        try:
            summaries.append(
                await run_one(
                    "split_" + "_".join(args.split_exams[:1]),
                    combined,
                    args.out,
                    settings,
                    caller,
                    corpus_started=started,
                )
            )
        except AiDailyLimitReached as error:
            return _limit_exit(error)
    summary: CorpusSummary = {
        "corpus_wall_seconds": corpus_wall,
        "first_pass_wall_seconds": first_pass_wall,
        "runs": summaries,
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
