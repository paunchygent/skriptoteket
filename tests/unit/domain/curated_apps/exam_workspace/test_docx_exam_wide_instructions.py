"""Exam-wide text belongs to the document's instructions once; metadata lines go nowhere."""

from uuid import UUID

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import assemble_build_result
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildResult,
    ProducedMetadata,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk

_BOX = "Instruktioner: Skriv tydligt."
_NAME = "Namn: ______"
_CHECK = "Kontrollera dina svar."
_DEL = "DEL A"
_QUESTIONS = {"body:0005": "1. Första frågan", "body:0006": "2. Andra frågan"}


def _chunks(del_kind: str) -> tuple[DocxChunk, ...]:
    lines = {
        "body:0001": ("paragraph", _BOX),
        "body:0002": ("paragraph", _NAME),
        "body:0003": ("paragraph", _CHECK),
        "body:0004": (del_kind, _DEL),
        **{anchor: ("paragraph", text) for anchor, text in _QUESTIONS.items()},
    }
    return tuple(DocxChunk(a, kind, text, text) for a, (kind, text) in lines.items())


def _build(del_kind: str, *, listed: tuple[str, ...]) -> DocxBuildResult:
    texts = {"body:0001": _BOX, "body:0002": _NAME, "body:0003": _CHECK, "body:0004": _DEL}
    return assemble_build_result(
        document_id=UUID(int=1),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=_chunks(del_kind),
        review_reasons=dict.fromkeys(_QUESTIONS, "Ingen fråga."),
        instructions=tuple(ProducedMetadata(text=texts[a], source_anchors=(a,)) for a in listed),
        exam_wide=frozenset({"body:0001", "body:0002", "body:0003"}),
        exam_metadata=frozenset({"body:0002"}),
        questions=tuple((a,) for a in _QUESTIONS),
    )


def _lines(paragraphs) -> list[str]:
    return [
        "".join(getattr(segment, "text", "") for segment in paragraph.segments)
        for paragraph in paragraphs
    ]


@pytest.mark.parametrize("del_kind", ["paragraph", "heading"])
@pytest.mark.parametrize(
    "listed",
    [("body:0001", "body:0002", "body:0004"), ("body:0004",)],
    ids=["reply_lists_exam_wide", "reply_lists_only_del"],
)
def test_exam_wide_text_lands_in_document_instructions_once(del_kind, listed):
    document = _build(del_kind, listed=listed).document

    assert _lines(document.instructions) == [_BOX, _CHECK]
    for item in document.items:
        assert not set(item.plain_text_lines()) & {_BOX, _NAME, _CHECK}
    for parent in document.parents:
        assert not set(_lines(parent.instruction)) & {_BOX, _NAME, _CHECK}


@pytest.mark.parametrize("del_kind", ["paragraph", "heading"])
def test_del_parent_still_forms(del_kind):
    document = _build(del_kind, listed=("body:0001", "body:0002", "body:0004")).document

    assert len(document.items) == 2
    assert len(document.parents) == 1
    assert _DEL in _lines(document.parents[0].instruction)


def test_listed_metadata_line_appears_nowhere():
    document = _build("paragraph", listed=("body:0002", "body:0004")).document

    shown = [
        *_lines(document.instructions),
        *(line for item in document.items for line in item.plain_text_lines()),
        *(line for parent in document.parents for line in _lines(parent.instruction)),
    ]
    assert not [line for line in shown if line.startswith("Namn")]
