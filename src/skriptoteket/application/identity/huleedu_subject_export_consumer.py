"""Apply HuleEdu subject exports to local identity projections.

Purpose:
    Create or update Skriptoteket-local users, roles, and realm-aware
    identity projections from a validated HuleEdu subject export.

Relationships:
    - Consumes models parsed by `huleedu_subject_export_contract`.
    - Depends only on repository protocols and `UnitOfWorkProtocol`.
    - Records projection audit events while keeping browser-session authority
      in HuleEdu.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.application.identity.huleedu_subject_export_contract import (
    DEFAULT_SUBJECT_ROLE_MATRIX,
    HuleEduSubjectExport,
    HuleEduSubjectExportRecord,
    build_subject_export_validation_error,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.domain.identity.projections import (
    IdentityProjection,
    IdentityProjectionEvent,
    IdentityProjectionEventType,
    ProductIdentityRealm,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import (
    IdentityProjectionEventRepositoryProtocol,
    IdentityProjectionRepositoryProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol

SUBJECT_EXPORT_CONSUME_RESULT_SCHEMA_VERSION = "skriptoteket-huleedu-export-consume-result-v1"

_ROLE_RANK: Mapping[Role, int] = {
    Role.USER: 0,
    Role.CONTRIBUTOR: 1,
    Role.ADMIN: 2,
    Role.SUPERUSER: 3,
}

type AccountAction = Literal["would_create", "would_update", "created", "updated", "unchanged"]


class HuleEduSubjectAccountResult(BaseModel):
    """Sanitized per-account result retained by the subject export consumer."""

    model_config = ConfigDict(frozen=True)

    stable_account_key: str
    email: str
    action: AccountAction
    role: Role
    product_identity_realm: ProductIdentityRealm
    realm_subject_id: str
    user_id: UUID | None = None
    projection_id: UUID | None = None


class HuleEduSubjectExportResult(BaseModel):
    """Sanitized command result for operator logs and retained artifacts."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = SUBJECT_EXPORT_CONSUME_RESULT_SCHEMA_VERSION
    status: Literal["ok"] = "ok"
    dry_run: bool
    processed: int
    created_users: int
    created_projections: int
    updated_users: int
    would_create_users: int
    would_create_projections: int
    would_update_users: int
    unchanged: int
    account_results: list[HuleEduSubjectAccountResult]


class HuleEduSubjectExportConsumer:
    """Apply a validated HuleEdu subject export to local identity state."""

    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        projections: IdentityProjectionRepositoryProtocol,
        projection_events: IdentityProjectionEventRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        role_matrix: Mapping[str, Role] | None = None,
    ) -> None:
        self._uow = uow
        self._users = users
        self._projections = projections
        self._projection_events = projection_events
        self._clock = clock
        self._id_generator = id_generator
        self._role_matrix = dict(role_matrix or DEFAULT_SUBJECT_ROLE_MATRIX)

    async def consume(
        self,
        *,
        export: HuleEduSubjectExport,
        dry_run: bool,
    ) -> HuleEduSubjectExportResult:
        """Create or update local users/projections for the subject role matrix."""
        results: list[HuleEduSubjectAccountResult] = []
        try:
            async with self._uow:
                for record in export.accounts:
                    result = await self._consume_record(record=record, dry_run=dry_run)
                    results.append(result)
        except _SubjectExportBlocked as exc:
            if not dry_run:
                await self._record_blocked_event(blocked=exc)
            raise exc.to_domain_error() from exc

        return HuleEduSubjectExportResult(
            dry_run=dry_run,
            processed=len(results),
            created_users=sum(1 for result in results if result.action == "created"),
            created_projections=sum(1 for result in results if result.action == "created"),
            updated_users=sum(1 for result in results if result.action == "updated"),
            would_create_users=sum(1 for result in results if result.action == "would_create"),
            would_create_projections=sum(
                1 for result in results if result.action == "would_create"
            ),
            would_update_users=sum(1 for result in results if result.action == "would_update"),
            unchanged=sum(1 for result in results if result.action == "unchanged"),
            account_results=results,
        )

    async def _consume_record(
        self,
        *,
        record: HuleEduSubjectExportRecord,
        dry_run: bool,
    ) -> HuleEduSubjectAccountResult:
        target_role = self._target_role(record=record)
        await self._projections.lock_realm_subject(
            product_identity_realm=record.projection_realm.value,
            realm_subject_id=record.realm_subject_id,
        )
        projection = await self._projections.get_by_realm_subject(
            product_identity_realm=record.projection_realm.value,
            realm_subject_id=record.realm_subject_id,
        )
        if projection is not None:
            return await self._consume_existing_projection(
                record=record,
                projection=projection,
                target_role=target_role,
                dry_run=dry_run,
            )

        await self._projections.lock_email(email=record.email)
        existing_user = await self._users.get_auth_by_email(record.email)
        if existing_user is not None:
            raise _SubjectExportBlocked(
                record=record,
                event_type=IdentityProjectionEventType.DUPLICATE_EMAIL_LINKING_REQUIRED,
                reason="identity_linking_required",
                message="HuleEdu subject export cannot be safely linked",
                field="email",
            )
        if dry_run:
            return self._result_for_record(record=record, action="would_create", role=target_role)

        return await self._create_user_projection(record=record, target_role=target_role)

    async def _consume_existing_projection(
        self,
        *,
        record: HuleEduSubjectExportRecord,
        projection: IdentityProjection,
        target_role: Role,
        dry_run: bool,
    ) -> HuleEduSubjectAccountResult:
        user = await self._users.get_by_id(projection.user_id)
        if user is None or not user.is_active:
            raise _SubjectExportBlocked(
                record=record,
                event_type=IdentityProjectionEventType.BLOCKED_PROVISIONING,
                reason="inactive_or_missing_local_user",
                message="HuleEdu subject export cannot be safely linked",
                user_id=user.id if user is not None else None,
                projection_id=projection.id,
            )
        if user.email != record.email:
            raise _SubjectExportBlocked(
                record=record,
                event_type=IdentityProjectionEventType.BLOCKED_PROVISIONING,
                reason="projection_email_mismatch",
                message="HuleEdu subject export cannot be safely linked",
                field="email",
                user_id=user.id,
                projection_id=projection.id,
            )
        if user.auth_provider is not AuthProvider.HULEEDU:
            raise _SubjectExportBlocked(
                record=record,
                event_type=IdentityProjectionEventType.BLOCKED_PROVISIONING,
                reason="local_password_owner_conflict",
                message="HuleEdu subject export cannot be safely linked",
                field="auth_provider",
                user_id=user.id,
                projection_id=projection.id,
            )

        next_role = _promoted_or_preserved_role(current=user.role, target=target_role)
        needs_update = next_role is not user.role or user.email_verified is not True
        if dry_run:
            action: AccountAction = "would_update" if needs_update else "unchanged"
            return self._result_for_record(
                record=record,
                action=action,
                role=next_role,
                user_id=user.id,
                projection_id=projection.id,
            )
        if not needs_update:
            await self._record_event(
                record=record,
                event_type=IdentityProjectionEventType.RESOLVED,
                reason_code="subject_export_projection_unchanged",
                user_id=user.id,
                projection_id=projection.id,
            )
            return self._result_for_record(
                record=record,
                action="unchanged",
                role=user.role,
                user_id=user.id,
                projection_id=projection.id,
            )

        now = self._clock.now()
        updated_user = await self._users.update(
            user=user.model_copy(
                update={
                    "role": next_role,
                    "email_verified": True,
                    "updated_at": now,
                }
            )
        )
        await self._record_event(
            record=record,
            event_type=IdentityProjectionEventType.RESOLVED,
            reason_code="subject_export_user_updated",
            user_id=updated_user.id,
            projection_id=projection.id,
        )
        return self._result_for_record(
            record=record,
            action="updated",
            role=updated_user.role,
            user_id=updated_user.id,
            projection_id=projection.id,
        )

    async def _create_user_projection(
        self,
        *,
        record: HuleEduSubjectExportRecord,
        target_role: Role,
    ) -> HuleEduSubjectAccountResult:
        now = self._clock.now()
        user = await self._users.create_if_email_available(
            user=User(
                id=self._id_generator.new_uuid(),
                email=record.email,
                role=target_role,
                auth_provider=AuthProvider.HULEEDU,
                is_active=True,
                email_verified=True,
                failed_login_attempts=0,
                locked_until=None,
                last_login_at=None,
                last_failed_login_at=None,
                created_at=now,
                updated_at=now,
            ),
            password_hash=None,
        )
        if user is None:
            raise _SubjectExportBlocked(
                record=record,
                event_type=IdentityProjectionEventType.DUPLICATE_EMAIL_LINKING_REQUIRED,
                reason="identity_linking_required",
                message="HuleEdu subject export cannot be safely linked",
                field="email",
            )

        projection = await self._projections.create_if_realm_subject_absent(
            projection=IdentityProjection(
                id=self._id_generator.new_uuid(),
                user_id=user.id,
                product_identity_realm=record.projection_realm,
                realm_subject_id=record.realm_subject_id,
                created_at=now,
                updated_at=now,
            )
        )
        if projection is None:
            raise _SubjectExportBlocked(
                record=record,
                event_type=IdentityProjectionEventType.BLOCKED_PROVISIONING,
                reason="projection_conflict_unresolved",
                message="HuleEdu subject export cannot be safely linked",
                field="realm_subject_id",
            )

        await self._record_event(
            record=record,
            event_type=IdentityProjectionEventType.PROVISIONED,
            reason_code="subject_export_projection_created",
            user_id=user.id,
            projection_id=projection.id,
        )
        return self._result_for_record(
            record=record,
            action="created",
            role=user.role,
            user_id=user.id,
            projection_id=projection.id,
        )

    async def _record_event(
        self,
        *,
        record: HuleEduSubjectExportRecord,
        event_type: IdentityProjectionEventType,
        reason_code: str,
        user_id: UUID,
        projection_id: UUID,
    ) -> None:
        await self._projection_events.create(
            event=IdentityProjectionEvent(
                id=self._id_generator.new_uuid(),
                event_type=event_type,
                user_id=user_id,
                projection_id=projection_id,
                product_identity_realm=record.projection_realm,
                realm_subject_id=record.realm_subject_id,
                reason_code=reason_code,
                correlation_id=None,
                context_jti=None,
                created_at=self._clock.now(),
            )
        )

    async def _record_blocked_event(self, *, blocked: "_SubjectExportBlocked") -> None:
        async with self._uow:
            await self._projection_events.create(
                event=IdentityProjectionEvent(
                    id=self._id_generator.new_uuid(),
                    event_type=blocked.event_type,
                    user_id=blocked.user_id,
                    projection_id=blocked.projection_id,
                    product_identity_realm=blocked.record.projection_realm,
                    realm_subject_id=blocked.record.realm_subject_id,
                    reason_code=blocked.reason,
                    correlation_id=None,
                    context_jti=None,
                    created_at=self._clock.now(),
                )
            )

    def _target_role(self, *, record: HuleEduSubjectExportRecord) -> Role:
        target_role = self._role_matrix.get(record.stable_account_key)
        if target_role is None:
            raise build_subject_export_validation_error(
                "unsupported_stable_account_key",
                field="stable_account_key",
                stable_account_key=record.stable_account_key,
            )
        if record.skriptoteket_role_hint != target_role.value:
            raise build_subject_export_validation_error(
                "role_hint_matrix_mismatch",
                field="skriptoteket_role_hint",
                stable_account_key=record.stable_account_key,
            )
        return target_role

    def _result_for_record(
        self,
        *,
        record: HuleEduSubjectExportRecord,
        action: AccountAction,
        role: Role,
        user_id: UUID | None = None,
        projection_id: UUID | None = None,
    ) -> HuleEduSubjectAccountResult:
        return HuleEduSubjectAccountResult(
            stable_account_key=record.stable_account_key,
            email=record.email,
            action=action,
            role=role,
            product_identity_realm=record.projection_realm,
            realm_subject_id=record.realm_subject_id,
            user_id=user_id,
            projection_id=projection_id,
        )


def _promoted_or_preserved_role(*, current: Role, target: Role) -> Role:
    if _ROLE_RANK[target] > _ROLE_RANK[current]:
        return target
    return current


class _SubjectExportBlocked(Exception):
    """Internal signal for blocked mappings that need durable audit before failing."""

    def __init__(
        self,
        *,
        record: HuleEduSubjectExportRecord,
        event_type: IdentityProjectionEventType,
        reason: str,
        message: str,
        field: str | None = None,
        user_id: UUID | None = None,
        projection_id: UUID | None = None,
    ) -> None:
        super().__init__(reason)
        self.record = record
        self.event_type = event_type
        self.reason = reason
        self.message = message
        self.field = field
        self.user_id = user_id
        self.projection_id = projection_id

    def to_domain_error(self) -> DomainError:
        """Return the sanitized operator-facing conflict after audit is persisted."""
        details: dict[str, object] = {
            "reason": self.reason,
            "stable_account_key": self.record.stable_account_key,
        }
        if self.field is not None:
            details["field"] = self.field
        return DomainError(
            code=ErrorCode.CONFLICT,
            message=self.message,
            details=details,
        )
