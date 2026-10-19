"""Exam.net PDF markers are Swedish for every exam (user decision of 2026-10-18).

Each corpus exam is converted from its recorded provider rounds and exported through the
native PDF function. The Swedish markers documented in sir-convert-a-lot's Swedish renderer
profile are used whatever language the exam is written in.
"""

import hashlib
import re
from dataclasses import dataclass
from functools import cache

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfStatus,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_pdf_export import (
    native_exam_to_pdf_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from tests.unit.domain.curated_apps.exam_workspace.matching_recording_support import (
    recorded_matching_items,
)
from tests.unit.scripts.exam_conversion_corpus_support import RECORDED_STEMS, gold_exam, replayed

_ITEM_TYPE = re.compile(r'<p class="item-type">([^<]*)</p>')
_KEY_LABEL = re.compile(r'<p class="answer-key">([^<:]*):|<div class="answer-key"><p>([^<:]*):</p>')
_ALT = re.compile(r'alt="([^"]*)"')


@dataclass(frozen=True)
class _Exported:
    stem: str
    language: str
    document: NativeExamDocument
    html: str


def _gold_label_word(stem: str) -> str:
    label = gold_exam(stem).questions[0].source_label.split(",")[-1]
    match = re.match(r"\s*(\w+)\s+\d", label)
    assert match is not None, label
    return match.group(1)


@cache
def _export(stem: str) -> _Exported | None:
    """The exam's export, or None when it has assets or does not print.

    Replaying an exam is expensive, so it runs inside the tests, once per process, and never
    while pytest collects: every xdist worker collects every module.
    """
    document, _ = replayed(stem)
    if document.assets:
        return None
    result = native_exam_to_pdf_document(document)
    if result.status is not DigiExamExamNetPdfStatus.SUCCESS:
        return None
    language = {"Fråga": "sv", "Question": "en"}.get(_gold_label_word(stem), "")
    return _Exported(stem, language, document, result.html)


def _exported() -> list[_Exported]:
    return [exam for stem in RECORDED_STEMS if (exam := _export(stem)) is not None]


def test_corpus_exports_both_languages() -> None:
    exported = _exported()
    languages = {exam.language for exam in exported}
    assert {"sv", "en"} <= languages, (languages, len(RECORDED_STEMS) - len(exported))


@pytest.mark.parametrize("stem", RECORDED_STEMS)
def test_every_exam_prints_only_swedish_markers(stem: str) -> None:
    exam = _export(stem)
    if exam is None:
        pytest.skip(f"{stem} has assets or does not print")
    allowed_types = {
        "Typ: Fritext",
        "Typ: Lucktext",
        "Typ: Flerval",
        "Typ: Matcha ihop",
        "Typ: Ordna",
    }
    allowed_keys = {"Rätt svar", "Rätta svar", "Rätta par", "Rätt ordning", "Rättningsmall"}
    assert set(_ITEM_TYPE.findall(exam.html)) <= allowed_types
    keys = {first or second for first, second in _KEY_LABEL.findall(exam.html)}
    assert keys <= allowed_keys
    assert not [alt for alt in _ALT.findall(exam.html) if alt.startswith("Image")]


def test_swedish_choice_item_prints_documented_markers() -> None:
    choice_exams = [
        exam
        for exam in _exported()
        if exam.language == "sv"
        and any(item.kind is NativeExamItemKind.SINGLE_CHOICE for item in exam.document.items)
    ]
    assert choice_exams, "the current corpus must exercise Swedish choice markers"
    for exam in choice_exams:
        assert "Typ: Flerval" in exam.html
        assert "Rätt svar:" in exam.html


def test_swedish_matching_item_prints_documented_markers() -> None:
    # The current Swedish corpus has no matching item. Exercise the exporter
    # deliberately: retain a real recorded matching key in a Swedish document,
    # with an explicitly synthetic Swedish instruction, rather than skipping.
    swedish = next(exam for exam in _exported() if exam.language == "sv")
    recorded = recorded_matching_items(keyed=True)[0]
    matching = recorded.model_copy(
        update={
            "sequence": 1,
            "body": (
                NativeParagraph(
                    heading_level=None,
                    segments=(
                        NativeTextSegment(
                            text="Para ihop varje uttryck med det som är rätt.", marks=()
                        ),
                    ),
                ),
            ),
        }
    )
    document = swedish.document.model_copy(update={"items": (matching,), "parents": ()})
    result = native_exam_to_pdf_document(document)
    assert result.status is DigiExamExamNetPdfStatus.SUCCESS
    assert "Typ: Matcha ihop" in result.html
    assert "Rätta par:" in result.html


_PNG = b"\x89PNG\r\n\x1a\nimage-bytes"
_ASSET_ID = "asset_0123456789abcdef"


def _with_image(document: NativeExamDocument) -> NativeExamDocument:
    first = document.items[0]
    illustrated = first.model_copy(
        update={
            "body": (
                *first.body,
                NativeParagraph(
                    heading_level=None, segments=(NativeAssetSegment(asset_id=_ASSET_ID),)
                ),
            )
        }
    )
    asset = NativeExamAsset(
        asset_id=_ASSET_ID,
        sha256=hashlib.sha256(_PNG).hexdigest(),
        media_type="image/png",
        byte_length=len(_PNG),
    )
    return document.model_copy(
        update={"items": (illustrated, *document.items[1:]), "assets": (asset,)}
    )


@pytest.mark.parametrize("language", ["sv", "en"])
def test_image_alt_is_swedish_for_every_exam_language(language: str) -> None:
    exam = next(e for e in _exported() if e.language == language)
    result = native_exam_to_pdf_document(_with_image(exam.document), assets_by_id={_ASSET_ID: _PNG})
    assert result.status is DigiExamExamNetPdfStatus.SUCCESS
    assert f'alt="Bild {_ASSET_ID}"' in result.html
