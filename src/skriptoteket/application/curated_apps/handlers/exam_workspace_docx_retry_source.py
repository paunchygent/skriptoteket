"""One-question retry source resolution (TASK-SKRIPT-39-05-09 D1).

Purpose:
    Anchor the retry in the saved revision's stored source: the saved document
    must exist and match the saved revision, the question must carry a retry
    source whose pictures the saved revision still holds, and the working
    item's retry history must extend the saved import facts with only
    teacher-request steps.

Relationships:
    Consumed by ``exam_workspace_docx_retry``; the retry source itself is
    read through ``native_exam_retry_source``.
"""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_import_record import (
    NativeExamRetryStep,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_records import (
    NativeExamRetrySource,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_source import (
    source_asset_ids,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error


def document_not_found(lineage_id: UUID) -> DomainError:
    return DomainError(
        code=ErrorCode.NOT_FOUND,
        message="Provdokumentet finns inte.",
        details={"lineage_id": str(lineage_id)},
    )


def missing_source_assets(
    source: NativeExamRetrySource,
    *,
    assets: tuple[NativeExamAsset, ...],
    payloads: Mapping[str, bytes],
) -> list[str]:
    """Source pictures whose saved manifest entry or container payload is gone."""
    referenced = set(source_asset_ids(source))
    declared = {asset.asset_id for asset in assets}
    return sorted(referenced - (declared & set(payloads)))


def validate_retry_history(original: NativeExamItem, draft_item: NativeExamItem) -> None:
    """Anchor import facts, but allow teacher retry history to branch after undo.

    Chosen type, answer-key origin and import type-conflict resends cannot change.
    Only the teacher-request tail is working state: it may predate or diverge from
    Spara, or include several unsaved attempts. Wording is copied from the saved
    record by ``_placed``, never trusted from the working document.
    """
    saved = original.import_record
    if saved is None:
        return
    import_end = next(
        (
            index
            for index, step in enumerate(saved.steps)
            if isinstance(step, NativeExamRetryStep) and step.reason == "teacher_request"
        ),
        len(saved.steps),
    )
    current = draft_item.import_record
    if (
        current is None
        or current.steps[:import_end] != saved.steps[:import_end]
        or any(
            not isinstance(step, NativeExamRetryStep) or step.reason != "teacher_request"
            for step in current.steps[import_end:]
        )
    ):
        raise validation_error(
            "Frågans konverteringshistorik stämmer inte med den sparade versionen.",
            details={"item_id": original.item_id},
        )
