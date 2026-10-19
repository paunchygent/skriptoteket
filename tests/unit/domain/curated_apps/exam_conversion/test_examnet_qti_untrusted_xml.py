"""Adversarial tests for the single hardened QTI XML entry point.

Purpose:
    Prove that ``parse_untrusted_qti_xml`` refuses DTD/entity/external
    constructs inside the parser for every declared encoding, maps encoding
    and well-formedness failures to typed Swedish validation errors, refuses
    overly deep trees iteratively, and that the item reader inherits all of
    it through ``read_examnet_qti_item``.

Relationships:
    Exercises ``examnet_qti_untrusted_xml`` directly and through
    ``examnet_qti_item_reader`` against real exporter item bytes.
"""

from __future__ import annotations

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiItem,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_reader import (
    read_examnet_qti_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_untrusted_xml import (
    UNSAFE_XML_MESSAGE,
    parse_untrusted_qti_xml,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.unit.domain.curated_apps.exam_workspace.examnet_qti_export_test_support import (
    document_of,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_single_choice_item,
)

pytestmark = pytest.mark.unit

_ITEM_PATH = "items/item_001.xml"
_INVALID = "QTI-paketet innehåller ogiltig XML."
_INVALID_ITEM = "QTI-paketet innehåller en fråga som inte är giltig XML."


def _nested(markers: int) -> bytes:
    return ("<r>" + "<x>" * markers + "deep" + "</x>" * markers + "</r>").encode("utf-8")


def _real_item_xml() -> bytes:
    document = document_of((make_single_choice_item(),))
    (exported,) = native_exam_to_examnet_qti_items(document, assets_by_id={})
    return serialize_qti_assessment_item(exported)


def _utf16_with_entity(xml: bytes, *, root_name: str) -> bytes:
    text = xml.decode("utf-8").split("?>", 1)[1]
    dtd = f'<!DOCTYPE {root_name} [<!ENTITY a "ENTITY_EXPANDED"><!ENTITY b "' + "&a;" * 100 + '">]>'
    return ('<?xml version="1.0" encoding="UTF-16"?>' + dtd + text).encode("utf-16")


def _nest_spans(xml: bytes, count: int) -> bytes:
    text = xml.decode("utf-8").replace(
        "</qti-prompt>",
        "<span>" * count + "deep" + "</span>" * count + "</qti-prompt>",
        1,
    )
    return text.encode("utf-8")


def test_valid_xml_parses_to_its_root() -> None:
    root = parse_untrusted_qti_xml(
        b'<?xml version="1.0" encoding="UTF-8"?><a><b>text</b></a>',
        path="manifest",
        invalid_message=_INVALID,
    )

    assert root.tag == "a"


def test_ascii_doctype_is_refused_as_unsafe() -> None:
    payload = b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x "y">]><r>&x;</r>'

    with pytest.raises(DomainError) as refusal:
        parse_untrusted_qti_xml(payload, path="manifest", invalid_message=_INVALID)

    assert refusal.value.code is ErrorCode.VALIDATION_ERROR
    assert refusal.value.message == UNSAFE_XML_MESSAGE
    assert refusal.value.details == {"path": "manifest"}


def test_utf16_item_with_internal_entity_is_refused_as_unsafe() -> None:
    text = _real_item_xml().decode("utf-8").split("?>", 1)[1]
    text = text.replace("</qti-prompt>", "&b;</qti-prompt>", 1)
    dtd = (
        '<!DOCTYPE qti-assessment-item [<!ENTITY a "ENTITY_EXPANDED"><!ENTITY b "'
        + "&a;" * 100
        + '">]>'
    )
    payload = ('<?xml version="1.0" encoding="UTF-16"?>' + dtd + text).encode("utf-16")

    with pytest.raises(DomainError) as refusal:
        parse_untrusted_qti_xml(payload, path=_ITEM_PATH, invalid_message=_INVALID)

    assert refusal.value.code is ErrorCode.VALIDATION_ERROR
    assert refusal.value.message == UNSAFE_XML_MESSAGE
    assert refusal.value.details == {"path": _ITEM_PATH}


def test_utf16_doctype_without_entity_is_refused_as_unsafe() -> None:
    text = _real_item_xml().decode("utf-8").split("?>", 1)[1]
    payload = (
        '<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE qti-assessment-item>' + text
    ).encode("utf-16")

    with pytest.raises(DomainError) as refusal:
        parse_untrusted_qti_xml(payload, path=_ITEM_PATH, invalid_message=_INVALID)

    assert refusal.value.message == UNSAFE_XML_MESSAGE
    assert refusal.value.details == {"path": _ITEM_PATH}


def test_unknown_encoding_is_a_typed_refusal() -> None:
    payload = _real_item_xml().replace(b'encoding="UTF-8"', b'encoding="x-does-not-exist"')

    with pytest.raises(DomainError) as refusal:
        parse_untrusted_qti_xml(payload, path=_ITEM_PATH, invalid_message=_INVALID)

    assert refusal.value.code is ErrorCode.VALIDATION_ERROR
    assert refusal.value.message == _INVALID
    assert refusal.value.details == {"path": _ITEM_PATH}


def test_undecodable_bytes_are_a_typed_refusal() -> None:
    with pytest.raises(DomainError) as refusal:
        parse_untrusted_qti_xml(
            b'<?xml version="1.0" encoding="UTF-8"?><r>\xff\xfe</r>',
            path="manifest",
            invalid_message=_INVALID,
        )

    assert refusal.value.code is ErrorCode.VALIDATION_ERROR
    assert refusal.value.message == _INVALID


def test_undefined_entity_reference_is_malformed_not_unsafe() -> None:
    with pytest.raises(DomainError) as refusal:
        parse_untrusted_qti_xml(b"<r>&nosuch;</r>", path="manifest", invalid_message=_INVALID)

    assert refusal.value.message == _INVALID


def test_tree_at_the_depth_limit_parses() -> None:
    root = parse_untrusted_qti_xml(_nested(63), path="manifest", invalid_message=_INVALID)

    assert root.tag == "r"


def test_tree_past_the_depth_limit_is_a_typed_refusal() -> None:
    with pytest.raises(DomainError) as refusal:
        parse_untrusted_qti_xml(_nested(64), path="manifest", invalid_message=_INVALID)

    assert refusal.value.code is ErrorCode.VALIDATION_ERROR
    assert refusal.value.message == _INVALID
    assert refusal.value.details == {"path": "manifest"}


def test_utf16_entity_item_is_refused_as_unsafe_through_the_item_reader() -> None:
    payload = _utf16_with_entity(_real_item_xml(), root_name="qti-assessment-item")
    payload = (
        payload.decode("utf-16").replace("</qti-prompt>", "&b;</qti-prompt>", 1).encode("utf-16")
    )

    with pytest.raises(DomainError) as refusal:
        read_examnet_qti_item(xml=payload, item_path=_ITEM_PATH, files={}, sequence=1)

    assert refusal.value.code is ErrorCode.VALIDATION_ERROR
    assert refusal.value.message == UNSAFE_XML_MESSAGE
    assert refusal.value.details == {"path": _ITEM_PATH}


def test_utf16_doctype_item_is_refused_as_unsafe_through_the_item_reader() -> None:
    text = _real_item_xml().decode("utf-8").split("?>", 1)[1]
    payload = (
        '<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE qti-assessment-item>' + text
    ).encode("utf-16")

    with pytest.raises(DomainError) as refusal:
        read_examnet_qti_item(xml=payload, item_path=_ITEM_PATH, files={}, sequence=1)

    assert refusal.value.message == UNSAFE_XML_MESSAGE
    assert refusal.value.details == {"path": _ITEM_PATH}


def test_item_with_unknown_encoding_is_a_typed_refusal() -> None:
    payload = _real_item_xml().replace(b'encoding="UTF-8"', b'encoding="x-does-not-exist"')

    with pytest.raises(DomainError) as refusal:
        read_examnet_qti_item(xml=payload, item_path=_ITEM_PATH, files={}, sequence=1)

    assert refusal.value.code is ErrorCode.VALIDATION_ERROR
    assert refusal.value.message == _INVALID_ITEM
    assert refusal.value.details == {"path": _ITEM_PATH}


def test_600_nested_spans_in_an_item_body_are_a_typed_refusal() -> None:
    with pytest.raises(DomainError) as refusal:
        read_examnet_qti_item(
            xml=_nest_spans(_real_item_xml(), 600),
            item_path=_ITEM_PATH,
            files={},
            sequence=1,
        )

    assert refusal.value.code is ErrorCode.VALIDATION_ERROR
    assert refusal.value.message == _INVALID_ITEM
    assert refusal.value.details == {"path": _ITEM_PATH}


def test_60_nested_spans_in_an_item_body_still_parse() -> None:
    (read,) = read_examnet_qti_item(
        xml=_nest_spans(_real_item_xml(), 60),
        item_path=_ITEM_PATH,
        files={},
        sequence=1,
    )

    assert isinstance(read, ExamNetQtiItem)
