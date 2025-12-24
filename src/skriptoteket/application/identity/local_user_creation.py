from __future__ import annotations

from skriptoteket.application.identity.commands import CreateLocalUserCommand, CreateLocalUserResult
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import AuthProvider, User
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import PasswordHasherProtocol, UserRepositoryProtocol


async def create_local_user(
    *,
    users: UserRepositoryProtocol,
    password_hasher: PasswordHasherProtocol,
    clock: ClockProtocol,
    id_generator: IdGeneratorProtocol,
    command: CreateLocalUserCommand,
    email_verified: bool = True,
) -> CreateLocalUserResult:
    email = command.email.strip().lower()
    if await users.get_auth_by_email(email):
        raise DomainError(
            code=ErrorCode.DUPLICATE_ENTRY,
            message="E-postadressen är redan registrerad",
        )

    now = clock.now()
    user = User(
        id=id_generator.new_uuid(),
        email=email,
        role=command.role,
        auth_provider=AuthProvider.LOCAL,
        external_id=None,
        is_active=True,
        email_verified=email_verified,
        failed_login_attempts=0,
        locked_until=None,
        last_login_at=None,
        last_failed_login_at=None,
        created_at=now,
        updated_at=now,
    )
    password_hash = password_hasher.hash(password=command.password)

    created = await users.create(user=user, password_hash=password_hash)
    return CreateLocalUserResult(user=created)
