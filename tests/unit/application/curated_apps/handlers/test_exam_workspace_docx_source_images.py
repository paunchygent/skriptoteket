"""A source part markdown cannot carry reaches the labeler as an image of that part (D14, R-F5).

The production pipeline converts exams built in Word: a table with a merged cell, a picture
or a text box in a paragraph of its own, and a picture in a format no image can be made of.
The Decisions first pass is the real HTTP adapter; only the network is replaced.
"""

import base64
import io
from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from docx import Document
from docx.document import Document as DocxDocument
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.opc.packuri import PackURI
from docx.opc.part import Part
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.oxml.text.paragraph import CT_P
from PIL import Image
from pydantic import BaseModel, JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_pipeline import (
    DocxConversionJob,
    DocxConversionOutcome,
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
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_labeler_markdown import (  # noqa: E501
    PythonDocxLabelerMarkdown,
)
from skriptoteket.protocols.item_type_labeler import ItemTypeLabel
from tests.fixtures.time_fixtures import FixedClock
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    GrantingLeases,
    NoSleep,
    NoTransaction,
    RecordingProgress,
)

pytestmark = pytest.mark.unit

_TABLE_STEM = "Para ihop varje ord med sin ordklass."
_PICTURE_STEM = "Vad visar bilden?"


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (120, 60), (40, 90, 160)).save(buffer, format="PNG")
    return buffer.getvalue()


def _emf(document: DocxDocument, paragraph: CT_P) -> None:
    """Point the paragraph's picture at an EMF part, which no browser can draw."""
    blip = next(paragraph.iter(qn("a:blip")))
    emf = Part(PackURI("/word/media/figur.emf"), "image/x-emf", b"\x01\x00\x00\x00", None)
    blip.set(qn("r:embed"), document.part.relate_to(emf, RELATIONSHIP_TYPE.IMAGE))


def _save(document: DocxDocument) -> bytes:
    buffer = io.BytesIO()
    document.save(buffer)
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
    _emf(document, picture)
    return _save(document)


_TEXT_BOX = (
    f"<mc:AlternateContent {nsdecls('w')} "
    'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006">'
    '<mc:Choice Requires="wps"><w:drawing><w:txbxContent>'
    "<w:p><w:r><w:t>Ja eller nej</w:t></w:r></w:p></w:txbxContent></w:drawing></mc:Choice>"
    "<mc:Fallback><w:pict><w:txbxContent>"
    "<w:p><w:r><w:t>Ja eller nej</w:t></w:r></w:p></w:txbxContent></w:pict></mc:Fallback>"
    "</mc:AlternateContent>"
)


def _drawn_exam() -> bytes:
    """Each drawn block sits in a paragraph with no text of its own: body:0003 a PNG,
    body:0005 a text box, body:0007 an EMF picture."""
    document = Document()
    document.add_paragraph("Bildfrågor", style="Title")
    document.add_paragraph(f"1. {_PICTURE_STEM}")
    document.add_picture(io.BytesIO(_png()))
    document.add_paragraph("2. Vad står i rutan?")
    document.add_paragraph().add_run()._r.append(parse_xml(_TEXT_BOX))
    document.add_paragraph("3. Beskriv figuren.")
    document.add_picture(io.BytesIO(_png()))
    _emf(document, document.element.body.findall(qn("w:p"))[-1])
    document.add_paragraph("Svara med en mening.")
    return _save(document)


def _question(question_id: str, *anchors: int) -> dict[str, JsonValue]:
    return {
        "id": question_id,
        "anchors": [f"body:{anchor:04d}" for anchor in anchors],
        "subpart_anchors": [],
        "answer_key_anchors": [],
    }


_DRAWN_GROUPING: dict[str, JsonValue] = {
    "title_anchors": ["body:0001"],
    "questions": [_question("q1", 2, 3), _question("q2", 4, 5), _question("q3", 6, 7, 8)],
    "shared_contexts": [],
    "other_anchors": [],
}


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

    def __init__(self, grouping: Mapping[str, JsonValue]) -> None:
        self.grouping = grouping
        self.requests: list[StructuredLLMRequest] = []

    async def complete_structured(
        self, *, request: StructuredLLMRequest, profile: StructuredLLMProviderProfile
    ) -> StructuredLLMResponse:
        self.requests.append(request)
        content: Mapping[str, JsonValue] = (
            self.grouping
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


class _Part(BaseModel):
    type: str
    text: str = ""
    image_url: str = ""


class _Message(BaseModel):
    content: list[_Part]


class _Question(BaseModel):
    name: str


class _DecisionsBody(BaseModel):
    """The fields of a Decisions request body these tests read."""

    input: list[_Message] | str  # text only when no source image goes in
    questions: list[_Question]


async def _convert(
    content: bytes, grouping: Mapping[str, JsonValue]
) -> tuple[list[_DecisionsBody], _Provider, DocxConversionOutcome]:
    decisions: list[_DecisionsBody] = []

    def answer(request: httpx.Request) -> httpx.Response:
        body = _DecisionsBody.model_validate_json(request.content)
        decisions.append(body)
        answers = [_free_text(question.name) for question in body.questions]
        return httpx.Response(200, json={"answers": answers})

    provider = _Provider(grouping)
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
            filename="prov.docx",
            source_sha256="0" * 64,
            source_docx=content,
            chunks=PythonDocxExamChunker().chunk(content=content),
        )
    )
    return decisions, provider, outcome


def _image(part: _Part) -> Image.Image:
    assert part.image_url.startswith("data:image/png;base64,")
    return Image.open(
        io.BytesIO(base64.b64decode(part.image_url.removeprefix("data:image/png;base64,")))
    )


@pytest.mark.asyncio
async def test_a_merged_cell_reaches_the_labeler_as_an_image_and_a_lost_picture_is_explicit():
    decisions, provider, outcome = await _convert(_exam(), _GROUPING)

    (labeling,) = decisions
    assert [q.name for q in labeling.questions] == ["kind_q1"], "q2 must not be labeled"
    assert not isinstance(labeling.input, str), "the source images must go in"
    (message,) = labeling.input
    parts = message.content
    assert [part.type for part in parts] == ["input_text", "input_image"]
    assert parts[0].text.endswith(f"### Question q1\n1. {_TABLE_STEM}")
    assert "springa" not in parts[0].text, "the table must not also go in as text"
    image = _image(parts[1])
    assert image.width > 0 and image.height > 0

    events = [e for e in outcome.result.events if e.code == "labeler_source_image_unavailable"]
    assert [e.anchors for e in events] == [("body:0004",)]
    converted = [r.item_id for r in provider.requests if r.item_id.startswith("docx_")]
    assert "docx_wi-01" in converted, "the unlabeled question still converts"
    assert outcome.update.pending == ()


def test_a_block_with_only_a_drawing_is_projected_at_its_source_position():
    source = PythonDocxLabelerMarkdown().source(content=_drawn_exam())

    assert [chunk.anchor for chunk in source.chunks] == [f"body:{i:04d}" for i in range(1, 9)]
    assert sorted(source.images) == ["body:0003", "body:0005"]
    assert list(source.unavailable) == ["body:0007"]


@pytest.mark.asyncio
async def test_a_picture_or_text_box_alone_in_its_paragraph_reaches_the_labeler_and_converter():
    decisions, provider, outcome = await _convert(_drawn_exam(), _DRAWN_GROUPING)

    (grouping,) = [r for r in provider.requests if r.item_id.startswith("docx_grouping")]
    for anchor in ("body:0003", "body:0005", "body:0007"):
        assert f"[{anchor}]" in grouping.user_payload, "grouping must see every drawn block"

    (labeling,) = decisions
    assert [q.name for q in labeling.questions] == ["kind_q1", "kind_q2"]
    assert not isinstance(labeling.input, str), "the source images must go in"
    (message,) = labeling.input
    parts = message.content
    assert [part.type for part in parts] == ["input_text", "input_image"] * 2
    assert parts[0].text.endswith(f"### Question q1\n1. {_PICTURE_STEM}")
    assert parts[2].text.endswith("### Question q2\n2. Vad står i rutan?")
    assert all("Ja eller nej" not in part.text for part in parts), "a text box is drawn, not typed"
    assert _image(parts[1]).width > 0 and _image(parts[3]).width > 0

    events = [e for e in outcome.result.events if e.code == "labeler_source_image_unavailable"]
    assert [e.anchors for e in events] == [("body:0007",)]
    batches = {
        r.item_id: r.user_payload for r in provider.requests if r.item_id.startswith("docx_w")
    }
    (unlabeled,) = [
        payload for item_id, payload in batches.items() if item_id.startswith("docx_wi")
    ]
    assert '"body:0007"' in unlabeled, "the unlabeled question still converts with its picture"
    labeled = "".join(
        payload for item_id, payload in batches.items() if item_id.startswith("docx_w1")
    )
    assert '"body:0003"' in labeled and '"body:0005"' in labeled
    assert outcome.update.pending == ()
