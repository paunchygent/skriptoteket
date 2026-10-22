"""One-question retry limit mapping (TASK-SKRIPT-41-01-03 B4).

Purpose:
    Run one retry batch and turn a door limit or overage-cap refusal into the
    429 limit error carrying the matching teacher note: the user's own note for
    a user-share refusal, the app note for pool, USD ceiling and the cap
    (recorded as pool). A busy door becomes the 429 try-again error carrying
    the try-again note and the door's Retry-After. A refusal never becomes a
    review item.

Relationships:
    Consumed by ``exam_workspace_docx_retry``; reuses ``convert_batch`` with
    the retry's door caller.
"""

from __future__ import annotations

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build import (
    BatchOutcome,
    convert_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_rounds import (
    DocxBuildExchangeProtocol,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import (
    ConversionBatch,
    QuestionFamily,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.llm_door import (
    AiDailyLimit,
    AiDailyLimitReached,
    AiDoorBusy,
    AiDoorCaller,
    AiJobOverageCapReached,
    ai_limit_note,
    door_refusal_error,
)


async def convert_retry_batch_with_limit(
    *,
    state: DocxBuildState,
    batch: ConversionBatch,
    families: dict[str, QuestionFamily],
    exchange: DocxBuildExchangeProtocol,
    profile: StructuredLLMProviderProfile,
    caller: AiDoorCaller,
) -> BatchOutcome:
    """Run one retry batch; a door refusal or busy door becomes a 429 error, never a review item."""

    try:
        return await convert_batch(
            state=state,
            batch=batch,
            families=families,
            exchange=exchange,
            profile=profile,
            caller=caller,
        )
    except (AiDailyLimitReached, AiDoorBusy) as error:
        raise door_refusal_error(error) from error
    except AiJobOverageCapReached as error:
        raise DomainError(
            code=ErrorCode.AI_DAILY_LIMIT_REACHED,
            message=ai_limit_note(AiDailyLimit.POOL),
            details={"limit": AiDailyLimit.POOL.value},
        ) from error
