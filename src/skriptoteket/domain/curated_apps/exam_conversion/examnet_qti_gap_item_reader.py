"""Gap-interaction item readers for Exam.net QTI items.

Responsibility: gap-fill and inline-choice items read from text-entry and
inline-choice interactions.
"""

from __future__ import annotations

from collections.abc import Mapping
from xml.etree import ElementTree

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_block_item_reader import (
    choice,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_body_reader import (
    ExamNetQtiReadBody,
    read_rich_content,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiInlineChoiceGap,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiTextEntryGap,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_scores import (
    ResponseDeclaration,
    bound_declaration,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_support import (
    UnsupportedInteraction,
    image_resources,
    item,
    local_name,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import (
    qti_tag,
)


def read_gap_item(
    root: ElementTree.Element,
    *,
    body: ElementTree.Element,
    declarations: Mapping[str, ResponseDeclaration],
    max_score: int | float | None,
    item_path: str,
    files: Mapping[str, bytes],
    sequence: int,
) -> ExamNetQtiItem:
    read_body = read_rich_content(list(body), leading_text=body.text)
    if not read_body.gap_elements:
        raise UnsupportedInteraction
    gap_names = {local_name(element.tag) for element in read_body.gap_elements}
    if gap_names == {"qti-text-entry-interaction"}:
        return gap_fill_item(
            root,
            read_body=read_body,
            declarations=declarations,
            max_score=max_score,
            item_path=item_path,
            files=files,
            sequence=sequence,
        )
    if gap_names == {"qti-inline-choice-interaction"}:
        return inline_choice_item(
            root,
            read_body=read_body,
            declarations=declarations,
            max_score=max_score,
            item_path=item_path,
            files=files,
            sequence=sequence,
        )
    raise UnsupportedInteraction


def gap_fill_item(
    root: ElementTree.Element,
    *,
    read_body: ExamNetQtiReadBody,
    declarations: Mapping[str, ResponseDeclaration],
    max_score: int | float | None,
    item_path: str,
    files: Mapping[str, bytes],
    sequence: int,
) -> ExamNetQtiItem:
    return item(
        root,
        sequence=sequence,
        interaction_type=ExamNetQtiInteractionType.GAP_FILL,
        prompt_paragraphs=read_body.paragraphs,
        image_resources=image_resources(read_body.image_elements, item_path=item_path, files=files),
        max_score=max_score,
        text_entry_gaps=tuple(
            _text_entry_gap(element, declarations) for element in read_body.gap_elements
        ),
    )


def inline_choice_item(
    root: ElementTree.Element,
    *,
    read_body: ExamNetQtiReadBody,
    declarations: Mapping[str, ResponseDeclaration],
    max_score: int | float | None,
    item_path: str,
    files: Mapping[str, bytes],
    sequence: int,
) -> ExamNetQtiItem:
    return item(
        root,
        sequence=sequence,
        interaction_type=ExamNetQtiInteractionType.INLINE_CHOICE,
        prompt_paragraphs=read_body.paragraphs,
        image_resources=image_resources(read_body.image_elements, item_path=item_path, files=files),
        max_score=max_score,
        inline_choice_gaps=tuple(
            _inline_choice_gap(element, declarations) for element in read_body.gap_elements
        ),
    )


def _text_entry_gap(
    element: ElementTree.Element,
    declarations: Mapping[str, ResponseDeclaration],
) -> ExamNetQtiTextEntryGap:
    response_identifier, declaration = bound_declaration(element, declarations)
    accepted_values: list[str] = []
    for value in declaration.correct_values:
        stripped = value.strip()
        if stripped:
            accepted_values.append(stripped)
    if declaration.mapping is not None:
        for entry in declaration.mapping.entries:
            stripped = entry.map_key.strip()
            if stripped and stripped not in accepted_values:
                accepted_values.append(stripped)
    return ExamNetQtiTextEntryGap(
        response_identifier=response_identifier,
        label="",
        accepted_values=tuple(accepted_values),
    )


def _inline_choice_gap(
    element: ElementTree.Element,
    declarations: Mapping[str, ResponseDeclaration],
) -> ExamNetQtiInlineChoiceGap:
    response_identifier, declaration = bound_declaration(element, declarations)
    if len(declaration.correct_values) != 1:
        raise UnsupportedInteraction
    options = tuple(choice(option) for option in element.findall(qti_tag("qti-inline-choice")))
    correct_option_identifier = declaration.correct_values[0]
    if correct_option_identifier not in {option.identifier for option in options}:
        raise UnsupportedInteraction
    return ExamNetQtiInlineChoiceGap(
        response_identifier=response_identifier,
        options=options,
        correct_option_identifier=correct_option_identifier,
    )
