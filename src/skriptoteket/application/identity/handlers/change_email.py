from __future__ import annotations

from skriptoteket.application.identity.commands import ChangeEmailCommand, ChangeEmailResult
from skriptoteket.application.identity.email_validation import validate_email
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import ChangeEmailHandlerProtocol, UserRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class ChangeEmailHandler(ChangeEmailHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._users = users
        self._clock = clock

    async def handle(self, command: ChangeEmailCommand) -> ChangeEmailResult:
        new_email = validate_email(email=command.new_email)

        async with self._uow:
            user = await self._users.get_by_id(command.user_id)
            if user is None:
                raise not_found("User", str(command.user_id))

            if new_email == user.email:
                raise DomainError(
                    code=ErrorCode.DUPLICATE_ENTRY,
                    message="E-postadressen är redan registrerad",
                )

            existing = await self._users.get_auth_by_email(new_email)
            if existing and existing.user.id != user.id:
                raise DomainError(
                    code=ErrorCode.DUPLICATE_ENTRY,
                    message="E-postadressen är redan registrerad",
                )

            updated_user = user.model_copy(
                update={
                    "email": new_email,
                    "email_verified": False,
                    "updated_at": self._clock.now(),
                }
            )
            user = await self._users.update(user=updated_user)

        return ChangeEmailResult(user=user)
