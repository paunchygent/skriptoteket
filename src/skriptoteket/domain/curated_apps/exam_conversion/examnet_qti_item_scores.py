"""Score and response-declaration interpretation for Exam.net QTI items.

Responsibility: response declarations, MAXSCORE, per-child points and the
unknown-remainder rule; nothing about prompts, layouts or interactions.
"""

from __future__ import annotations

from collections.abc import Mapping as AbcMapping
from dataclasses import dataclass, replace
from decimal import ROUND_DOWN, Decimal, InvalidOperation
from xml.etree import ElementTree

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_support import (
    UnsupportedInteraction,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import (
    qti_tag,
)


@dataclass(frozen=True)
class MappingEntry:
    map_key: str
    mapped_value: str


@dataclass(frozen=True)
class Mapping:
    upper_bound: str | None
    entries: tuple[MappingEntry, ...]


@dataclass(frozen=True)
class ResponseDeclaration:
    cardinality: str
    base_type: str
    correct_values: tuple[str, ...]
    mapping: Mapping | None


def response_declarations(
    root: ElementTree.Element,
) -> dict[str, ResponseDeclaration]:
    declarations: dict[str, ResponseDeclaration] = {}
    for element in root.findall(qti_tag("qti-response-declaration")):
        identifier = element.get("identifier")
        if not identifier:
            continue
        declarations[identifier] = _response_declaration(element)
    return declarations


def _response_declaration(element: ElementTree.Element) -> ResponseDeclaration:
    correct_response = element.find(qti_tag("qti-correct-response"))
    correct_values: tuple[str, ...] = ()
    if correct_response is not None:
        correct_values = tuple(
            (value.text or "").strip() for value in correct_response.findall(qti_tag("qti-value"))
        )
    mapping_element = element.find(qti_tag("qti-mapping"))
    mapping: Mapping | None = None
    if mapping_element is not None:
        mapping = Mapping(
            upper_bound=mapping_element.get("upper-bound"),
            entries=tuple(
                MappingEntry(
                    map_key=entry.get("map-key") or "",
                    mapped_value=entry.get("mapped-value") or "",
                )
                for entry in mapping_element.findall(qti_tag("qti-map-entry"))
            ),
        )
    return ResponseDeclaration(
        cardinality=element.get("cardinality") or "",
        base_type=element.get("base-type") or "",
        correct_values=correct_values,
        mapping=mapping,
    )


def bound_declaration(
    element: ElementTree.Element,
    declarations: AbcMapping[str, ResponseDeclaration],
) -> tuple[str, ResponseDeclaration]:
    response_identifier = element.get("response-identifier")
    declaration = declarations.get(response_identifier) if response_identifier else None
    if response_identifier is None or declaration is None:
        raise UnsupportedInteraction
    return response_identifier, declaration


def max_score(root: ElementTree.Element) -> int | float | None:
    declaration = next(
        (
            element
            for element in root.findall(qti_tag("qti-outcome-declaration"))
            if element.get("identifier") == "MAXSCORE"
        ),
        None,
    )
    if declaration is None:
        return None
    default_value = declaration.find(qti_tag("qti-default-value"))
    if default_value is None:
        return None
    value = default_value.find(qti_tag("qti-value"))
    if value is None or value.text is None:
        return None
    # A present zero stays zero: export admissibility
    # (examnet_qti_item_admissibility._item_errors: an automatic item without
    # points is blocked) means an exported package never writes an absent score
    # as "0", so MAXSCORE 0 is always a stated zero. Only a missing
    # declaration or value reads as None.
    return number(value.text)


# The native points contract (NativeExamItem.points: a finite non-negative
# int | float; tick_points: a non-negative two-decimal Decimal) admits no
# million-point question and no sub-hundred-quintillionth share. Decimal
# comparisons, adjusted() and exponent reads below never expand the number
# into an int or float; only _to_number does, after these bounds hold.
_MAX_SCORE_ADJUSTED_LIMIT = 5
_MIN_SCORE_EXPONENT = -20


def number(text: str) -> int | float:
    return _to_number(_decimal(text))


def _decimal(text: str) -> Decimal:
    try:
        value = Decimal(text.strip())
    except InvalidOperation as error:
        raise UnsupportedInteraction from error
    if not value.is_finite():
        raise UnsupportedInteraction
    if value < 0:
        raise UnsupportedInteraction
    if value.adjusted() > _MAX_SCORE_ADJUSTED_LIMIT:
        raise UnsupportedInteraction
    exponent = value.as_tuple().exponent
    if isinstance(exponent, int) and exponent < _MIN_SCORE_EXPONENT:
        raise UnsupportedInteraction
    return value


def _to_number(value: Decimal) -> int | float:
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def block_child_points(
    root: ElementTree.Element,
    response_identifier: str,
    declaration: ResponseDeclaration,
) -> int | float | None:
    if declaration.mapping is not None and declaration.mapping.upper_bound is not None:
        return number(declaration.mapping.upper_bound)
    return _all_or_nothing_points(root, response_identifier)


def _all_or_nothing_points(
    root: ElementTree.Element,
    response_identifier: str,
) -> int | float | None:
    processing = root.find(qti_tag("qti-response-processing"))
    if processing is None:
        return None
    for condition in processing.findall(qti_tag("qti-response-condition")):
        response_if = condition.find(qti_tag("qti-response-if"))
        if response_if is None:
            continue
        match = response_if.find(qti_tag("qti-match"))
        if match is None:
            continue
        variable = match.find(qti_tag("qti-variable"))
        correct = match.find(qti_tag("qti-correct"))
        if variable is None or correct is None:
            continue
        if (
            variable.get("identifier") != response_identifier
            or correct.get("identifier") != response_identifier
        ):
            continue
        set_outcome = response_if.find(qti_tag("qti-set-outcome-value"))
        if set_outcome is None:
            return None
        total = set_outcome.find(qti_tag("qti-sum"))
        if total is None:
            return None
        points = total.find(qti_tag("qti-base-value"))
        if points is None or points.text is None:
            return None
        return number(points.text)
    return None


def gap_child_points(
    declarations: AbcMapping[str, ResponseDeclaration],
    gap_elements: tuple[ElementTree.Element, ...],
) -> int | float | None:
    """A parent gap child's own score: the package never states it exactly.

    The exporter writes only a per-gap share rounded down to 0.01, whose
    interval does not identify the total, so a gap or inline-choice child
    inside a parent keeps None here. The parent remainder in
    apply_unknown_remainder is the only exact evidence and assigns it there.
    """

    return None


def apply_unknown_remainder(
    children: list[ExamNetQtiItem],
    max_score: int | float | None,
    declarations: AbcMapping[str, ResponseDeclaration] | None = None,
) -> None:
    """Give a single child without its own points the parent total's remainder.

    A gap or inline-choice child takes the remainder only when it is
    consistent with its stated per-gap share (remainder / gap count, rounded
    down to 0.01, equals the share). More than one unknown child, a negative
    remainder, or an inconsistent or unstated share leaves the child at None
    so the mapper sends it to review instead of guessing.
    """

    if max_score is None:
        return
    unknown = [index for index, child in enumerate(children) if child.max_score is None]
    if len(unknown) != 1:
        return
    known = sum(
        (Decimal(str(child.max_score)) for child in children if child.max_score is not None),
        Decimal(0),
    )
    remainder = Decimal(str(max_score)) - known
    if remainder < 0:
        return
    position = unknown[0]
    child = children[position]
    if declarations is not None and child.interaction_type in (
        ExamNetQtiInteractionType.GAP_FILL,
        ExamNetQtiInteractionType.INLINE_CHOICE,
    ):
        if not _remainder_matches_share(child, declarations, remainder):
            return
    children[position] = replace(children[position], max_score=_to_number(remainder))


def _remainder_matches_share(
    child: ExamNetQtiItem,
    declarations: AbcMapping[str, ResponseDeclaration],
    remainder: Decimal,
) -> bool:
    if child.interaction_type is ExamNetQtiInteractionType.INLINE_CHOICE:
        gaps: tuple[str, ...] = tuple(gap.response_identifier for gap in child.inline_choice_gaps)
    else:
        gaps = tuple(gap.response_identifier for gap in child.text_entry_gaps)
    if not gaps:
        return False
    values: set[Decimal] = set()
    for response_identifier in gaps:
        declaration = declarations.get(response_identifier)
        if declaration is None or declaration.mapping is None or not declaration.mapping.entries:
            return False
        for entry in declaration.mapping.entries:
            try:
                values.add(_decimal(entry.mapped_value))
            except UnsupportedInteraction:
                return False
    if len(values) != 1:
        return False
    share = next(iter(values))
    expected = (remainder / len(gaps)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    return expected == share
