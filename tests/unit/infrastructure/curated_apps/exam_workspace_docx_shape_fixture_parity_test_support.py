"""The drawn figures of ``metodprov_med_bilder.docx`` reach every export below the UI.

TASK-SKRIPT-39-04-22 (D5, D6, D8-D11): the Word import gives questions 5 and 6 their
pictures at the places the PDF import puts them; each picture's asset keeps the Word
shapes it was drawn from; the Word export writes those shapes back and every other
export uses the picture; a picture the teacher replaces or removes takes its shapes with it.

The chunker, the build state and its admission, document assembly and the export renderer
with its real QTI, Word and print writers are the production code. The model's reply is a
scripted fixture, scoped to questions 5 to 7 (the questions that hold a picture); it is
not an AI result. The picture replacement mirrors the editor's document edit (a new asset
without shapes, the old asset leaves the document), because the editor is frontend code.

This module holds the shared build (the ``imported`` fixture) and the export renderer;
the ``test_exam_workspace_docx_shape_fixture_parity_*`` files rebind the fixture.
"""

from __future__ import annotations

import base64
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceExportTarget
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_export_renderer import (
    ExamWorkspaceExportRenderer,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import DocxBuildResult
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxImage,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_print_renderer import (
    WeasyPrintExamPrintRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_writer import (  # noqa: E501
    ExamWorkspaceDocxWriter,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_pdf_renderer import (
    WeasyPrintExamNetPdfRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)

_FIXTURES = Path("tests/fixtures/exam_conversion/pdf_corpus")
_DOCX = _FIXTURES / "metodprov_med_bilder.docx"
_PDF = _FIXTURES / "metodprov_med_bilder.pdf"

_NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "wpg": "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup",
}
_NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_Q5_ANCHOR, _Q6_ANCHOR, _CHART_ANCHOR = "body:0029", "body:0036", "body:0043"
_Q5_LABELS = ("Svenska gymnasieelever (populationen)", "Elever på ett program (urvalet)")
_Q6_LABELS = ("Alla elever på skolan", "Elever som är i biblioteket", "Svarar på frågan")
# The chunks questions 5 to 7 own, heading of question 5 to facit of question 7.
_FIRST_SCOPED, _LAST_SCOPED = 26, 46
_NEW_PICTURE = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAECAIAAAA8r+mnAAAAFElEQVR4nGOUbLJhwAaYsIqSJQEAVB8A33yzxnAAAAAASUVORK5CYII="
)


def _word_chunks() -> tuple[DocxChunk, ...]:
    return PythonDocxExamChunker().chunk(content=_DOCX.read_bytes())


def _words(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


# --- The build, driven through the real admission and assembly ------------------------


def _anchors(first: int, last: int) -> tuple[str, ...]:
    return tuple(f"body:{number:04d}" for number in range(first, last + 1))


def _text(text: str) -> dict[str, JsonValue]:
    return {"kind": "text", "text": text, "accepted_values": []}


def _asset(asset_id: str) -> dict[str, JsonValue]:
    return {"kind": "asset", "text": None, "accepted_values": [], "asset_id": asset_id}


def _reply_item(
    chunks: dict[str, DocxChunk], *, first: int, label: str, kind: str, points: int
) -> dict[str, JsonValue]:
    """What a correct reply gives a choice question of the fixture: the question holds its
    heading, text, drawing, prompt, answer instruction and options (anchors ``first`` to
    ``first + 5``), the chunk after them is its facit. The drawing stays where the source
    puts it, between the question's text and its prompt."""
    anchors = _anchors(first, first + 5)
    _, stem, drawing, prompt, instruction, options = (chunks[a] for a in anchors)
    keyed = {
        part.strip()[0]
        for part in chunks[f"body:{first + 6:04d}"].text[len("Rätt svar: ") :].split("; ")
    }
    (image,) = drawing.images
    return {
        "source_anchors": list(anchors),
        "outcome": "converted",
        "conflict_kind": None,
        "review_reason": None,
        "kind": kind,
        "key_source": "copied",
        "facit_text": chunks[f"body:{first + 6:04d}"].text,
        "printed_label": label,
        "body": [
            {"segments": [_text(stem.text)]},
            {"segments": [_asset(image.asset_id)]},
            {"segments": [_text(prompt.text)]},
            {"segments": [_text(instruction.text)]},
        ],
        "points": points,
        "choices": [
            {"text": line[3:], "correct": line[0] in keyed} for line in options.text.split("\n")
        ],
        "match_left": [],
        "match_right": [],
        "match_pairs": [],
        "criteria": [],
    }


@dataclass(frozen=True)
class _Import:
    """Questions 5 to 7 of the Word import, built from the scripted reply."""

    chunks: dict[str, DocxChunk]
    result: DocxBuildResult

    @property
    def document(self) -> NativeExamDocument:
        return self.result.document

    def picture(self, anchor: str) -> DocxImage:
        (image,) = self.chunks[anchor].images
        return image

    def item_with(self, anchor: str) -> NativeExamItem:
        asset_id = self.picture(anchor).asset_id
        (item,) = (i for i in self.document.items if asset_id in i.body_asset_ids())
        return item


@pytest.fixture(scope="module")
def imported() -> _Import:
    chunks = _word_chunks()
    scoped = chunks[_FIRST_SCOPED : _LAST_SCOPED + 1]
    by_anchor = {chunk.anchor: chunk for chunk in scoped}
    state = DocxBuildState(
        origin_kind="docx_import",
        job_id=uuid4(),
        document_id=uuid4(),
        filename=_DOCX.name,
        source_sha256="0" * 64,
        chunks=scoped,
        # Each question's own chunks: heading to options, never its facit.
        questions=(_anchors(27, 32), _anchors(34, 39), _anchors(41, 46)),
    )
    reply: dict[str, JsonValue] = {
        "items": [
            _reply_item(by_anchor, first=27, label="5", kind="single_choice", points=1),
            _reply_item(by_anchor, first=34, label="6", kind="single_choice", points=1),
            _reply_item(by_anchor, first=41, label="7", kind="multiple_response", points=2),
        ],
        "answer_key_anchors": ["body:0033", "body:0040", "body:0047"],
    }
    admit_batch(reply, state)
    return _Import({chunk.anchor: chunk for chunk in chunks}, state.result())


# --- The exports --------------------------------------------------------------------

_RENDERER = ExamWorkspaceExportRenderer(
    qti_writer=ExamNetQtiPackageWriter(),
    pdf_renderer=WeasyPrintExamNetPdfRenderer(),
    docx_writer=ExamWorkspaceDocxWriter(),
    print_renderer=WeasyPrintExamPrintRenderer(),
)


def _export(
    document: NativeExamDocument,
    assets_by_id: Mapping[str, bytes],
    target: ExamWorkspaceExportTarget,
) -> bytes:
    return _RENDERER.render(document=document, assets_by_id=assets_by_id, target=target).content
