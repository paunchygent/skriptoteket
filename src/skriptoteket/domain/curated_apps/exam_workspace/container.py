"""Exam workspace container content: one versioned Mina filer save unit.

A container carries exactly one native exam document revision plus the asset
payloads its items reference. The zip codec lives in infrastructure behind
``ExamWorkspaceContainerCodecProtocol``; this module owns the validated
content shape both sides exchange.
"""

from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)

EXAM_WORKSPACE_CONTAINER_SCHEMA_VERSION: Literal["exam_workspace_container_v1"] = (
    "exam_workspace_container_v1"
)


class ExamWorkspaceContainerContent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    document: NativeExamDocument
    assets_by_id: dict[str, bytes] = {}
    notes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _assets_match_document(self) -> "ExamWorkspaceContainerContent":
        declared = {asset.asset_id: asset for asset in self.document.assets}
        if set(self.assets_by_id) != set(declared):
            raise ValueError("container assets must match the document's asset list")
        for asset_id, payload in self.assets_by_id.items():
            asset = declared[asset_id]
            if len(payload) != asset.byte_length:
                raise ValueError(f"asset {asset_id} payload length mismatch")
            if hashlib.sha256(payload).hexdigest() != asset.sha256:
                raise ValueError(f"asset {asset_id} payload sha256 mismatch")
        return self
