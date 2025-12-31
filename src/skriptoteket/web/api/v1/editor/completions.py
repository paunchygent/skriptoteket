from __future__ import annotations

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends

from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.llm import InlineCompletionCommand, InlineCompletionHandlerProtocol
from skriptoteket.web.auth.api_dependencies import require_contributor_api, require_csrf_token

from .models import EditorInlineCompletionRequest, EditorInlineCompletionResponse

router = APIRouter()


@router.post("/completions", response_model=EditorInlineCompletionResponse)
@inject
async def create_inline_completion(
    payload: EditorInlineCompletionRequest,
    handler: FromDishka[InlineCompletionHandlerProtocol],
    user: User = Depends(require_contributor_api),
    _: None = Depends(require_csrf_token),
) -> EditorInlineCompletionResponse:
    result = await handler.handle(
        actor=user,
        command=InlineCompletionCommand(prefix=payload.prefix, suffix=payload.suffix),
    )
    return EditorInlineCompletionResponse(
        completion=result.completion,
        enabled=result.enabled,
    )
