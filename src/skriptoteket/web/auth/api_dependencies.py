from fastapi import Depends, Header

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role, Session, User
from skriptoteket.domain.identity.role_guards import require_any_role, require_at_least_role
from skriptoteket.web.auth.dependencies import get_current_session, get_current_user


async def require_user_api(user: User | None = Depends(get_current_user)) -> User:
    if user is None:
        raise DomainError(code=ErrorCode.UNAUTHORIZED, message="Unauthorized")
    return user


async def require_admin_api(user: User = Depends(require_user_api)) -> User:
    require_any_role(user=user, roles={Role.ADMIN, Role.SUPERUSER})
    return user


async def require_contributor_api(user: User = Depends(require_user_api)) -> User:
    require_at_least_role(user=user, role=Role.CONTRIBUTOR)
    return user


async def require_superuser_api(user: User = Depends(require_user_api)) -> User:
    require_any_role(user=user, roles={Role.SUPERUSER})
    return user


async def require_session_api(session: Session | None = Depends(get_current_session)) -> Session:
    if session is None:
        raise DomainError(code=ErrorCode.UNAUTHORIZED, message="Unauthorized")
    return session


async def require_csrf_token(
    csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
    session: Session = Depends(require_session_api),
) -> None:
    if not csrf_token or csrf_token != session.csrf_token:
        raise DomainError(code=ErrorCode.FORBIDDEN, message="CSRF validation failed")
