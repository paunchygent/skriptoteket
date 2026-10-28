"""Progress port for type-batched DOCX conversion (TASK-SKRIPT-39-05-04 D25, D30).

Purpose:
    The conversion pipeline reports the question outline once grouping is known,
    each admitted batch as a provisional whole document, and finally publishes
    the finished document through the same port. Every call carries the claim's
    ``worker_id`` so the implementation fences its writes like the job handler.

Relationships:
    The pipeline in ``application.curated_apps.handlers.exam_workspace_docx_pipeline``
    calls the port; it never calls two port methods at once and never while a token
    lease transaction runs, so an implementation may use the request unit of work.
    Calls may repeat after a lease-expiry reclaim; an implementation treats a repeat
    for an already-filled question as a no-op. The phase marks which step of the import
    the job is in (TASK-SKRIPT-39-04-23 D1).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol
from uuid import UUID

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.identity.models import User


class ConversionPhase(StrEnum):
    """The step of an import a job is in: reading the file, finding the questions,
    sorting them by type (first-pass labelling), converting them."""

    READING = "reading"
    FINDING = "finding"
    SORTING = "sorting"
    CONVERTING = "converting"


@dataclass(frozen=True)
class OutlineQuestion:
    """One grouped question in source order, before conversion."""

    question_id: str
    position: int
    anchors: tuple[str, ...]
    source_text: str


@dataclass(frozen=True)
class ConversionOutline:
    """The grouped questions of one exam; their placeholders show until batches fill them."""

    title: str | None
    questions: tuple[OutlineQuestion, ...]


@dataclass(frozen=True)
class ConversionUpdate:
    """A provisional (or, with no pending question, final) whole document in source order.

    ``item_ids`` maps every outline question to its items in ``document``: converted items
    for a filled question, the placeholder item for a pending one. ``extra_item_ids`` are
    review items for source chunks no question owns. ``parent_ids`` maps a question to the
    parent it sits under. ``assets_by_id`` carries the payloads of every picture the
    document references, so a provisional save writes them beside the revision.
    """

    filled: tuple[str, ...]
    pending: tuple[str, ...]
    document: NativeExamDocument
    item_ids: Mapping[str, tuple[str, ...]]
    extra_item_ids: tuple[str, ...]
    parent_ids: Mapping[str, str]
    assets_by_id: Mapping[str, bytes] = MappingProxyType({})


class DocxConversionProgressProtocol(Protocol):
    """Deliver converted batches before the whole document is done, then publish it."""

    async def phase(self, *, worker_id: str, job_id: UUID, phase: ConversionPhase) -> None:
        """Called once as each phase starts: one small write per phase change. A repeat
        after a lease-expiry reclaim overwrites the phase with the new worker's start time."""
        ...

    async def outline(self, *, worker_id: str, job_id: UUID, outline: ConversionOutline) -> None:
        """Called once, after grouping and before any conversion."""
        ...

    async def received(
        self, *, worker_id: str, job_id: UUID, question_ids: tuple[str, ...]
    ) -> None:
        """Record question-output receipt after outline, independently of saved results.

        Repeated identities leave receipt set; this does not publish a revision or make
        a question editable. The pipeline serializes this write with other port calls.
        """
        ...

    async def batch_ready(
        self,
        *,
        worker_id: str,
        job_id: UUID,
        update: ConversionUpdate,
        notes: tuple[str, ...],
    ) -> None:
        """Called after each admitted batch, in admission order.

        ``notes`` holds the reader's import notes; the first saved revision carries them, so
        an import that keeps its published batches after a failure still names them.
        """
        ...

    async def publish_final(
        self,
        *,
        worker_id: str,
        job_id: UUID,
        lineage_id: UUID,
        actor: User,
        file_id: UUID,
        update: ConversionUpdate,
        notes: tuple[str, ...],
    ) -> None:
        """Save the final document inside the caller's fenced unit of work.

        The caller owns ``file_id`` and discards that vault file when its transaction fails.
        """
        ...

    async def abandon(self, *, worker_id: str, job_id: UUID, reason: str) -> None:
        """Called inside the caller's fenced unit of work when the job fails after conversion
        started; placeholders a teacher has not changed become review items with ``reason``."""
        ...
