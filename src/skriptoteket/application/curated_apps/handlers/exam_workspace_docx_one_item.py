"""A grouped question is admitted as one item (TASK-SKRIPT-39-04-12 C3).

A reply that spreads one question's body over several entries, or puts the bodies of several
questions in one entry, converts none of those questions: each becomes its source review item,
which the teacher reconverts through the single-question retry.
"""

from collections import Counter

from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_lines import line_points
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    POINT_LABEL,
    QUESTION_HEADING_LABEL,
)

SPLIT_QUESTION_REASON = (
    "AI-tolkningen delade frågan i flera frågor. Kontrollera frågan och konvertera den igen."
)
MERGED_QUESTIONS_REASON = (
    "AI-tolkningen slog ihop frågan med en annan fråga. Kontrollera frågan och konvertera den igen."
)
_REASONS = {"question_split": SPLIT_QUESTION_REASON, "questions_merged": MERGED_QUESTIONS_REASON}


def raw_anchors(raw: JsonValue) -> tuple[str, ...]:
    """The string anchors a reply entry lists, whether or not the entry is valid."""
    anchors = raw.get("source_anchors") if isinstance(raw, dict) else None
    return tuple(a for a in anchors if isinstance(a, str)) if isinstance(anchors, list) else ()


def _label_line(anchor: str, state: DocxBuildState) -> bool:
    """A question's heading or points line, which joins the entry holding its body."""
    chunk = state.chunk_by_anchor[anchor]
    return line_points(chunk) is not None or (
        chunk.kind == "heading"
        and anchor not in state.header_anchors
        and bool(QUESTION_HEADING_LABEL.match(chunk.text) or POINT_LABEL.search(chunk.text))
    )


def refused_questions(items: list[JsonValue], state: DocxBuildState) -> dict[tuple[str, ...], str]:
    """The grouped questions this reply does not return as one item each, in source order,
    with the admission event code that names why.

    An entry touches every question one of its anchors belongs to, heading and points lines
    included; the questions one entry touches are merged. ``state.question_by_anchor`` is the
    one owner of every anchor, as admission and assembly read it: the normalised manifest
    already gives each line that prints a total to its owner (``assign_points_lines``). An
    entry that touches one question holds its body unless it lists only the question's heading
    and points lines, which the admission joins to the body. A question whose body several
    entries hold is split.
    """
    owner = state.question_by_anchor
    holders: Counter[tuple[str, ...]] = Counter()
    refused: dict[tuple[str, ...], str] = {}
    for raw in items:
        owned = [a for a in raw_anchors(raw) if a in owner]
        touched = {owner[a] for a in owned}
        if len(touched) > 1:
            refused.update((question, "questions_merged") for question in touched)
        elif not all(_label_line(a, state) for a in owned):
            holders.update(touched)
    for question, count in holders.items():
        if count > 1:
            refused.setdefault(question, "question_split")
    return {q: refused[q] for q in state.questions if q in refused}


def refuse_questions(
    refused: dict[tuple[str, ...], str], state: DocxBuildState, seen: set[str]
) -> None:
    """Each refused question becomes one review item showing its source as printed."""
    for question, code in refused.items():
        own = tuple(c.anchor for c in state.pending if c.anchor in question)
        if not own:
            continue
        state.record("admission", code, anchors=own)
        seen.update(own)
        state.accepted.append(state.printed(own, _REASONS[code], seen))
