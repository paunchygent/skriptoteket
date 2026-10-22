"""Shared primitives for Exam.net QTI item readers.

Responsibility: interaction sets, refusal markers, prompt text helpers, image
resolution and tag-name helpers used by every item-reader module.
"""

from __future__ import annotations

import posixpath
from collections.abc import Mapping
from typing import Literal
from xml.etree import ElementTree

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_body_reader import (
    paragraphs_plain_text,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiEvaluationMode,
    ExamNetQtiImageResource,
    ExamNetQtiInlineChoiceGap,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiMatchEntry,
    ExamNetQtiMatchPair,
    ExamNetQtiPromptParagraph,
    ExamNetQtiTextEntryGap,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import (
    qti_tag,
)

BLOCK_INTERACTIONS = frozenset(
    {
        qti_tag("qti-choice-interaction"),
        qti_tag("qti-order-interaction"),
        qti_tag("qti-match-interaction"),
        qti_tag("qti-extended-text-interaction"),
    }
)


SEPARATOR = qti_tag("qti-gap-match-interaction")


GAP_INTERACTIONS = frozenset(
    {
        qti_tag("qti-text-entry-interaction"),
        qti_tag("qti-inline-choice-interaction"),
    }
)


_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


_JPEG_SIGNATURE = b"\xff\xd8\xff"


OPENING_TEXT_LIMIT = 200


class UnsupportedInteraction(Exception):
    """Raised when the item's structure is outside the supported standalone shapes."""


class UnsupportedImage(Exception):
    """Raised when one image cannot be resolved to a supported package payload."""


def item(
    root: ElementTree.Element,
    *,
    sequence: int,
    interaction_type: ExamNetQtiInteractionType,
    prompt_paragraphs: tuple[ExamNetQtiPromptParagraph, ...],
    image_resources: tuple[ExamNetQtiImageResource, ...],
    max_score: int | float | None,
    evaluation_mode: ExamNetQtiEvaluationMode = ExamNetQtiEvaluationMode.AUTOMATIC,
    free_text_criterion_points: int | float | None = None,
    choices: tuple[ExamNetQtiChoice, ...] = (),
    correct_choice_identifiers: tuple[str, ...] = (),
    text_entry_gaps: tuple[ExamNetQtiTextEntryGap, ...] = (),
    inline_choice_gaps: tuple[ExamNetQtiInlineChoiceGap, ...] = (),
    match_pairs: tuple[ExamNetQtiMatchPair, ...] = (),
    match_left: tuple[ExamNetQtiMatchEntry, ...] = (),
    match_right: tuple[ExamNetQtiMatchEntry, ...] = (),
) -> ExamNetQtiItem:
    return ExamNetQtiItem(
        item_id=root.get("identifier") or "",
        sequence=sequence,
        title=root.get("title") or "",
        interaction_type=interaction_type,
        prompt_lines=prompt_lines(prompt_paragraphs),
        max_score=max_score,
        prompt_paragraphs=prompt_paragraphs,
        evaluation_mode=evaluation_mode,
        free_text_criterion_points=free_text_criterion_points,
        choices=choices,
        correct_choice_identifiers=correct_choice_identifiers,
        text_entry_gaps=text_entry_gaps,
        inline_choice_gaps=inline_choice_gaps,
        match_pairs=match_pairs,
        match_left=match_left,
        match_right=match_right,
        image_resources=image_resources,
    )


def prompt_lines(paragraphs: tuple[ExamNetQtiPromptParagraph, ...]) -> tuple[str, ...]:
    return tuple(line for line in paragraphs_plain_text(paragraphs).splitlines() if line.strip())


def plain_text(paragraphs: tuple[ExamNetQtiPromptParagraph, ...]) -> str:
    return " ".join(paragraphs_plain_text(paragraphs).split())


def image_resources(
    elements: tuple[ElementTree.Element, ...],
    *,
    item_path: str,
    files: Mapping[str, bytes],
) -> tuple[ExamNetQtiImageResource, ...]:
    base_dir = posixpath.dirname(item_path)
    resources: list[ExamNetQtiImageResource] = []
    for number, element in enumerate(elements, start=1):
        source = element.get("src")
        if not source:
            raise UnsupportedImage
        path = posixpath.normpath(posixpath.join(base_dir, source))
        payload = files.get(path)
        if payload is None:
            raise UnsupportedImage
        media_type = picture_media_type(payload)
        if media_type is None:
            raise UnsupportedImage
        resources.append(
            ExamNetQtiImageResource(
                asset_id=f"image_{number:03d}",
                filename=posixpath.basename(path),
                media_type=media_type,
                payload=payload,
                alt_text=element.get("alt", ""),
                source_reference=path,
            )
        )
    return tuple(resources)


def picture_media_type(payload: bytes) -> Literal["image/png", "image/jpeg"] | None:
    """The picture media type its leading bytes name: PNG or JPEG, else None."""
    if payload.startswith(_PNG_SIGNATURE):
        return "image/png"
    if payload.startswith(_JPEG_SIGNATURE):
        return "image/jpeg"
    return None


def local_name(tag: str) -> str:
    if not tag.startswith("{"):
        return tag
    return tag.rsplit("}", 1)[-1]
