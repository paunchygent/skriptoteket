"""Protocols for the exam workspace sign-in guest-draft handoff (P5)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Protocol
from uuid import UUID

from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceDocumentResponse
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.identity.models import User


class ExamGuestDraftHandoffRepositoryProtocol(Protocol):
    """Claim a guest draft once per owner, backed by the database primary key."""

    async def claim(
        self,
        *,
        owner_user_id: UUID,
        draft_id: UUID,
        lineage_id: UUID,
        now: datetime,
    ) -> bool:
        """Insert the ledger row; return True only when this call inserted it."""

    async def get_lineage(self, *, owner_user_id: UUID, draft_id: UUID) -> UUID | None:
        """Return the lineage the winning claim created, or None."""


class ImportGuestExamDraftHandlerProtocol(Protocol):
    """Save a guest's browser draft into Mina filer exactly once per (owner, draft)."""

    async def handle(
        self,
        *,
        actor: User,
        draft_id: UUID,
        document: NativeExamDocument,
        assets_by_id: Mapping[str, bytes],
    ) -> ExamWorkspaceDocumentResponse: ...
