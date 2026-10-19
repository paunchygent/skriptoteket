"""Standalone block-interaction item readers for Exam.net QTI items.

Responsibility: choice, ordering, matching and free-text items read from a
single block interaction and its surrounding prompt.
"""

from __future__ import annotations

from collections.abc import Mapping
from xml.etree import ElementTree

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_body_reader import (
    ExamNetQtiReadBody,
    read_rich_content,
    read_text_paragraphs,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiEvaluationMode,
    ExamNetQtiImageResource,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiMatchEntry,
    ExamNetQtiMatchPair,
    ExamNetQtiPromptParagraph,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_scores import (
    ResponseDeclaration,
    number,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_support import (
    UnsupportedInteraction,
    image_resources,
    item,
    plain_text,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import (
    qti_tag,
)


def read_block_item(
    root: ElementTree.Element,
    *,
    body: ElementTree.Element,
    block: ElementTree.Element,
    declarations: Mapping[str, ResponseDeclaration],
    max_score: int | float | None,
    item_path: str,
    files: Mapping[str, bytes],
    sequence: int,
) -> ExamNetQtiItem:
    before, prompt, after = _read_block_prompt(
        body=body,
        block=block,
    )
    if before.gap_elements or prompt.gap_elements or after.gap_elements:
        raise UnsupportedInteraction

    prompt_paragraphs = (*before.paragraphs, *prompt.paragraphs, *after.paragraphs)
    image_elements = (
        *before.image_elements,
        *prompt.image_elements,
        *after.image_elements,
    )
    resolved_images = image_resources(image_elements, item_path=item_path, files=files)
    response_identifier = block.get("response-identifier")
    declaration = declarations.get(response_identifier) if response_identifier else None
    if declaration is None:
        raise UnsupportedInteraction

    if block.tag == qti_tag("qti-choice-interaction"):
        return choice_item(
            root,
            block=block,
            declaration=declaration,
            prompt_paragraphs=prompt_paragraphs,
            image_resources=resolved_images,
            max_score=max_score,
            sequence=sequence,
        )
    if block.tag == qti_tag("qti-order-interaction"):
        return ordering_item(
            root,
            block=block,
            declaration=declaration,
            prompt_paragraphs=prompt_paragraphs,
            image_resources=resolved_images,
            max_score=max_score,
            sequence=sequence,
        )
    if block.tag == qti_tag("qti-match-interaction"):
        return matching_item(
            root,
            block=block,
            declaration=declaration,
            prompt_paragraphs=prompt_paragraphs,
            image_resources=resolved_images,
            max_score=max_score,
            sequence=sequence,
        )
    return free_text_item(
        root,
        declaration=declaration,
        prompt_paragraphs=prompt_paragraphs,
        image_resources=resolved_images,
        max_score=max_score,
        sequence=sequence,
    )


def _read_block_prompt(
    *,
    body: ElementTree.Element,
    block: ElementTree.Element,
) -> tuple[ExamNetQtiReadBody, ExamNetQtiReadBody, ExamNetQtiReadBody]:
    children = list(body)
    position = children.index(block)
    before = read_rich_content(children[:position], leading_text=body.text)

    prompt_element = block.find(qti_tag("qti-prompt"))
    if prompt_element is None:
        prompt = read_rich_content(())
    else:
        prompt = read_rich_content(
            list(prompt_element),
            leading_text=prompt_element.text,
            image_offset=len(before.image_elements),
            gap_offset=len(before.gap_elements),
        )

    after = read_rich_content(
        children[position + 1 :],
        leading_text=block.tail,
        image_offset=len(before.image_elements) + len(prompt.image_elements),
        gap_offset=len(before.gap_elements) + len(prompt.gap_elements),
    )
    return before, prompt, after


def choice_item(
    root: ElementTree.Element,
    *,
    block: ElementTree.Element,
    declaration: ResponseDeclaration,
    prompt_paragraphs: tuple[ExamNetQtiPromptParagraph, ...],
    image_resources: tuple[ExamNetQtiImageResource, ...],
    max_score: int | float | None,
    sequence: int,
) -> ExamNetQtiItem:
    if declaration.cardinality == "single":
        interaction_type = ExamNetQtiInteractionType.SINGLE_CHOICE
    elif declaration.cardinality == "multiple":
        interaction_type = ExamNetQtiInteractionType.MULTIPLE_RESPONSE
    else:
        raise UnsupportedInteraction
    return item(
        root,
        sequence=sequence,
        interaction_type=interaction_type,
        prompt_paragraphs=prompt_paragraphs,
        image_resources=image_resources,
        max_score=max_score,
        choices=tuple(choice(element) for element in block.findall(qti_tag("qti-simple-choice"))),
        correct_choice_identifiers=declaration.correct_values,
    )


def ordering_item(
    root: ElementTree.Element,
    *,
    block: ElementTree.Element,
    declaration: ResponseDeclaration,
    prompt_paragraphs: tuple[ExamNetQtiPromptParagraph, ...],
    image_resources: tuple[ExamNetQtiImageResource, ...],
    max_score: int | float | None,
    sequence: int,
) -> ExamNetQtiItem:
    return item(
        root,
        sequence=sequence,
        interaction_type=ExamNetQtiInteractionType.ORDERING,
        prompt_paragraphs=prompt_paragraphs,
        image_resources=image_resources,
        max_score=max_score,
        choices=tuple(choice(element) for element in block.findall(qti_tag("qti-simple-choice"))),
        correct_choice_identifiers=declaration.correct_values,
    )


def matching_item(
    root: ElementTree.Element,
    *,
    block: ElementTree.Element,
    declaration: ResponseDeclaration,
    prompt_paragraphs: tuple[ExamNetQtiPromptParagraph, ...],
    image_resources: tuple[ExamNetQtiImageResource, ...],
    max_score: int | float | None,
    sequence: int,
) -> ExamNetQtiItem:
    match_sets = block.findall(qti_tag("qti-simple-match-set"))
    if len(match_sets) != 2:
        raise UnsupportedInteraction
    match_left = tuple(
        _match_entry(element)
        for element in match_sets[0].findall(qti_tag("qti-simple-associable-choice"))
    )
    match_right = tuple(
        _match_entry(element)
        for element in match_sets[1].findall(qti_tag("qti-simple-associable-choice"))
    )
    left_by_identifier = {entry.identifier: entry for entry in match_left}
    right_by_identifier = {entry.identifier: entry for entry in match_right}
    pairs: list[ExamNetQtiMatchPair] = []
    for value in declaration.correct_values:
        identifiers = value.split()
        if len(identifiers) != 2:
            raise UnsupportedInteraction
        left_identifier, right_identifier = identifiers
        left = left_by_identifier.get(left_identifier)
        right = right_by_identifier.get(right_identifier)
        if left is None or right is None:
            raise UnsupportedInteraction
        pairs.append(
            ExamNetQtiMatchPair(
                left_identifier=left.identifier,
                left_text=left.text,
                right_identifier=right.identifier,
                right_text=right.text,
            )
        )
    return item(
        root,
        sequence=sequence,
        interaction_type=ExamNetQtiInteractionType.MATCHING,
        prompt_paragraphs=prompt_paragraphs,
        image_resources=image_resources,
        max_score=max_score,
        match_left=match_left,
        match_right=match_right,
        match_pairs=tuple(pairs),
    )


def free_text_item(
    root: ElementTree.Element,
    *,
    declaration: ResponseDeclaration,
    prompt_paragraphs: tuple[ExamNetQtiPromptParagraph, ...],
    image_resources: tuple[ExamNetQtiImageResource, ...],
    max_score: int | float | None,
    sequence: int,
) -> ExamNetQtiItem:
    if declaration.mapping is None:
        return item(
            root,
            sequence=sequence,
            interaction_type=ExamNetQtiInteractionType.FREE_TEXT,
            prompt_paragraphs=prompt_paragraphs,
            image_resources=image_resources,
            max_score=max_score,
            evaluation_mode=ExamNetQtiEvaluationMode.MANUAL_UNKEYED,
            free_text_criterion_points=None,
        )
    if not declaration.mapping.entries:
        raise UnsupportedInteraction
    return item(
        root,
        sequence=sequence,
        interaction_type=ExamNetQtiInteractionType.FREE_TEXT,
        prompt_paragraphs=prompt_paragraphs,
        image_resources=image_resources,
        max_score=max_score,
        evaluation_mode=ExamNetQtiEvaluationMode.AUTOMATIC,
        free_text_criterion_points=number(declaration.mapping.entries[0].mapped_value),
    )


def choice(element: ElementTree.Element) -> ExamNetQtiChoice:
    body = read_text_paragraphs(element)
    return ExamNetQtiChoice(
        identifier=element.get("identifier") or "",
        text=plain_text(body),
        body=body,
    )


def _match_entry(element: ElementTree.Element) -> ExamNetQtiMatchEntry:
    body = read_text_paragraphs(element)
    return ExamNetQtiMatchEntry(
        identifier=element.get("identifier") or "",
        text=plain_text(body),
        body=body,
    )
