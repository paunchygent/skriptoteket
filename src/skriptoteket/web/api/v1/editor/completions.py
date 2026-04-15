"""Inline-completion editor API routes.

Purpose:
    Accept editor inline completion requests and translate them into
    application-layer AI completion commands.

Relationships:
    - Signed HuleEdu-derived authentication stays in web dependencies.
    - AI consent/provider preferences come from request-scoped profile state.
"""

from fastapi import APIRouter, Depends, Header, Response

from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_any_role
from skriptoteket.protocols.llm import InlineCompletionCommand, InlineCompletionHandlerProtocol
from skriptoteket.web.auth.ai_preferences import AiPreferences, require_app_ai_preferences
from skriptoteket.web.auth.huleedu_app_projection import (
    require_app_contributor_api,
)
from skriptoteket.web.dishka_dependencies import FromDishka

from .models.requests import EditorInlineCompletionRequest
from .models.responses import EditorInlineCompletionResponse

router = APIRouter()
_EVAL_REQUEST_HEADER = "X-Skriptoteket-Eval"


@router.post(
    "/completions",
    response_model=EditorInlineCompletionResponse,
    response_model_exclude_none=True,
)
async def create_inline_completion(
    payload: EditorInlineCompletionRequest,
    response: Response,
    handler: FromDishka[InlineCompletionHandlerProtocol],
    settings: FromDishka[Settings],
    user: User = Depends(require_app_contributor_api),
    ai_preferences: AiPreferences = Depends(require_app_ai_preferences),
    eval_mode: str | None = Header(default=None, alias=_EVAL_REQUEST_HEADER),
) -> EditorInlineCompletionResponse:
    if eval_mode == "1":
        if settings.ENVIRONMENT == "production":
            raise DomainError(
                code=ErrorCode.FORBIDDEN,
                message="Eval mode is not available in production",
            )
        require_any_role(user=user, roles=(Role.ADMIN, Role.SUPERUSER))
    result = await handler.handle(
        actor=user,
        command=InlineCompletionCommand(
            prefix=payload.prefix,
            suffix=payload.suffix,
            active_file=payload.active_file,
            allow_remote_fallback=ai_preferences.allow_remote_fallback,
            inline_completion_provider=ai_preferences.inline_completion_provider,
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
        if result.eval_meta.system_prompt_tokens is not None:
            response.headers["X-Skriptoteket-Eval-System-Prompt-Tokens"] = str(
                result.eval_meta.system_prompt_tokens
            )
        if result.eval_meta.prefix_tokens is not None:
            response.headers["X-Skriptoteket-Eval-Prefix-Tokens"] = str(
                result.eval_meta.prefix_tokens
            )
        if result.eval_meta.suffix_tokens is not None:
            response.headers["X-Skriptoteket-Eval-Suffix-Tokens"] = str(
                result.eval_meta.suffix_tokens
            )
        if result.eval_meta.prompt_tokens_total is not None:
            response.headers["X-Skriptoteket-Eval-Prompt-Tokens-Total"] = str(
                result.eval_meta.prompt_tokens_total
            )
        if result.eval_meta.prompt_budget_tokens is not None:
            response.headers["X-Skriptoteket-Eval-Prompt-Budget-Tokens"] = str(
                result.eval_meta.prompt_budget_tokens
            )
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
        replace_suffix_chars=result.replace_suffix_chars,
        notice_message=result.notice_message,
        notice_variant=result.notice_variant,
        notice_code=result.notice_code,
    )
