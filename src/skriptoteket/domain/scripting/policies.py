from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.scripting.models import ToolVersion, VersionState


def _is_derived_from_actor(
    *,
    actor_id: UUID,
    version: ToolVersion,
    versions_by_id: dict[UUID, ToolVersion],
) -> bool:
    current = version
    visited: set[UUID] = set()
    while current.derived_from_version_id is not None:
        parent_id = current.derived_from_version_id
        if parent_id in visited:
            return False
        visited.add(parent_id)

        parent = versions_by_id.get(parent_id)
        if parent is None:
            return False
        if parent.created_by_user_id == actor_id:
            return True
        current = parent
    return False


def can_view_version(
    *,
    actor: User,
    version: ToolVersion,
    versions: Iterable[ToolVersion],
) -> bool:
    if actor.role in {Role.ADMIN, Role.SUPERUSER}:
        return True

    if actor.role is not Role.CONTRIBUTOR:
        return False

    if version.created_by_user_id == actor.id:
        return True

    if version.state not in {VersionState.ACTIVE, VersionState.ARCHIVED}:
        return False

    versions_by_id = {candidate.id: candidate for candidate in versions}
    return _is_derived_from_actor(actor_id=actor.id, version=version, versions_by_id=versions_by_id)


def require_can_view_version(
    *,
    actor: User,
    version: ToolVersion,
    versions: Iterable[ToolVersion],
) -> None:
    if can_view_version(actor=actor, version=version, versions=versions):
        return
    raise DomainError(
        code=ErrorCode.FORBIDDEN,
        message="Insufficient permissions",
        details={
            "actor_user_id": str(actor.id),
            "actor_role": actor.role.value,
            "tool_id": str(version.tool_id),
            "version_id": str(version.id),
            "version_state": version.state.value,
        },
    )


def visible_versions_for_actor(
    *,
    actor: User,
    versions: Iterable[ToolVersion],
) -> list[ToolVersion]:
    versions_list = list(versions)
    if actor.role in {Role.ADMIN, Role.SUPERUSER}:
        return versions_list
    if actor.role is not Role.CONTRIBUTOR:
        return []

    versions_by_id = {version.id: version for version in versions_list}
    visible: list[ToolVersion] = []
    for version in versions_list:
        if version.created_by_user_id == actor.id:
            visible.append(version)
            continue
        if version.state in {VersionState.ACTIVE, VersionState.ARCHIVED} and _is_derived_from_actor(
            actor_id=actor.id,
            version=version,
            versions_by_id=versions_by_id,
        ):
            visible.append(version)
    return visible

