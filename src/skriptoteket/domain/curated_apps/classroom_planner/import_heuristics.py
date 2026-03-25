from __future__ import annotations

from skriptoteket.application.curated_apps.classroom_planner.import_contracts import (
    ClassListImportPreview,
)
from skriptoteket.protocols.classroom_planner_imports import ClassListHeuristicParserProtocol


class ClassListHeuristicParser(ClassListHeuristicParserProtocol):
    """Dummy parser implementation for PR-0133.

    To be fully implemented with heuristics in PR-0134.
    """

    def parse(
        self,
        *,
        file_name: str,
        text: str | None,
        rows: list[list[str]] | None,
    ) -> ClassListImportPreview:
        return ClassListImportPreview(
            file_name=file_name,
            suggested_class_name=None,
            parsed_students=[],
            ambiguous_rows=[],
        )
