from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, Header, Response

from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.llm import (
    EditOpsCommand,
    EditOpsCursor,
    EditOpsHandlerProtocol,
    EditOpsSelection,
)
from skriptoteket.web.auth.api_dependencies import require_contributor_api, require_csrf_token
from skriptoteket.web.editor_support import require_tool_access

from .models import EditorEditOpsRequest, EditorEditOpsResponse

router = APIRouter()

_EVAL_REQUEST_HEADER = "X-Skriptoteket-Eval"


@router.post("/edit-ops", response_model=EditorEditOpsResponse)
@inject
async def create_edit_ops(
    payload: EditorEditOpsRequest,
    response: Response,
    handler: FromDishka[EditOpsHandlerProtocol],
    settings: FromDishka[Settings],
    maintainers: FromDishka[ToolMaintainerRepositoryProtocol],
    user: User = Depends(require_contributor_api),
    _: None = Depends(require_csrf_token),
    eval_mode: str | None = Header(default=None, alias=_EVAL_REQUEST_HEADER),
) -> EditorEditOpsResponse:
    if eval_mode == "1":
        if settings.ENVIRONMENT == "production":
            raise DomainError(
                code=ErrorCode.FORBIDDEN,
                message="Eval mode is not available in production",
            )
        if user.role not in {Role.ADMIN, Role.SUPERUSER}:
            raise DomainError(code=ErrorCode.FORBIDDEN, message="Eval mode requires admin access")

    await require_tool_access(actor=user, tool_id=payload.tool_id, maintainers=maintainers)

    selection = (
        EditOpsSelection(start=payload.selection.start, end=payload.selection.end)
        if payload.selection
        else None
    )
    cursor = EditOpsCursor(pos=payload.cursor.pos) if payload.cursor else None

    result = await handler.handle(
        actor=user,
        command=EditOpsCommand(
            tool_id=payload.tool_id,
            message=payload.message,
            active_file=payload.active_file,
            selection=selection,
            cursor=cursor,
            virtual_files=payload.virtual_files.as_map(),
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

    return EditorEditOpsResponse(
        enabled=result.enabled,
        assistant_message=result.assistant_message,
        ops=[op.model_dump(exclude_none=True) for op in result.ops],
        base_fingerprints=result.base_fingerprints,
    )
