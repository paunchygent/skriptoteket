"""Exam.net PDF markers follow the exam's language (TASK-SKRIPT-39-05-03 D21).

Each corpus exam is converted from its recorded provider rounds and exported through the
native PDF function. Only the Swedish markers documented in sir-convert-a-lot's Swedish
renderer profile are used; every other language keeps the default profile's markers.
"""

import hashlib
import re
from dataclasses import dataclass

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_pdf_target_profile import (
    DEFAULT_EXAMNET_PDF_TARGET_PROFILE_CONTEXT,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_pdf_export import (
    native_exam_to_pdf_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAssetSegment,
    NativeExamAsset,
    NativeExamDocument,
    NativeExamItemKind,
    NativeParagraph,
    NativeTextSegment,
)
from tests.unit.domain.curated_apps.exam_workspace.matching_recording_support import (
    recorded_matching_items,
)
from tests.unit.scripts.exam_conversion_corpus_support import RECORDED_STEMS, gold_exam, replayed

_ENGLISH_MARKERS = (
    "Type:",
    "Multiple choice",
    "Multiple response",
    "Matching",
    "Correct answer",
    "Correct answers",
    "Image ",
)
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


def _exported() -> tuple[list[_Exported], int]:
    exported: list[_Exported] = []
    skipped = 0
    for stem in RECORDED_STEMS:
        document, _ = replayed(stem)
        if document.assets:
            skipped += 1
            continue
        result = native_exam_to_pdf_document(document)
        if result.status is not DigiExamExamNetPdfStatus.SUCCESS:
            skipped += 1
            continue
        language = {"Fråga": "sv", "Question": "en"}.get(_gold_label_word(stem), "")
        exported.append(_Exported(stem, language, document, result.html))
    return exported, skipped


_EXPORTED, _SKIPPED = _exported()


def test_corpus_exports_both_languages() -> None:
    languages = {exam.language for exam in _EXPORTED}
    assert {"sv", "en"} <= languages, (languages, _SKIPPED)


@pytest.mark.parametrize("exam", [e for e in _EXPORTED if e.language == "sv"], ids=lambda e: e.stem)
def test_swedish_exam_prints_no_english_marker_word(exam: _Exported) -> None:
    present = [marker for marker in _ENGLISH_MARKERS if marker in exam.html]
    assert not present, f"{exam.stem} prints English markers {present}"


@pytest.mark.parametrize("exam", [e for e in _EXPORTED if e.language == "en"], ids=lambda e: e.stem)
def test_english_exam_keeps_default_markers_and_english_alt(exam: _Exported) -> None:
    labels = DEFAULT_EXAMNET_PDF_TARGET_PROFILE_CONTEXT.label_policy
    allowed_types = {
        f"{labels.source_item_type_marker}: {labels.free_text_type_label}",
        f"{labels.source_item_type_marker}: {labels.gap_open_cloze_type_label}",
        f"{labels.target_item_type_marker}: {labels.choice_type_label}",
        f"{labels.target_item_type_marker}: {labels.multiple_response_type_label}",
        f"{labels.target_item_type_marker}: {labels.matching_type_label}",
    }
    allowed_keys = {labels.single_answer_key_label, labels.multiple_answer_key_label}
    assert set(_ITEM_TYPE.findall(exam.html)) <= allowed_types
    keys = {first or second for first, second in _KEY_LABEL.findall(exam.html)}
    assert keys <= allowed_keys
    assert not [alt for alt in _ALT.findall(exam.html) if alt.startswith("Bild")]
    assert not [
        word for word in ("Flerval", "Rätt svar", "Rätta", "Matcha ihop") if word in exam.html
    ]


def test_swedish_choice_item_prints_documented_markers() -> None:
    choice_exams = [
        exam
        for exam in _EXPORTED
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
    swedish = next(exam for exam in _EXPORTED if exam.language == "sv")
    recorded = recorded_matching_items(keyed=True)[0]
    matching = recorded.model_copy(
        update={
            "sequence": 1,
            "body": (
                NativeParagraph(
                    segments=(
                        NativeTextSegment(text="Para ihop varje uttryck med det som är rätt."),
                    )
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
                NativeParagraph(segments=(NativeAssetSegment(asset_id=_ASSET_ID),)),
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


@pytest.mark.parametrize(("language", "alt"), [("sv", "Bild"), ("en", "Image")])
def test_image_alt_follows_the_exam_language(language: str, alt: str) -> None:
    exam = next(e for e in _EXPORTED if e.language == language)
    result = native_exam_to_pdf_document(_with_image(exam.document), assets_by_id={_ASSET_ID: _PNG})
    assert result.status is DigiExamExamNetPdfStatus.SUCCESS
    assert f'alt="{alt} {_ASSET_ID}"' in result.html
