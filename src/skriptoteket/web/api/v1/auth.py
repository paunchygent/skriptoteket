"""Authentication routes for Skriptoteket's SPA-facing API.

Purpose:
    Expose login, logout, identity, and email-verification endpoints backed by
    application-layer protocols and cookie-based session auth.

Relationships:
    - Uses `skriptoteket.web.request_metadata` to capture audit metadata for
      login events.
    - Depends on `skriptoteket.config.Settings` for cookie policy and runtime
      feature flags.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from skriptoteket.application.identity.commands import (
    LoginCommand,
    LogoutCommand,
    RegisterUserCommand,
    RequestPasswordResetCommand,
    ResendVerificationCommand,
    ResetPasswordCommand,
    ValidateRegistrationCommand,
    VerifyEmailCommand,
)
from skriptoteket.application.identity.handlers.request_password_reset import (
    RequestPasswordResetHandlerProtocol,
)
from skriptoteket.application.identity.handlers.resend_verification import (
    ResendVerificationHandlerProtocol,
)
from skriptoteket.application.identity.handlers.reset_password import (
    ResetPasswordHandlerProtocol,
)
from skriptoteket.application.identity.handlers.verify_email import VerifyEmailHandlerProtocol
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Session, User, UserProfile
from skriptoteket.infrastructure.llm.provider_sets import is_remote_llm_endpoint
from skriptoteket.protocols.identity import (
    LoginHandlerProtocol,
    LogoutHandlerProtocol,
    ProfileRepositoryProtocol,
    RegisterUserHandlerProtocol,
    ValidateRegistrationHandlerProtocol,
)
from skriptoteket.web.auth.api_dependencies import require_session_api
from skriptoteket.web.auth.dependencies import (
    get_current_session,
    get_current_user,
    get_session_id,
)
from skriptoteket.web.dishka_dependencies import FromDishka
from skriptoteket.web.request_metadata import (
    get_client_ip,
    get_correlation_id,
    get_user_agent,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class AiPolicyResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    remote_providers_enabled: bool
    completion_external_available: bool
    completion_local_available: bool


def _build_ai_policy(settings: Settings) -> AiPolicyResponse:
    completion_candidates = [
        (settings.LLM_COMPLETION_BASE_URL.strip(), settings.LLM_COMPLETION_MODEL.strip()),
        (
            settings.LLM_COMPLETION_FALLBACK_BASE_URL.strip(),
            settings.LLM_COMPLETION_FALLBACK_MODEL.strip(),
        ),
    ]
    configured = [(url, model) for url, model in completion_candidates if url and model]
    completion_external_available = any(is_remote_llm_endpoint(url) for url, _ in configured)
    completion_local_available = any(not is_remote_llm_endpoint(url) for url, _ in configured)
    return AiPolicyResponse(
        remote_providers_enabled=settings.AI_REMOTE_PROVIDERS_ENABLED,
        completion_external_available=completion_external_available,
        completion_local_available=completion_local_available,
    )


class LoginRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    email: str
    password: str


class LoginResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    user: User
    profile: UserProfile | None = None
    csrf_token: str
    ai_policy: AiPolicyResponse


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


class RegistrationValidationFieldResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    status: str
    message: str | None = None


class ValidateRegistrationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    email: str | None = None
    password: str | None = None


class ValidateRegistrationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    email: RegistrationValidationFieldResponse
    password: RegistrationValidationFieldResponse


class MeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    authenticated: bool
    user: User | None = None
    profile: UserProfile | None = None
    ai_policy: AiPolicyResponse


class CsrfResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    csrf_token: str


@router.post("/login", response_model=LoginResponse)
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
            ip_address=get_client_ip(request, settings=settings),
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
    return LoginResponse(
        user=result.user,
        profile=result.profile,
        csrf_token=result.csrf_token,
        ai_policy=_build_ai_policy(settings),
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    handler: FromDishka[RegisterUserHandlerProtocol],
) -> RegisterResponse:
    """Register a new user account."""
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


@router.post("/register/validate", response_model=ValidateRegistrationResponse)
async def validate_registration(
    payload: ValidateRegistrationRequest,
    handler: FromDishka[ValidateRegistrationHandlerProtocol],
) -> ValidateRegistrationResponse:
    result = await handler.handle(
        ValidateRegistrationCommand(email=payload.email, password=payload.password)
    )
    return ValidateRegistrationResponse(
        email=RegistrationValidationFieldResponse(
            status=result.email.status,
            message=result.email.message,
        ),
        password=RegistrationValidationFieldResponse(
            status=result.password.status,
            message=result.password.message,
        ),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
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
async def me(
    profiles: FromDishka[ProfileRepositoryProtocol],
    settings: FromDishka[Settings],
    user: User | None = Depends(get_current_user),
) -> MeResponse:
    if user is None:
        return MeResponse(
            authenticated=False,
            user=None,
            profile=None,
            ai_policy=_build_ai_policy(settings),
        )
    profile = await profiles.get_by_user_id(user_id=user.id)
    return MeResponse(
        authenticated=True,
        user=user,
        profile=profile,
        ai_policy=_build_ai_policy(settings),
    )


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


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    email: str | None = None


class ForgotPasswordResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    message: str


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    token: str | None = None
    new_password: str | None = None


class ResetPasswordResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    message: str


def _require_non_empty_string(*, value: str | None, field_name: str) -> str:
    if value is None:
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"{field_name} måste anges",
        )
    normalized = value.strip()
    if normalized == "":
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"{field_name} måste anges",
        )
    return normalized


def _domain_error_response(
    *,
    request: Request,
    error: DomainError,
    status_code: int,
) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", None)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": error.code.value,
                "message": error.message,
                "details": error.details,
            },
            "correlation_id": str(correlation_id) if correlation_id else None,
        },
    )


@router.post("/verify-email", response_model=VerifyEmailResponse)
async def verify_email(
    payload: VerifyEmailRequest,
    handler: FromDishka[VerifyEmailHandlerProtocol],
) -> VerifyEmailResponse:
    """Verify email with token from verification link."""
    result = await handler.handle(VerifyEmailCommand(token=payload.token))
    return VerifyEmailResponse(message=result.message, user=result.user)


@router.post("/resend-verification", response_model=ResendVerificationResponse)
async def resend_verification(
    payload: ResendVerificationRequest,
    handler: FromDishka[ResendVerificationHandlerProtocol],
) -> ResendVerificationResponse:
    """Resend verification email.
    Always returns success for security (doesn't reveal if email exists).
    """
    result = await handler.handle(ResendVerificationCommand(email=payload.email))
    return ResendVerificationResponse(message=result.message)


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    handler: FromDishka[RequestPasswordResetHandlerProtocol],
) -> ForgotPasswordResponse:
    email = payload.email.strip() if isinstance(payload.email, str) else ""
    result = await handler.handle(RequestPasswordResetCommand(email=email))
    return ForgotPasswordResponse(message=result.message)


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    handler: FromDishka[ResetPasswordHandlerProtocol],
) -> object:
    try:
        result = await handler.handle(
            ResetPasswordCommand(
                token=_require_non_empty_string(value=payload.token, field_name="Token"),
                new_password=_require_non_empty_string(
                    value=payload.new_password,
                    field_name="Nytt lösenord",
                ),
            )
        )
    except DomainError as error:
        if error.code is ErrorCode.VALIDATION_ERROR:
            return _domain_error_response(
                request=request,
                error=error,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        raise
    return ResetPasswordResponse(message=result.message)
