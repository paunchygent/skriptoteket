"""Deterministic recoverable-source repair helpers for DigiExam exports.

Purpose:
    Own the shared Swedish review messages, visible placeholders, and prompt
    image-position classification used by the parser, PDF renderer, and QTI
    adapter for recoverable `.dxe` source defects. These repairs are
    deterministic and provider-free.

Relationships:
    - Consumed by `domain.digiexam_embedded_assets`,
      `domain.digiexam_examnet_pdf_prompt`, and
      `domain.digiexam_examnet_qti_adapter`.
    - Carries no service, renderer, or provider coupling.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from html.parser import HTMLParser

MISSING_PROMPT_IMAGE_MESSAGE_TEMPLATE = (
    "Bilden i fråga {question_number} saknas. Lägg till den innan du använder provet."
)
PROMPT_IMAGE_PLACEHOLDER_LINE = "Bild saknas – lägg till bilden innan du använder provet."
PROMPT_IMAGE_PLACEHOLDER_HTML = (
    f'<span class="missing-image-placeholder">{PROMPT_IMAGE_PLACEHOLDER_LINE}</span>'
)

MISSING_QUESTION_TITLE_MESSAGE_TEMPLATE = (
    "Fråga {question_number} saknade titel. "
    "Titeln ”{fallback_title}” lades till automatiskt. "
    "Kontrollera titeln innan du använder provet."
)


def missing_prompt_image_message(*, question_number: int) -> str:
    """Return the canonical Swedish review message for one missing prompt image."""

    return MISSING_PROMPT_IMAGE_MESSAGE_TEMPLATE.format(question_number=question_number)


def missing_question_title_message(*, question_number: int, fallback_title: str) -> str:
    """Return the canonical Swedish review message for a generated title."""

    return MISSING_QUESTION_TITLE_MESSAGE_TEMPLATE.format(
        question_number=question_number, fallback_title=fallback_title
    )


@dataclass(frozen=True)
class PromptImagePosition:
    """One visible prompt image position with resolved binding state."""

    reference_index: int | None
    ambiguous: bool = False


def prompt_image_positions(prompt_html: str | None) -> tuple[PromptImagePosition, ...]:
    """Return every visible prompt image position of an item prompt.

    Positions come from real `img` elements of the parsed HTML; comments and
    attribute text never count. A position carries its decimal `data-image-id`
    index when the binding is singular and decimal, ``None`` when the element
    has no usable id, and the ``ambiguous`` flag when the element carries
    multiple or non-decimal bindings. This is the single interpretation shared
    by the parser, PDF renderer, and QTI adapter.
    """

    if prompt_html is None:
        return ()
    collector = _ImagePositionCollector()
    collector.feed(prompt_html)
    collector.close()
    return tuple(collector.positions)


class _ImagePositionCollector(HTMLParser):
    """Collect one `PromptImagePosition` per real `img` element."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.positions: list[PromptImagePosition] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "img":
            return
        bindings = [value for name, value in attrs if name.lower() == "data-image-id" and value]
        if len(bindings) == 1 and bindings[0].isdecimal():
            self.positions.append(PromptImagePosition(reference_index=int(bindings[0])))
        elif bindings:
            self.positions.append(PromptImagePosition(reference_index=None, ambiguous=True))
        else:
            self.positions.append(PromptImagePosition(reference_index=None))


def unresolved_prompt_image_positions(
    prompt_html: str | None,
    usable_image_indexes: Iterable[int],
) -> tuple[PromptImagePosition, ...]:
    """Return the visible prompt positions that cannot bind to a usable image."""

    usable = frozenset(usable_image_indexes)
    return tuple(
        position
        for position in prompt_image_positions(prompt_html)
        if not _is_bound_position(position, usable)
    )


def unresolved_prompt_image_position_count(
    prompt_html: str | None,
    usable_image_indexes: Iterable[int],
) -> int:
    """Return how many visible prompt positions carry no usable image."""

    return len(unresolved_prompt_image_positions(prompt_html, usable_image_indexes))


def _is_bound_position(position: PromptImagePosition, usable: frozenset[int]) -> bool:
    return (
        not position.ambiguous
        and position.reference_index is not None
        and position.reference_index in usable
    )
