"""Position-and-hash projections shared by the QTI round-trip tests.

The projections compare positions and payload hashes, never regenerated
identifiers, so an export/import pair can be compared without knowing the new
ids. They live here so the domain mapping test and the application round-trip
test project documents the same way.
"""

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import NativeGap
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text


def _body_text(body: tuple[NativeParagraph, ...]) -> str:
    return " ".join(body_plain_text(body).split())


def _body_projection(
    body: tuple[NativeParagraph, ...],
    sha_by_asset_id: dict[str, str],
) -> tuple[tuple[int | None, tuple[tuple[str, object], ...]], ...]:
    gap_position = 0
    paragraphs: list[tuple[int | None, tuple[tuple[str, object], ...]]] = []
    for paragraph in body:
        segments: list[tuple[str, object]] = []
        for segment in paragraph.segments:
            if isinstance(segment, NativeTextSegment):
                segments.append(("text", (segment.text, tuple(segment.marks))))
            elif isinstance(segment, NativeAssetSegment):
                segments.append(("asset", sha_by_asset_id[segment.asset_id]))
            else:
                segments.append(("gap", gap_position))
                gap_position += 1
        paragraphs.append((paragraph.heading_level, tuple(segments)))
    return tuple(paragraphs)


def _position(identifiers: list[str], identifier: str | None) -> int | None:
    return identifiers.index(identifier) if identifier is not None else None


def _positions(identifiers: list[str], selected: tuple[str, ...]) -> tuple[int, ...]:
    return tuple(identifiers.index(identifier) for identifier in selected)


def _gap_values(gap: NativeGap) -> tuple[str, ...]:
    values: list[str] = []
    for value in (*gap.accepted_values, *gap.automatic_values):
        stripped = value.strip()
        if stripped and stripped not in values:
            values.append(stripped)
    return tuple(values)


def _item_projection(
    item: NativeExamItem,
    sha_by_asset_id: dict[str, str],
) -> dict[str, object]:
    choice_ids = [choice.choice_id for choice in item.choices]
    placed_gaps = item.body_gaps()
    return {
        "kind": item.kind.value,
        "body": _body_projection(item.body, sha_by_asset_id),
        "points": item.points,
        "choices": tuple(_body_text(choice.body) for choice in item.choices),
        "correct": _positions(choice_ids, item.answer_key.correct_choice_ids),
        "gaps": tuple(_gap_values(gap) for gap in placed_gaps),
        "inline": tuple(
            (
                tuple(_body_text(option.body) for option in gap.options),
                _position([option.choice_id for option in gap.options], gap.correct_option_id),
            )
            for gap in placed_gaps
        ),
        "match_left": tuple(_body_text(entry.body) for entry in item.match_left),
        "match_right": tuple(_body_text(entry.body) for entry in item.match_right),
        "pairs": tuple(
            (
                [entry.left_id for entry in item.match_left].index(pair.left_id),
                [entry.right_id for entry in item.match_right].index(pair.right_id),
            )
            for pair in item.answer_key.match_pairs
        ),
        "tick_points": item.tick_points,
        "steps": tuple(_body_text(choice.body) for choice in item.choices),
        "print_order": _positions(choice_ids, item.print_order),
    }


def _document_projection(document: NativeExamDocument) -> dict[str, object]:
    sha_by_asset_id = {asset.asset_id: asset.sha256 for asset in document.assets}
    item_positions = {item.item_id: index for index, item in enumerate(document.items)}
    return {
        "items": tuple(_item_projection(item, sha_by_asset_id) for item in document.items),
        "parents": tuple(
            (
                _body_projection(parent.instruction, sha_by_asset_id),
                tuple(item_positions[item_id] for item_id in parent.item_ids),
            )
            for parent in document.parents
        ),
        "assets": tuple(sorted(sha_by_asset_id.values())),
    }
