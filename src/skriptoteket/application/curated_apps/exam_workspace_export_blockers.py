"""One shared export-gate verdict for exam workspace document responses.

``export_blockers`` is a plain field filled by the single ``mode="before"``
validator below, never a computed property: every ``computed_field`` form over
a property (bare, over ``cached_property``, or wrapping the getter) fails
mypy or the pydantic plugin unless a suppression comment is added, and such
suppressions are not allowed. A stored field keeps the JSON shape byte-identical
while type-checking cleanly.
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    NativeExportBlocker,
    native_export_blockers,
)


class NativeDocumentWithExportBlockers(BaseModel):
    """A native exam document plus the export gate's verdict on it."""

    model_config = ConfigDict(frozen=True)

    document: NativeExamDocument

    # The export gate's verdict on ``document``, derived on every response.
    export_blockers: tuple[NativeExportBlocker, ...] = ()

    @model_validator(mode="before")
    @classmethod
    def _fill_export_blockers(cls, data: dict[str, object] | Self) -> dict[str, object] | Self:
        if not isinstance(data, dict):
            return data
        document = data.get("document")
        if isinstance(document, dict):
            document = NativeExamDocument.model_validate(document)
        if not isinstance(document, NativeExamDocument):
            return data
        return {
            **data,
            "document": document,
            "export_blockers": native_export_blockers(document),
        }
