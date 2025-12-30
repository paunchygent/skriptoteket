from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, Header, Request, Response, status
from pydantic import BaseModel, ConfigDict

from skriptoteket.application.identity.commands import (
    LoginCommand,
    LogoutCommand,
    RegisterUserCommand,
    ResendVerificationCommand,
    VerifyEmailCommand,
)
from skriptoteket.application.identity.handlers.resend_verification import (
    ResendVerificationHandlerProtocol,
)
from skriptoteket.application.identity.handlers.verify_email import VerifyEmailHandlerProtocol
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Session, User, UserProfile
from skriptoteket.protocols.identity import (
    LoginHandlerProtocol,
    LogoutHandlerProtocol,
    ProfileRepositoryProtocol,
    RegisterUserHandlerProtocol,
)
from skriptoteket.web.auth.api_dependencies import require_session_api, require_user_api
from skriptoteket.web.auth.dependencies import get_current_session, get_session_id
from skriptoteket.web.request_metadata import (
    get_client_ip,
    get_correlation_id,
    get_user_agent,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    email: str
    password: str


class LoginResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    user: User
    profile: UserProfile | None = None
    csrf_token: str


class RegisterRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    email: str
    password: str
    first_name: str
    last_name: str


class RegisterResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    user: User
    profile: UserProfile
    message: str = "Konto skapat! Kontrollera din e-post för att verifiera kontot."


class MeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    user: User
    profile: UserProfile | None = None


class CsrfResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    csrf_token: str


@router.post("/login", response_model=LoginResponse)
@inject
async def login(
    payload: LoginRequest,
    response: Response,
    request: Request,
    settings: FromDishka[Settings],
    handler: FromDishka[LoginHandlerProtocol],
) -> LoginResponse:
    result = await handler.handle(
        LoginCommand(
            email=payload.email,
            password=payload.password,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            correlation_id=get_correlation_id(request),
        )
    )

    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=str(result.session_id),
        max_age=settings.SESSION_TTL_SECONDS,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )
    return LoginResponse(user=result.user, profile=result.profile, csrf_token=result.csrf_token)


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
@inject
async def register(
    payload: RegisterRequest,
    handler: FromDishka[RegisterUserHandlerProtocol],
) -> RegisterResponse:
    """Register a new user account.

    User must verify their email before they can login.
    """
    result = await handler.handle(
        RegisterUserCommand(
            email=payload.email,
            password=payload.password,
            first_name=payload.first_name,
            last_name=payload.last_name,
        )
    )
    # No cookie - user must verify email first
    return RegisterResponse(user=result.user, profile=result.profile)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def logout(
    response: Response,
    settings: FromDishka[Settings],
    handler: FromDishka[LogoutHandlerProtocol],
    session_id: UUID | None = Depends(get_session_id),
    session: Session | None = Depends(get_current_session),
    csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> None:
    if session_id is None or session is None:
        response.delete_cookie(key=settings.SESSION_COOKIE_NAME, path="/")
        return None

    if not csrf_token or csrf_token != session.csrf_token:
        raise DomainError(code=ErrorCode.FORBIDDEN, message="CSRF validation failed")

    await handler.handle(LogoutCommand(session_id=session_id, csrf_token=csrf_token))
    response.delete_cookie(key=settings.SESSION_COOKIE_NAME, path="/")
    return None


@router.get("/me", response_model=MeResponse)
@inject
async def me(
    profiles: FromDishka[ProfileRepositoryProtocol],
    user: User = Depends(require_user_api),
) -> MeResponse:
    profile = await profiles.get_by_user_id(user_id=user.id)
    return MeResponse(user=user, profile=profile)


@router.get("/csrf", response_model=CsrfResponse)
async def csrf(session: Session = Depends(require_session_api)) -> CsrfResponse:
    return CsrfResponse(csrf_token=session.csrf_token)


class VerifyEmailRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    token: str


class VerifyEmailResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    message: str
    user: User


class ResendVerificationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    email: str


class ResendVerificationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    message: str


@router.post("/verify-email", response_model=VerifyEmailResponse)
@inject
async def verify_email(
    payload: VerifyEmailRequest,
    handler: FromDishka[VerifyEmailHandlerProtocol],
) -> VerifyEmailResponse:
    """Verify email with token from verification link."""
    result = await handler.handle(VerifyEmailCommand(token=payload.token))
    return VerifyEmailResponse(message=result.message, user=result.user)


@router.post("/resend-verification", response_model=ResendVerificationResponse)
@inject
async def resend_verification(
    payload: ResendVerificationRequest,
    handler: FromDishka[ResendVerificationHandlerProtocol],
) -> ResendVerificationResponse:
    """Resend verification email.

    Always returns success for security (doesn't reveal if email exists).
    """
    result = await handler.handle(ResendVerificationCommand(email=payload.email))
    return ResendVerificationResponse(message=result.message)
