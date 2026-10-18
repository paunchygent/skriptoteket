"""Shared fixtures for the curated-apps handler tests."""

from __future__ import annotations

import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_merge import (
    ConversionProgress,
    first_conversion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_conversion_support import (
    choice,
    conversion_update,
    placeholder,
)


@pytest.fixture
def first() -> tuple[NativeExamDocument, ConversionProgress]:
    progress = ConversionProgress.from_question_ids(["q1", "q2", "q3"])
    merged = first_conversion(
        update=conversion_update(
            [
                ("q1", [choice("p1", "Fråga ett")]),
                ("q2", [placeholder("p2", "Källtext två")]),
                ("q3", [placeholder("p3", "Källtext tre")]),
            ],
            pending=("q2", "q3"),
        ),
        progress=progress,
    )
    return merged.document, merged.progress
