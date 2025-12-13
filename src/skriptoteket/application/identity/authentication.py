from __future__ import annotations

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import AuthProvider, User
from skriptoteket.protocols.identity import PasswordHasherProtocol, UserRepositoryProtocol


async def authenticate_local_user(
    *,
    users: UserRepositoryProtocol,
    password_hasher: PasswordHasherProtocol,
    email: str,
    password: str,
) -> User:
    normalized_email = email.strip().lower()
    user_auth = await users.get_auth_by_email(normalized_email)
    if not user_auth or not user_auth.user.is_active:
        raise DomainError(code=ErrorCode.INVALID_CREDENTIALS, message="Invalid credentials")

    if user_auth.user.auth_provider is not AuthProvider.LOCAL:
        raise DomainError(code=ErrorCode.INVALID_CREDENTIALS, message="Invalid credentials")

    if not user_auth.password_hash:
        raise DomainError(code=ErrorCode.INVALID_CREDENTIALS, message="Invalid credentials")

    if not password_hasher.verify(password=password, password_hash=user_auth.password_hash):
        raise DomainError(code=ErrorCode.INVALID_CREDENTIALS, message="Invalid credentials")

    return user_auth.user
