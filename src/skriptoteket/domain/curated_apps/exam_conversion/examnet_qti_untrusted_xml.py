"""Parse one untrusted QTI XML document behind a single hardened entry point.

Purpose:
    Decode and parse a manifest, assessment-test or item document from raw
    bytes. DTD, entity and external constructs are refused inside the parser
    (after decoding, so the decision holds for every declared encoding),
    encoding and well-formedness failures become typed Swedish validation
    errors, and element trees deeper than ``_MAX_DEPTH`` are refused
    iteratively before recursive content readers run.

Relationships:
    Consumed by ``examnet_qti_item_reader._parse_item`` and the
    conversion-hub ``examnet_qti_package_reader``. This module owns the
    unsafe-XML message for the whole QTI import lane.
"""

from __future__ import annotations

from xml.etree import ElementTree

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import fromstring

from skriptoteket.domain.errors import validation_error

__all__ = [
    "UNSAFE_XML_MESSAGE",
    "parse_untrusted_qti_xml",
]


UNSAFE_XML_MESSAGE = "QTI-paketet innehåller en otillåten XML-konstruktion."


_MAX_DEPTH = 64


def parse_untrusted_qti_xml(
    payload: bytes, *, path: str, invalid_message: str
) -> ElementTree.Element:
    """Parse untrusted QTI XML bytes into its root element.

    ``DefusedXmlException`` (DTD, entity or external constructs) becomes the
    shared unsafe-XML refusal. ``ParseError``, ``LookupError`` (undeclared or
    unknown encoding), ``UnicodeError`` and the parser's ``ValueError`` for
    unsupported multibyte encodings become the caller's malformed-XML
    refusal. Only those exception types are caught.
    """

    try:
        root = fromstring(payload, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    except DefusedXmlException as error:
        raise validation_error(UNSAFE_XML_MESSAGE, {"path": path}) from error
    except (ElementTree.ParseError, LookupError, UnicodeError, ValueError) as error:
        raise validation_error(invalid_message, {"path": path}) from error
    _refuse_too_deep(root, path=path, invalid_message=invalid_message)
    return root


def _refuse_too_deep(root: ElementTree.Element, *, path: str, invalid_message: str) -> None:
    """Refuse element trees deeper than ``_MAX_DEPTH`` without recursion."""

    stack: list[tuple[ElementTree.Element, int]] = [(root, 1)]
    while stack:
        element, depth = stack.pop()
        if depth > _MAX_DEPTH:
            raise validation_error(invalid_message, {"path": path})
        for child in element:
            stack.append((child, depth + 1))
