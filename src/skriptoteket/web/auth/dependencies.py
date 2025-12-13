from __future__ import annotations

from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import Depends, HTTPException, Request

from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role, Session, User
from skriptoteket.domain.identity.role_guards import require_any_role
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import CurrentUserProviderProtocol, SessionRepositoryProtocol


def _parse_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


@inject
def get_session_id(request: Request, settings: FromDishka[Settings]) -> UUID | None:
    return _parse_uuid(request.cookies.get(settings.SESSION_COOKIE_NAME))


@inject
async def get_current_session(
    sessions: FromDishka[SessionRepositoryProtocol],
    clock: FromDishka[ClockProtocol],
    session_id: UUID | None = Depends(get_session_id),
) -> Session | None:
    if session_id is None:
        return None

    session = await sessions.get_by_id(session_id)
    if session is None or session.revoked_at is not None:
        return None
    if session.expires_at <= clock.now():
        return None
    return session


@inject
async def get_current_user(
    provider: FromDishka[CurrentUserProviderProtocol],
    session_id: UUID | None = Depends(get_session_id),
) -> User | None:
    return await provider.get_current_user(session_id=session_id)


async def require_user(user: User | None = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


async def require_admin(user: User = Depends(require_user)) -> User:
    require_any_role(user=user, roles={Role.ADMIN, Role.SUPERUSER})
    return user


async def require_superuser(user: User = Depends(require_user)) -> User:
    require_any_role(user=user, roles={Role.SUPERUSER})
    return user
