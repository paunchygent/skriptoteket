from __future__ import annotations

from collections.abc import Collection

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role, User

_ROLE_RANK: dict[Role, int] = {
    Role.USER: 0,
    Role.CONTRIBUTOR: 1,
    Role.ADMIN: 2,
    Role.SUPERUSER: 3,
}


def has_any_role(*, user: User, roles: Collection[Role]) -> bool:
    return user.role in roles


def require_any_role(*, user: User, roles: Collection[Role]) -> None:
    if has_any_role(user=user, roles=roles):
        return
    raise DomainError(
        code=ErrorCode.FORBIDDEN,
        message="Insufficient permissions",
        details={
            "required_roles": [role.value for role in roles],
            "actual_role": user.role.value,
        },
    )


def has_at_least_role(*, user: User, role: Role) -> bool:
    return _ROLE_RANK[user.role] >= _ROLE_RANK[role]


def require_at_least_role(*, user: User, role: Role) -> None:
    if has_at_least_role(user=user, role=role):
        return
    raise DomainError(
        code=ErrorCode.FORBIDDEN,
        message="Insufficient permissions",
        details={"required_role": role.value, "actual_role": user.role.value},
    )


def can_provision_local_user(*, actor: User, target_role: Role) -> bool:
    if actor.role is Role.SUPERUSER:
        return True
    if actor.role is Role.ADMIN:
        return target_role in {Role.USER, Role.CONTRIBUTOR}
    return False


def require_can_provision_local_user(*, actor: User, target_role: Role) -> None:
    if can_provision_local_user(actor=actor, target_role=target_role):
        return
    raise DomainError(
        code=ErrorCode.FORBIDDEN,
        message="Insufficient permissions",
        details={
            "required_roles": [Role.ADMIN.value, Role.SUPERUSER.value],
            "target_role": target_role.value,
            "actor_role": actor.role.value,
        },
    )
