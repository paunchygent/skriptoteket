"""A source part markdown cannot carry reaches the labeler as an image of that part (D14, R-F5).

The production pipeline converts an exam built in Word: one question holds a table with a
merged cell, another a picture in a format no image can be made of. The Decisions first pass
is the real HTTP adapter; only the network is replaced.
"""

import base64
import io
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
import pytest
from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.opc.packuri import PackURI
from docx.opc.part import Part
from docx.oxml.ns import qn
from PIL import Image
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_pipeline import (
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
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.protocols.item_type_labeler import ItemTypeLabel
from tests.fixtures.time_fixtures import FixedClock
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    GrantingLeases,
    NoSleep,
    NoTransaction,
    RecordingProgress,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_TABLE_STEM = "Para ihop varje ord med sin ordklass."
_PICTURE_STEM = "Vad visar bilden?"


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (120, 60), (40, 90, 160)).save(buffer, format="PNG")
    return buffer.getvalue()


def _exam() -> bytes:
    """body:0001 title, body:0002-0003 a question with a merged-cell table, body:0004-0005 a
    question whose stem holds an EMF picture."""
    document = Document()
    document.add_paragraph("Ordklasser", style="Title")
    document.add_paragraph(f"1. {_TABLE_STEM}")
    table = document.add_table(rows=3, cols=2)
    table.cell(0, 0).merge(table.cell(0, 1)).text = "Ord och ordklass"
    for row, (word, kind) in enumerate((("springa", "verb"), ("hus", "substantiv")), start=1):
        table.cell(row, 0).text = word
        table.cell(row, 1).text = kind
    document.add_paragraph(f"2. {_PICTURE_STEM} ").add_run().add_picture(io.BytesIO(_png()))
    picture = document.element.body.findall(qn("w:p"))[-1]
    document.add_paragraph("Svara med en mening.")
    blip = next(picture.iter(qn("a:blip")))
    emf = Part(PackURI("/word/media/figur.emf"), "image/x-emf", b"\x01\x00\x00\x00", None)
    blip.set(qn("r:embed"), document.part.relate_to(emf, RELATIONSHIP_TYPE.IMAGE))
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


_GROUPING: dict[str, JsonValue] = {
    "title_anchors": ["body:0001"],
    "questions": [
        {
            "id": "q1",
            "anchors": ["body:0002", "body:0003"],
            "subpart_anchors": [],
            "answer_key_anchors": [],
        },
        {
            "id": "q2",
            "anchors": ["body:0004", "body:0005"],
            "subpart_anchors": [],
            "answer_key_anchors": [],
        },
    ],
    "shared_contexts": [],
    "other_anchors": [],
}


class _Provider:
    """Answer grouping with the exam's questions and every converter batch with no items."""

    def __init__(self) -> None:
        self.requests: list[StructuredLLMRequest] = []

    async def complete_structured(
        self, *, request: StructuredLLMRequest, profile: StructuredLLMProviderProfile
    ) -> StructuredLLMResponse:
        self.requests.append(request)
        content: Mapping[str, JsonValue] = (
            _GROUPING
            if request.item_id.startswith("docx_grouping")
            else {"title": None, "instructions": [], "answer_key_anchors": [], "items": []}
        )
        return StructuredLLMResponse(
            content=dict(content), finish_reason="completed", usage=StructuredLLMUsage()
        )


def _free_text(name: str) -> dict[str, JsonValue]:
    return {
        "type": "choice",
        "name": name,
        "choice": "free_text",
        "probabilities": [
            {"value": label.value, "probability": 1.0 if label is ItemTypeLabel.FREE_TEXT else 0.0}
            for label in ItemTypeLabel
        ],
        "confidence": 1.0,
    }


async def test_a_merged_cell_reaches_the_labeler_as_an_image_and_a_lost_picture_is_explicit():
    decisions: list[Any] = []  # request bodies as the Decisions endpoint parses them

    def answer(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        decisions.append(body)
        names = [str(question["name"]) for question in body["questions"]]
        return httpx.Response(200, json={"answers": [_free_text(name) for name in names]})

    provider = _Provider()
    content = _exam()
    pipeline = build_docx_conversion_pipeline(
        client=httpx.AsyncClient(transport=httpx.MockTransport(answer)),
        provider=provider,
        sleeper=NoSleep(),
        leases=GrantingLeases(),
        uow=SerializedUnitOfWork(NoTransaction()),
        clock=FixedClock(datetime(2026, 10, 11, tzinfo=UTC)),
        settings=Settings.model_construct(
            LLM_ANSWER_KEY_ENABLED=True, OPENAI_LLM_ANSWER_KEY_API_KEY="test-key"
        ),
        progress=RecordingProgress(),
    )
    outcome = await pipeline.convert(
        job=DocxConversionJob(
            job_id=uuid4(),
            worker_id="worker",
            document_id=uuid4(),
            filename="ordklasser.docx",
            source_sha256="0" * 64,
            source_docx=content,
            chunks=PythonDocxExamChunker().chunk(content=content),
        )
    )

    (labeling,) = decisions
    assert [q["name"] for q in labeling["questions"]] == ["kind_q1"], "q2 must not be labeled"
    (message,) = labeling["input"]
    parts = message["content"]
    assert [part["type"] for part in parts] == ["input_text", "input_image"]
    assert parts[0]["text"].endswith(f"### Question q1\n1. {_TABLE_STEM}")
    assert "springa" not in parts[0]["text"], "the table must not also go in as text"
    url = parts[1]["image_url"]
    assert url.startswith("data:image/png;base64,")
    image = Image.open(io.BytesIO(base64.b64decode(url.removeprefix("data:image/png;base64,"))))
    assert image.width > 0 and image.height > 0

    events = [e for e in outcome.result.events if e.code == "labeler_source_image_unavailable"]
    assert [e.anchors for e in events] == [("body:0004",)]
    converted = [r.item_id for r in provider.requests if r.item_id.startswith("docx_")]
    assert "docx_wi-01" in converted, "the unlabeled question still converts"
    assert outcome.update.pending == ()
