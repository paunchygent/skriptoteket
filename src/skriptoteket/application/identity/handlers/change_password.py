from __future__ import annotations

from skriptoteket.application.identity.commands import ChangePasswordCommand
from skriptoteket.application.identity.password_validation import validate_password_strength
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import AuthProvider
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    ChangePasswordHandlerProtocol,
    PasswordHasherProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class ChangePasswordHandler(ChangePasswordHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        password_hasher: PasswordHasherProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._users = users
        self._password_hasher = password_hasher
        self._clock = clock

    async def handle(self, command: ChangePasswordCommand) -> None:
        validate_password_strength(password=command.new_password)

        async with self._uow:
            user = await self._users.get_by_id(command.user_id)
            if user is None:
                raise not_found("User", str(command.user_id))

            if user.auth_provider is not AuthProvider.LOCAL:
                raise DomainError(
                    code=ErrorCode.INVALID_CREDENTIALS,
                    message="Fel lösenord",
                )

            user_auth = await self._users.get_auth_by_email(user.email)
            if user_auth is None or user_auth.user.id != user.id or not user_auth.password_hash:
                raise DomainError(
                    code=ErrorCode.INVALID_CREDENTIALS,
                    message="Fel lösenord",
                )

            if not self._password_hasher.verify(
                password=command.current_password,
                password_hash=user_auth.password_hash,
            ):
                raise DomainError(
                    code=ErrorCode.INVALID_CREDENTIALS,
                    message="Fel lösenord",
                )

            password_hash = self._password_hasher.hash(password=command.new_password)
            await self._users.update_password_hash(
                user_id=user.id,
                password_hash=password_hash,
                updated_at=self._clock.now(),
            )
