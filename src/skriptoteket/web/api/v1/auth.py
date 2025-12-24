from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, Header, Response, status
from pydantic import BaseModel, ConfigDict

from skriptoteket.application.identity.commands import (
    LoginCommand,
    LogoutCommand,
    RegisterUserCommand,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Session, User, UserProfile
from skriptoteket.protocols.identity import (
    LoginHandlerProtocol,
    LogoutHandlerProtocol,
    RegisterUserHandlerProtocol,
)
from skriptoteket.web.auth.api_dependencies import require_session_api, require_user_api
from skriptoteket.web.auth.dependencies import get_current_session, get_session_id

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    email: str
    password: str


class LoginResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    user: User
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
    csrf_token: str


class MeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    user: User


class CsrfResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    csrf_token: str


@router.post("/login", response_model=LoginResponse)
@inject
async def login(
    payload: LoginRequest,
    response: Response,
    settings: FromDishka[Settings],
    handler: FromDishka[LoginHandlerProtocol],
) -> LoginResponse:
    result = await handler.handle(LoginCommand(email=payload.email, password=payload.password))

    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=str(result.session_id),
        max_age=settings.SESSION_TTL_SECONDS,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )
    return LoginResponse(user=result.user, csrf_token=result.csrf_token)


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
@inject
async def register(
    payload: RegisterRequest,
    response: Response,
    settings: FromDishka[Settings],
    handler: FromDishka[RegisterUserHandlerProtocol],
) -> RegisterResponse:
    result = await handler.handle(
        RegisterUserCommand(
            email=payload.email,
            password=payload.password,
            first_name=payload.first_name,
            last_name=payload.last_name,
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
    return RegisterResponse(
        user=result.user,
        profile=result.profile,
        csrf_token=result.csrf_token,
    )


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
async def me(user: User = Depends(require_user_api)) -> MeResponse:
    return MeResponse(user=user)


@router.get("/csrf", response_model=CsrfResponse)
async def csrf(session: Session = Depends(require_session_api)) -> CsrfResponse:
    return CsrfResponse(csrf_token=session.csrf_token)
