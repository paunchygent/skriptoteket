"""Gap paragraphs with an inline answer key but no blank run (TASK-SKRIPT-39-04-17).

A source paragraph with no blank run before an inline answer label (``ANSWER_LABEL``)
has one blank run at the label's place: the paragraph is built from its source text
up to the label, and a reply gap count other than one raises
``GapCountMismatchError``. Every case runs the real fixtures through
``aligned_native_item`` so the domain rule and its wiring are proved together.
"""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import (
    FormattingTransferError,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_gap_paragraphs import (
    GapCountMismatchError,
)
from tests.unit.domain.curated_apps.exam_workspace.gap_paragraph_test_support import (
    chunk as _chunk,
)
from tests.unit.domain.curated_apps.exam_workspace.gap_paragraph_test_support import (
    gap as _gap,
)
from tests.unit.domain.curated_apps.exam_workspace.gap_paragraph_test_support import (
    item as _item,
)
from tests.unit.domain.curated_apps.exam_workspace.gap_paragraph_test_support import (
    text as _text,
)

pytestmark = pytest.mark.unit


def test_a_word_before_an_inline_answer_label_is_kept_with_one_gap():
    chunks = (_chunk("body:0001", "a) solrosornas Svar: sol (R) + ros (R)"),)
    produced = _item(
        chunks,
        [{"segments": [_text("a) sol"), _gap()]}],
    )
    result = aligned_native_item(produced, chunks=chunks, language="sv").item
    assert body_plain_text(result.body) == "a) solrosornas [___]"
    assert "Svar" not in body_plain_text(result.body)
    assert "sol (R)" not in body_plain_text(result.body)


def test_two_gaps_for_an_inline_answer_label_paragraph_raise_a_count_mismatch():
    chunks = (_chunk("body:0001", "a) solrosornas Svar: sol (R) + ros (R)"),)
    produced = _item(
        chunks,
        [{"segments": [_text("a) sol"), _gap(), _text(" + ros"), _gap()]}],
    )
    with pytest.raises(GapCountMismatchError) as raised:
        aligned_native_item(produced, chunks=chunks, language="sv")
    assert not isinstance(raised.value, FormattingTransferError)
    assert (raised.value.gaps, raised.value.blanks) == (2, 1)


def test_appended_gaps_for_an_inline_answer_label_paragraph_raise_a_count_mismatch():
    chunks = (_chunk("body:0001", "a) snöbollarnas Svar: snö (R) + boll (R)"),)
    produced = _item(
        chunks,
        [{"segments": [_text("a) snö + boll"), _gap(), _gap()]}],
    )
    with pytest.raises(GapCountMismatchError) as raised:
        aligned_native_item(produced, chunks=chunks, language="sv")
    assert not isinstance(raised.value, FormattingTransferError)
    assert (raised.value.gaps, raised.value.blanks) == (2, 1)


def test_a_wrapped_answer_label_cuts_the_build_span_at_the_wrapper():
    chunks = (_chunk("body:0001", "a) solrosornas (Svar: sol)"),)
    produced = _item(
        chunks,
        [{"segments": [_text("a) sol"), _gap()]}],
    )
    result = aligned_native_item(produced, chunks=chunks, language="sv").item
    assert body_plain_text(result.body) == "a) solrosornas [___]"


def test_an_underscore_run_before_an_inline_answer_label_is_the_only_run():
    chunks = (_chunk("body:0001", "I ___ (vara) happy. Svar: was"),)
    produced = _item(
        chunks,
        [{"segments": [_text("I "), _gap(), _text(" (vara) happy.")]}],
    )
    result = aligned_native_item(produced, chunks=chunks, language="sv").item
    assert body_plain_text(result.body) == "I [___] (vara) happy."
    assert body_plain_text(result.body).count("[___]") == 1


def test_a_lone_answer_line_with_a_blank_run_builds_just_the_gap():
    chunks = (_chunk("body:0001", "Svar: ________"),)
    produced = _item(
        chunks,
        [{"segments": [_text("Svar: "), _gap()]}],
    )
    result = aligned_native_item(produced, chunks=chunks, language="sv").item
    assert body_plain_text(result.body) == "[___]"


def test_a_paragraph_with_neither_a_label_nor_a_blank_run_keeps_the_reply():
    chunks = (_chunk("body:0001", "Name a river."),)
    produced = _item(
        chunks,
        [{"segments": [_text("Name a "), _gap(), _text(".")]}],
    )
    result = aligned_native_item(produced, chunks=chunks, language="sv").item
    assert body_plain_text(result.body) == "Name a [___]."
