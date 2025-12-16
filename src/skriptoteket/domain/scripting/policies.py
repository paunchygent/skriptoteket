from __future__ import annotations

from collections.abc import Iterable

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.scripting.models import ToolVersion, VersionState


def can_access_tool(*, actor: User, is_tool_maintainer: bool) -> bool:
    if actor.role in {Role.ADMIN, Role.SUPERUSER}:
        return True
    if actor.role is Role.CONTRIBUTOR:
        return is_tool_maintainer
    return False


def require_can_access_tool(*, actor: User, tool_id: str, is_tool_maintainer: bool) -> None:
    if can_access_tool(actor=actor, is_tool_maintainer=is_tool_maintainer):
        return
    raise DomainError(
        code=ErrorCode.FORBIDDEN,
        message="Insufficient permissions",
        details={
            "actor_user_id": str(actor.id),
            "actor_role": actor.role.value,
            "tool_id": tool_id,
        },
    )


def can_view_version(*, actor: User, version: ToolVersion, is_tool_maintainer: bool) -> bool:
    if actor.role in {Role.ADMIN, Role.SUPERUSER}:
        return True
    if actor.role is not Role.CONTRIBUTOR or not is_tool_maintainer:
        return False

    if version.state in {VersionState.ACTIVE, VersionState.ARCHIVED}:
        return True
    return version.created_by_user_id == actor.id


def require_can_view_version(
    *,
    actor: User,
    version: ToolVersion,
    is_tool_maintainer: bool,
) -> None:
    if can_view_version(actor=actor, version=version, is_tool_maintainer=is_tool_maintainer):
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
    is_tool_maintainer: bool,
) -> list[ToolVersion]:
    versions_list = list(versions)
    if actor.role in {Role.ADMIN, Role.SUPERUSER}:
        return versions_list
    if actor.role is not Role.CONTRIBUTOR:
        return []

    if not is_tool_maintainer:
        return []

    return [
        version
        for version in versions_list
        if can_view_version(actor=actor, version=version, is_tool_maintainer=is_tool_maintainer)
    ]
