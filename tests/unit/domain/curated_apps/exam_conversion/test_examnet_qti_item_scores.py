"""Score-bound and zero-score tests for the Exam.net QTI score reader.

Covers review 596c1654 F3 (unbounded numeric expansion) and F5 (present zero
versus absent points) at the score-reader boundary. Parent-remainder behaviour
(F4) is covered by the application score round-trip tests.
"""

from __future__ import annotations

from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_import_contracts import (
    ExamNetQtiUnsupportedReason,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_reader import (
    read_examnet_qti_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_scores import (
    _decimal,
    max_score,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_support import (
    UnsupportedInteraction,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import QTI_NAMESPACE

pytestmark = pytest.mark.unit

_ITEM_PATH = "items/item_001.xml"
_QTI = f"{{{QTI_NAMESPACE}}}"


def _root() -> ElementTree.Element:
    return ElementTree.Element(
        f"{_QTI}qti-assessment-item",
        {"identifier": "item_001", "title": "Fråga"},
    )


def _max_score(root: ElementTree.Element, value: str) -> None:
    outcome = ElementTree.SubElement(
        root,
        f"{_QTI}qti-outcome-declaration",
        {"identifier": "MAXSCORE", "cardinality": "single", "base-type": "float"},
    )
    default_value = ElementTree.SubElement(outcome, f"{_QTI}qti-default-value")
    ElementTree.SubElement(default_value, f"{_QTI}qti-value").text = value


def _body(root: ElementTree.Element) -> ElementTree.Element:
    return ElementTree.SubElement(root, f"{_QTI}qti-item-body")


def _xml(root: ElementTree.Element) -> bytes:
    ElementTree.indent(root, space="  ")
    payload = ElementTree.tostring(root, encoding="utf-8")
    assert isinstance(payload, bytes)
    return payload


def _minimal_item_xml(score: str) -> bytes:
    root = _root()
    _max_score(root, score)
    body = _body(root)
    paragraph = ElementTree.SubElement(body, f"{_QTI}p")
    paragraph.text = "Instruction"
    return _xml(root)


def _read_minimal(score: str) -> tuple[object, ...]:
    return read_examnet_qti_item(
        xml=_minimal_item_xml(score),
        item_path=_ITEM_PATH,
        files={},
        sequence=1,
    )


@pytest.mark.parametrize("score", ["1e100000000", "1e7", "-1", "1e-21"])
def test_out_of_bound_scores_are_unsupported(score: str) -> None:
    with pytest.raises(UnsupportedInteraction):
        _decimal(score)


@pytest.mark.parametrize("score", ["1e100000000", "1e7", "-1"])
def test_out_of_bound_maxscore_is_skipped_with_an_interaction_note(score: str) -> None:
    (read,) = _read_minimal(score)

    from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_import_contracts import (
        ExamNetQtiUnsupportedItem,
    )

    assert isinstance(read, ExamNetQtiUnsupportedItem)
    assert read.reason is ExamNetQtiUnsupportedReason.INTERACTION
    assert read.sequence == 1


@pytest.mark.parametrize(("score", "expected"), [("1e3", 1000), ("999999", 999999)])
def test_bounded_scores_still_read(score: str, expected: int) -> None:
    assert _decimal(score) == _decimal(str(expected))

    root = _root()
    _max_score(root, score)
    assert max_score(root) == expected


def test_a_present_zero_maxscore_reads_as_zero() -> None:
    root = _root()
    _max_score(root, "0")

    assert max_score(root) == 0


def test_a_missing_maxscore_declaration_reads_as_none() -> None:
    root = _root()

    assert max_score(root) is None


def test_a_missing_maxscore_value_reads_as_none() -> None:
    root = _root()
    outcome = ElementTree.SubElement(
        root,
        f"{_QTI}qti-outcome-declaration",
        {"identifier": "MAXSCORE", "cardinality": "single", "base-type": "float"},
    )
    ElementTree.SubElement(outcome, f"{_QTI}qti-default-value")

    assert max_score(root) is None
