"""Live run of the production item-type labeler over the DOCX corpus (TASK-SKRIPT-39-05-04).

Questions come from source chunks plus a saved provider grouping (never gold).
Every HTTP exchange of the production adapter is recorded with an allowlist of
response headers; the Authorization header is never recorded. The API key is
read from ``OPENAI_LLM_ANSWER_KEY_API_KEY`` and never written or printed.

Usage:
    python -m scripts.item_type_labeler_live --groupings <dir> --out <dir>
        [--split-exams <stem> <stem> ...]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
import uuid
from pathlib import Path
from typing import TypedDict

import httpx
from pydantic import JsonValue

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.infrastructure.llm.openai.decisions_item_labeler import (
    OpenAIDecisionsItemTypeLabeler,
)
from skriptoteket.infrastructure.time.asyncio_sleeper import AsyncioSleeper
from skriptoteket.protocols.item_type_labeler import (
    ItemTypeLabelerError,
    ItemTypeLabeling,
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


class GroupedQuestion(TypedDict):
    id: str
    anchors: list[str]
    key_anchors: list[str]


class GroupingContext(TypedDict):
    anchor: str
    governs: list[str]


class Grouping(TypedDict):
    """A saved provider grouping's output: the questions and the contexts that govern them."""

    questions: list[GroupedQuestion]
    contexts: list[GroupingContext]


class RecordingTransport(httpx.AsyncBaseTransport):
    """Forward to the real transport and keep each exchange without credentials."""

    def __init__(self) -> None:
        self._inner = httpx.AsyncHTTPTransport()
        self.exchanges: list[dict[str, JsonValue]] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        started = time.perf_counter()
        response = await self._inner.handle_async_request(request)
        content = await response.aread()
        try:
            body: JsonValue = json.loads(content)
        except ValueError:
            body = content.decode("utf-8", errors="replace")
        sent: JsonValue = json.loads(request.content)
        self.exchanges.append(
            {
                "request": sent,
                "status_code": response.status_code,
                "duration_seconds": round(time.perf_counter() - started, 3),
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


def corpus_items(stem: str, grouping: Grouping) -> list[LabelingItem]:
    """One item per grouped question: its source and key lines, governing context as parent."""

    chunks = PythonDocxExamChunker().chunk(content=(CORPUS / f"{stem}.docx").read_bytes())
    text = {chunk.anchor: chunk.marked_text for chunk in chunks}
    items = []
    for question in grouping["questions"]:
        qid = question["id"]
        governing = [c["anchor"] for c in grouping["contexts"] if qid in c["governs"]]
        source = [f"[{a}] {text[a]}" for a in question["anchors"]]
        source += [f"[{a}] (answer key) {text[a]}" for a in question["key_anchors"]]
        items.append(
            LabelingItem(
                item_id=f"{stem}/{qid}",
                source_text="\n".join(source),
                parent_instruction="\n".join(f"[{a}] {text[a]}" for a in governing) or None,
            )
        )
    return items


def labeling_json(labeling: ItemTypeLabeling) -> dict[str, JsonValue]:
    tokens = labeling.usage.input_tokens
    return {
        "usage": {
            "input_tokens": tokens,
            "requests": labeling.usage.requests,
            "attempts": labeling.usage.attempts,
            "cost_usd": None if tokens is None else tokens * DECISIONS_INPUT_USD_PER_MILLION / 1e6,
        },
        "results": [
            {
                "item_id": r.item_id,
                "label": r.label.value,
                "probability": r.probability,
                "threshold": r.threshold,
                "route": r.route.value,
                "refused": r.refused,
                "probabilities": {k.value: v for k, v in r.probabilities.items()},
            }
            for r in labeling.results
        ],
    }


async def run_one(
    name: str, items: list[LabelingItem], out: Path, api_key: str
) -> dict[str, JsonValue]:
    transport = RecordingTransport()
    async with httpx.AsyncClient(transport=transport) as client:
        labeler = OpenAIDecisionsItemTypeLabeler(
            client=client,
            base_url="https://api.openai.com",
            api_key=api_key,
            timeout_seconds=60.0,
            sleeper=AsyncioSleeper(),
        )
        request = LabelingRequest(job_id=uuid.uuid4(), items=tuple(items))
        started = time.perf_counter()
        try:
            outcome = labeling_json(await labeler.label(request=request))
        except ItemTypeLabelerError as error:
            outcome = {"error": {"code": error.code, "status_code": error.status_code}}
        outcome["wall_seconds"] = round(time.perf_counter() - started, 3)
    record = {
        "name": name,
        "items": [vars(item) for item in items],
        "exchanges": transport.exchanges,
        **outcome,
    }
    (out / f"{name}.json").write_text(json.dumps(record, ensure_ascii=False, indent=1))
    return {
        "name": name,
        "items": len(items),
        **{k: v for k, v in outcome.items() if k != "results"},
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--groupings", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--split-exams", nargs="*", default=[])
    args = parser.parse_args()
    api_key = os.environ["OPENAI_LLM_ANSWER_KEY_API_KEY"]
    args.out.mkdir(parents=True, exist_ok=True)
    stems = sorted(path.stem for path in CORPUS.glob("*.docx"))
    items: dict[str, list[LabelingItem]] = {}
    for stem in stems:
        grouping: Grouping = json.loads((args.groupings / stem / "grouping_a.json").read_text())[
            "output"
        ]
        items[stem] = corpus_items(stem, grouping)
    started = time.perf_counter()
    summaries = await asyncio.gather(
        *(run_one(stem, items[stem], args.out, api_key) for stem in stems)
    )
    corpus_wall = round(time.perf_counter() - started, 3)
    if args.split_exams:
        combined = [item for stem in args.split_exams for item in items[stem]]
        summaries.append(
            await run_one("split_" + "_".join(args.split_exams[:1]), combined, args.out, api_key)
        )
    summary = {"corpus_wall_seconds": corpus_wall, "runs": summaries}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    asyncio.run(main())
