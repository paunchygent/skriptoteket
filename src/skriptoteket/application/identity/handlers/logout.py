from __future__ import annotations

from skriptoteket.application.identity.commands import LogoutCommand
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.identity import LogoutHandlerProtocol, SessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class LogoutHandler(LogoutHandlerProtocol):
    def __init__(self, *, uow: UnitOfWorkProtocol, sessions: SessionRepositoryProtocol) -> None:
        self._uow = uow
        self._sessions = sessions

    async def handle(self, command: LogoutCommand) -> None:
        async with self._uow:
            session = await self._sessions.get_by_id(command.session_id)
            if session is None or session.csrf_token != command.csrf_token:
                raise DomainError(code=ErrorCode.FORBIDDEN, message="CSRF validation failed")
            await self._sessions.revoke(session_id=command.session_id)
