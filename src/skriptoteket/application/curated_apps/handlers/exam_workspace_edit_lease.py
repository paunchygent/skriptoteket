"""One editing tab per exam: the server edit lease next to the history head.

The holder claims the lease on open and renews it on heartbeat; a lease not
renewed for 15 s is dead and another tab may claim it. Every step store and
position move carries the tab id and is refused without a live lease. A waiting
tab records a takeover request, sees it answered when the holder releases, or
claims once the lease dies.
Relationships: the lease rows live on the history head row; the step store
reads the lease through ``require_edit_lease`` under the same lineage lock, so
a store and a release cannot race.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from skriptoteket.application.curated_apps.exam_workspace_history import (
    ExamWorkspaceEditLease,
    ExamWorkspaceEditLeaseResponse,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol

EDIT_LEASE_TTL_SECONDS = 15
"""A lease not renewed within this long is dead; another tab may claim it."""

EDIT_LEASE_HEARTBEAT_INTERVAL_SECONDS = 5
"""How often the holder renews the lease; the client's heartbeat cadence."""


def lease_is_live(*, lease: ExamWorkspaceEditLease | None, now: datetime) -> bool:
    """Whether a tab currently holds the lease: named, stamped, and fresh."""
    if lease is None or lease.holder_tab_id is None or lease.renewed_at is None:
        return False
    return (now - lease.renewed_at).total_seconds() < EDIT_LEASE_TTL_SECONDS


def require_edit_lease(
    *, lease: ExamWorkspaceEditLease | None, tab_id: UUID, now: datetime
) -> None:
    """Refuse a write from a tab that does not hold a live lease.

    The one shared guard: the step store and the position move call it, and the
    parent and change-type commands reach it through the step store.
    """
    if lease is None or lease.holder_tab_id != tab_id or not lease_is_live(lease=lease, now=now):
        raise DomainError(
            code=ErrorCode.EDIT_LEASE_HELD,
            message="Provet redigeras i en annan flik.",
            details={"tab_id": str(tab_id)},
        )


def _response(*, lease: ExamWorkspaceEditLease, tab_id: UUID) -> ExamWorkspaceEditLeaseResponse:
    return ExamWorkspaceEditLeaseResponse(
        holder_tab_id=lease.holder_tab_id,
        renewed_at=lease.renewed_at,
        takeover_requested_by=lease.takeover_requested_by,
        takeover_requested=lease.takeover_requested_by is not None
        and lease.takeover_requested_by != tab_id,
    )


class ExamWorkspaceEditLeaseHandler:
    """Claim, renew, request and release one exam's edit lease."""

    def __init__(
        self,
        *,
        vault_files: VaultFileRepositoryProtocol,
        store: ExamWorkspaceDocumentStore,
        clock: ClockProtocol,
    ) -> None:
        self._vault_files = vault_files
        self._store = store
        self._clock = clock

    async def _current(self, *, actor: User, lineage_id: UUID) -> ExamWorkspaceEditLease:
        head = await self._vault_files.get_document_head(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        if head is None:
            raise DomainError(code=ErrorCode.NOT_FOUND, message="Provdokumentet finns inte.")
        await self._store.ensure_history_head(actor=actor, lineage_id=lineage_id)
        lease = await self._vault_files.get_history_lease(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        return lease if lease is not None else ExamWorkspaceEditLease()

    async def claim(
        self, *, actor: User, lineage_id: UUID, tab_id: UUID
    ) -> ExamWorkspaceEditLeaseResponse:
        """Take the lease when none lives, or renew the tab's own; else refuse."""
        async with self._store.transaction(user_id=actor.id, lineage_id=lineage_id):
            await self._vault_files.lock_document_lineage(
                user_id=actor.id, document_lineage_id=lineage_id
            )
            lease = await self._current(actor=actor, lineage_id=lineage_id)
            now = self._clock.now()
            if lease_is_live(lease=lease, now=now) and lease.holder_tab_id != tab_id:
                require_edit_lease(lease=lease, tab_id=tab_id, now=now)
            updated = ExamWorkspaceEditLease(
                holder_tab_id=tab_id,
                renewed_at=now,
                takeover_requested_by=None
                if lease.takeover_requested_by == tab_id
                else lease.takeover_requested_by,
            )
            await self._vault_files.upsert_history_lease(
                user_id=actor.id, document_lineage_id=lineage_id, lease=updated
            )
            return _response(lease=updated, tab_id=tab_id)

    async def renew(
        self, *, actor: User, lineage_id: UUID, tab_id: UUID
    ) -> ExamWorkspaceEditLeaseResponse:
        """Refresh the holder's lease; report whether another tab waits for it."""
        async with self._store.transaction(user_id=actor.id, lineage_id=lineage_id):
            await self._vault_files.lock_document_lineage(
                user_id=actor.id, document_lineage_id=lineage_id
            )
            lease = await self._current(actor=actor, lineage_id=lineage_id)
            now = self._clock.now()
            require_edit_lease(lease=lease, tab_id=tab_id, now=now)
            updated = lease.model_copy(update={"renewed_at": now})
            await self._vault_files.upsert_history_lease(
                user_id=actor.id, document_lineage_id=lineage_id, lease=updated
            )
            return _response(lease=updated, tab_id=tab_id)

    async def request_takeover(
        self, *, actor: User, lineage_id: UUID, tab_id: UUID
    ) -> ExamWorkspaceEditLeaseResponse:
        """Record a waiting tab; the holder sees it at its next heartbeat."""
        async with self._store.transaction(user_id=actor.id, lineage_id=lineage_id):
            await self._vault_files.lock_document_lineage(
                user_id=actor.id, document_lineage_id=lineage_id
            )
            lease = await self._current(actor=actor, lineage_id=lineage_id)
            if lease.holder_tab_id == tab_id:
                return _response(lease=lease, tab_id=tab_id)
            updated = lease.model_copy(update={"takeover_requested_by": tab_id})
            await self._vault_files.upsert_history_lease(
                user_id=actor.id, document_lineage_id=lineage_id, lease=updated
            )
            return _response(lease=updated, tab_id=tab_id)

    async def release(
        self, *, actor: User, lineage_id: UUID, tab_id: UUID
    ) -> ExamWorkspaceEditLeaseResponse:
        """Clear the holder's lease; a waiting takeover claims it next."""
        async with self._store.transaction(user_id=actor.id, lineage_id=lineage_id):
            await self._vault_files.lock_document_lineage(
                user_id=actor.id, document_lineage_id=lineage_id
            )
            lease = await self._current(actor=actor, lineage_id=lineage_id)
            require_edit_lease(lease=lease, tab_id=tab_id, now=self._clock.now())
            updated = lease.model_copy(update={"holder_tab_id": None, "renewed_at": None})
            await self._vault_files.upsert_history_lease(
                user_id=actor.id, document_lineage_id=lineage_id, lease=updated
            )
            return _response(lease=updated, tab_id=tab_id)
