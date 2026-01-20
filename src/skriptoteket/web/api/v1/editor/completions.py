from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, Header, Response

from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role, Session, User
from skriptoteket.protocols.llm import InlineCompletionCommand, InlineCompletionHandlerProtocol
from skriptoteket.web.auth.api_dependencies import (
    require_contributor_api,
    require_csrf_token,
    require_session_api,
)

from .models import EditorInlineCompletionRequest, EditorInlineCompletionResponse

router = APIRouter()

_EVAL_REQUEST_HEADER = "X-Skriptoteket-Eval"


@router.post(
    "/completions",
    response_model=EditorInlineCompletionResponse,
    response_model_exclude_none=True,
)
@inject
async def create_inline_completion(
    payload: EditorInlineCompletionRequest,
    response: Response,
    handler: FromDishka[InlineCompletionHandlerProtocol],
    settings: FromDishka[Settings],
    user: User = Depends(require_contributor_api),
    session: Session = Depends(require_session_api),
    _: None = Depends(require_csrf_token),
    eval_mode: str | None = Header(default=None, alias=_EVAL_REQUEST_HEADER),
) -> EditorInlineCompletionResponse:
    if eval_mode == "1":
        if settings.ENVIRONMENT == "production":
            raise DomainError(
                code=ErrorCode.FORBIDDEN,
                message="Eval mode is not available in production",
            )
        if user.role not in {Role.ADMIN, Role.SUPERUSER}:
            raise DomainError(code=ErrorCode.FORBIDDEN, message="Eval mode requires admin access")

    result = await handler.handle(
        actor=user,
        command=InlineCompletionCommand(
            prefix=payload.prefix,
            suffix=payload.suffix,
            active_file=payload.active_file,
            allow_remote_fallback=session.allow_remote_fallback,
            inline_completion_provider=session.inline_completion_provider,
        ),
    )
    if eval_mode == "1" and result.eval_meta is not None:
        response.headers["X-Skriptoteket-Eval-Template-Id"] = result.eval_meta.template_id or ""
        response.headers["X-Skriptoteket-Eval-Outcome"] = result.eval_meta.outcome
        response.headers["X-Skriptoteket-Eval-System-Prompt-Chars"] = str(
            result.eval_meta.system_prompt_chars
        )
        response.headers["X-Skriptoteket-Eval-Prefix-Chars"] = str(result.eval_meta.prefix_chars)
        response.headers["X-Skriptoteket-Eval-Suffix-Chars"] = str(result.eval_meta.suffix_chars)
        if result.eval_meta.raw_chars is not None:
            response.headers["X-Skriptoteket-Eval-Raw-Chars"] = str(result.eval_meta.raw_chars)
        if result.eval_meta.normalized_chars is not None:
            response.headers["X-Skriptoteket-Eval-Normalized-Chars"] = str(
                result.eval_meta.normalized_chars
            )
        if result.eval_meta.prefix_overlap_chars is not None:
            response.headers["X-Skriptoteket-Eval-Prefix-Overlap-Chars"] = str(
                result.eval_meta.prefix_overlap_chars
            )
        if result.eval_meta.suffix_overlap_chars is not None:
            response.headers["X-Skriptoteket-Eval-Suffix-Overlap-Chars"] = str(
                result.eval_meta.suffix_overlap_chars
            )
        if result.eval_meta.prepare_ms is not None:
            response.headers["X-Skriptoteket-Eval-Prepare-Ms"] = str(result.eval_meta.prepare_ms)
        if result.eval_meta.provider_ms is not None:
            response.headers["X-Skriptoteket-Eval-Provider-Ms"] = str(result.eval_meta.provider_ms)
        if result.eval_meta.normalize_ms is not None:
            response.headers["X-Skriptoteket-Eval-Normalize-Ms"] = str(
                result.eval_meta.normalize_ms
            )
        if result.eval_meta.total_ms is not None:
            response.headers["X-Skriptoteket-Eval-Total-Ms"] = str(result.eval_meta.total_ms)

    return EditorInlineCompletionResponse(
        completion=result.completion,
        enabled=result.enabled,
        notice_message=result.notice_message,
        notice_variant=result.notice_variant,
        notice_code=result.notice_code,
    )
