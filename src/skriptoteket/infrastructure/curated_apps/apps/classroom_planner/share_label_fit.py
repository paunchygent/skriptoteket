"""Deterministic seating-label fit rules for Klassrumskartan share pages.

Purpose:
    Convert full student labels into static, CSS-owned visible lines and fit
    tiers before immutable seating share HTML is persisted.

Relationships:
    - Used by `share_scene_renderer.py` for public seating share artifacts.
    - Keeps long-name support independent of browser JavaScript measurement.
    - Preserves the caller-provided full label for accessible/title text.
"""

from __future__ import annotations

from dataclasses import dataclass

_DENSE_SCORE_LIMIT = 11.5
_ULTRA_SCORE_LIMIT = 17.0

_NARROW_CHARS = frozenset("ijlIrtf")
_WIDE_CHARS = frozenset("mwMW@")
_EXTRA_WIDE_CHARS = frozenset("ÅÄÖ")


@dataclass(frozen=True, slots=True)
class SeatLabelPresentation:
    """Describe the visible student label and renderer fit state."""

    visible_lines: tuple[str, ...]
    css_classes: tuple[str, ...]
    is_fallback: bool


def build_seat_label_presentation(value: str) -> SeatLabelPresentation:
    """Return static visible lines and CSS classes for one full student label.

    Args:
        value: Full label from the prepared seating scene.

    Returns:
        A deterministic presentation with one or two visible lines. Supported
        name parts are kept in full; over-budget parts fall back to initials.
    """

    words = [word for word in value.split() if word]
    if not words:
        return SeatLabelPresentation(
            visible_lines=(value,),
            css_classes=("room-seat--name-compact",),
            is_fallback=False,
        )

    first_part = _fit_name_part(words[0])
    if len(words) == 1:
        return SeatLabelPresentation(
            visible_lines=(first_part.text,),
            css_classes=first_part.css_classes,
            is_fallback=first_part.is_fallback,
        )

    surname_part = _fit_name_part(" ".join(words[1:]))
    classes = {first_part.tier_class, surname_part.tier_class}
    if first_part.is_fallback or surname_part.is_fallback:
        classes.add("room-seat--name-fallback")
    return SeatLabelPresentation(
        visible_lines=(first_part.text, surname_part.text),
        css_classes=tuple(sorted(classes)),
        is_fallback=first_part.is_fallback or surname_part.is_fallback,
    )


@dataclass(frozen=True, slots=True)
class _FittedNamePart:
    """Describe one visible name part after applying the width budget."""

    text: str
    tier_class: str
    is_fallback: bool

    @property
    def css_classes(self) -> tuple[str, ...]:
        """Return the CSS classes needed when this is the only visible line."""

        if self.is_fallback:
            return ("room-seat--name-fallback",)
        return (self.tier_class,)


def _fit_name_part(value: str) -> _FittedNamePart:
    """Return a full supported name part or a deterministic initial fallback."""

    score = _visible_width_score(value)
    if score <= _ULTRA_SCORE_LIMIT:
        return _FittedNamePart(
            text=value,
            tier_class=_tier_class(score),
            is_fallback=False,
        )

    initial = value[0].upper() if value else ""
    return _FittedNamePart(
        text=f"{initial}.",
        tier_class="room-seat--name-fallback",
        is_fallback=True,
    )


def _tier_class(score: float) -> str:
    """Return the CSS tier for a supported visible-line width score."""

    if score <= 8.0:
        return "room-seat--name-compact"
    if score <= _DENSE_SCORE_LIMIT:
        return "room-seat--name-dense"
    return "room-seat--name-ultra"


def _visible_width_score(value: str) -> float:
    """Return a conservative static approximation of rendered text width."""

    return sum(_character_width_score(character) for character in value)


def _character_width_score(character: str) -> float:
    """Return the static width weight for one visible label character."""

    if character.isspace():
        return 0.45
    if character in "-–":
        return 0.55
    if character in _NARROW_CHARS:
        return 0.58
    if character in _EXTRA_WIDE_CHARS:
        return 1.35
    if character in _WIDE_CHARS:
        return 1.42
    if character.isupper():
        return 1.15
    if character.isdigit():
        return 0.9
    if character in ".,'":
        return 0.35
    return 1.0
