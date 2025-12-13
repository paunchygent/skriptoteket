from __future__ import annotations

import pytest

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.identity.role_guards import (
    require_any_role,
    require_at_least_role,
    require_can_provision_local_user,
)
from tests.fixtures.identity_fixtures import make_user


def test_require_any_role_allows_when_role_present() -> None:
    user = make_user(role=Role.ADMIN)
    require_any_role(user=user, roles={Role.ADMIN, Role.SUPERUSER})


def test_require_any_role_raises_for_missing_role() -> None:
    user = make_user(role=Role.USER)
    with pytest.raises(DomainError) as exc_info:
        require_any_role(user=user, roles={Role.ADMIN})

    assert exc_info.value.code == ErrorCode.FORBIDDEN


def test_require_at_least_role_compares_hierarchy() -> None:
    user = make_user(role=Role.ADMIN)
    require_at_least_role(user=user, role=Role.CONTRIBUTOR)

    with pytest.raises(DomainError) as exc_info:
        require_at_least_role(user=user, role=Role.SUPERUSER)

    assert exc_info.value.code == ErrorCode.FORBIDDEN


def test_require_can_provision_local_user_enforces_policy() -> None:
    admin = make_user(role=Role.ADMIN)
    require_can_provision_local_user(actor=admin, target_role=Role.USER)

    with pytest.raises(DomainError) as exc_info:
        require_can_provision_local_user(actor=admin, target_role=Role.ADMIN)

    assert exc_info.value.code == ErrorCode.FORBIDDEN
