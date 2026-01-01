from __future__ import annotations

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, Header, Response

from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.protocols.llm import EditSuggestionCommand, EditSuggestionHandlerProtocol
from skriptoteket.web.auth.api_dependencies import require_contributor_api, require_csrf_token

from .models import EditorEditSuggestionRequest, EditorEditSuggestionResponse

router = APIRouter()

_EVAL_REQUEST_HEADER = "X-Skriptoteket-Eval"


@router.post("/edits", response_model=EditorEditSuggestionResponse)
@inject
async def create_edit_suggestion(
    payload: EditorEditSuggestionRequest,
    response: Response,
    handler: FromDishka[EditSuggestionHandlerProtocol],
    settings: FromDishka[Settings],
    user: User = Depends(require_contributor_api),
    _: None = Depends(require_csrf_token),
    eval_mode: str | None = Header(default=None, alias=_EVAL_REQUEST_HEADER),
) -> EditorEditSuggestionResponse:
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
        command=EditSuggestionCommand(
            prefix=payload.prefix,
            selection=payload.selection,
            suffix=payload.suffix,
            instruction=payload.instruction,
        ),
    )
    if eval_mode == "1" and result.eval_meta is not None:
        response.headers["X-Skriptoteket-Eval-Template-Id"] = result.eval_meta.template_id or ""
        response.headers["X-Skriptoteket-Eval-Outcome"] = result.eval_meta.outcome
        response.headers["X-Skriptoteket-Eval-System-Prompt-Chars"] = str(
            result.eval_meta.system_prompt_chars
        )
        response.headers["X-Skriptoteket-Eval-Instruction-Chars"] = str(
            result.eval_meta.instruction_chars
        )
        response.headers["X-Skriptoteket-Eval-Selection-Chars"] = str(
            result.eval_meta.selection_chars
        )
        response.headers["X-Skriptoteket-Eval-Prefix-Chars"] = str(result.eval_meta.prefix_chars)
        response.headers["X-Skriptoteket-Eval-Suffix-Chars"] = str(result.eval_meta.suffix_chars)

    return EditorEditSuggestionResponse(
        suggestion=result.suggestion,
        enabled=result.enabled,
    )
