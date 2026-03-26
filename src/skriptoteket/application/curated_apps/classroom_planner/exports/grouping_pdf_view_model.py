"""View models for classroom-planner grouping PDF exports.

Purpose:
    Project the shared grouping presentation contract into a renderer-friendly
    digital-handout model with deterministic left-right pairing, branded
    letterhead metadata, and a teacher-safe output filename.

Relationships:
    - Built from `GroupingExportPresentation` in the application layer.
    - Consumed by the classroom-planner grouping PDF renderer in
      `infrastructure.curated_apps.apps.classroom_planner`.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .grouping_presentation import GroupingExportPresentation


class GroupingPdfMemberRow(BaseModel):
    """Describe one ordered member row inside a rendered group card."""

    model_config = ConfigDict(frozen=True)

    member_order: int
    display_name: str


class GroupingPdfCard(BaseModel):
    """Describe one framed group card in the presentation handout."""

    model_config = ConfigDict(frozen=True)

    group_label: str
    members: tuple[GroupingPdfMemberRow, ...]


class GroupingPdfCardPair(BaseModel):
    """Describe one left-right card row in the rendered PDF."""

    model_config = ConfigDict(frozen=True)

    left_card: GroupingPdfCard
    right_card: GroupingPdfCard | None = None


class GroupingPdfViewModel(BaseModel):
    """Describe the full grouping PDF handout."""

    model_config = ConfigDict(frozen=True)

    title: str
    class_name: str
    generated_label: str
    output_filename: str
    card_pairs: tuple[GroupingPdfCardPair, ...]


def build_grouping_pdf_view_model(
    *,
    presentation: GroupingExportPresentation,
    generated_at: datetime,
) -> GroupingPdfViewModel:
    """Project grouping export data into a two-column PDF handout model."""

    cards = tuple(
        GroupingPdfCard(
            group_label=group.group_label,
            members=tuple(
                GroupingPdfMemberRow(
                    member_order=member.member_order,
                    display_name=member.display_name,
                )
                for member in group.members
            ),
        )
        for group in presentation.groups
    )
    card_pairs = tuple(
        GroupingPdfCardPair(
            left_card=cards[index],
            right_card=cards[index + 1] if index + 1 < len(cards) else None,
        )
        for index in range(0, len(cards), 2)
    )
    return GroupingPdfViewModel(
        title=presentation.title,
        class_name=presentation.class_name,
        generated_label=f"Skapad {generated_at.strftime('%Y-%m-%d %H:%M')}",
        output_filename=f"{presentation.filename_stem}-a4-portrait.pdf",
        card_pairs=card_pairs,
    )
