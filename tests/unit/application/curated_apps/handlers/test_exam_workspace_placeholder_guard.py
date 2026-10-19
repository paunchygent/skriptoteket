"""Conversion-placeholder guard: a step that changes a converting placeholder is refused (C2)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
    ExamWorkspaceConversionJobView,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_merge import (
    ConversionProgress,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_editor_content import (
    refuse_placeholder_changes,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.web.error_mapping import error_to_status
from tests.unit.application.curated_apps.handlers.exam_workspace_conversion_merge_test_support import (  # noqa: E501
    _teacher_save,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_conversion_support import (
    body,
)


def test_a_save_that_changes_a_placeholder_reports_the_conversion_refusal(
    first: tuple[NativeExamDocument, ConversionProgress],
) -> None:
    head, progress = first
    edited = head.items[1].model_copy(update={"body": body("Lärarens redigerade källtext")})
    saved = _teacher_save(head, items=(head.items[0], edited, head.items[2]))
    job = ExamWorkspaceConversionJobView(
        id=uuid4(),
        owner_user_id=uuid4(),
        source_kind=ExamAnswerKeySourceKind.WORKSPACE,
        status=ExamAnswerKeyEnrichmentJobStatus.RUNNING,
        workspace_lineage_id=head.document_id,
        last_error=None,
        conversion_progress=progress.model_dump(mode="json"),
    )

    with pytest.raises(DomainError) as refused:
        refuse_placeholder_changes(job=job, base=head, saved=saved)

    assert refused.value.code is ErrorCode.CONVERSION_IN_PROGRESS
    assert refused.value.message == (
        "Provet kunde inte sparas. Vänta tills frågorna har konverterats "
        "innan du ändrar, flyttar eller tar bort dem."
    )
    assert refused.value.details == {"item_ids": ["item_002"]}
    assert error_to_status(refused.value.code) == 422
