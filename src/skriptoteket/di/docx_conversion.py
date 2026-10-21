"""Compose the type-batched DOCX conversion pipeline (TASK-SKRIPT-39-05-04).

The DOCX job and the exam-conversion eval build the converter through this one function,
so both run the same grouping, labeling, batching and assembly.
"""

from __future__ import annotations

import httpx

from skriptoteket.application.curated_apps.exam_content_tagging import (
    MeteredExamContentTagClassifier,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_rounds import (
    DocxBuildRoundExchange,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_grouping import (
    ResponsesExamGrouper,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_pipeline import (
    DocxConversionPipeline,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_serial_uow import (
    SerializedUnitOfWork,
)
from skriptoteket.application.curated_apps.item_type_labeling import TwoPassItemTypeLabeler
from skriptoteket.config import Settings
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_labeler_markdown import (  # noqa: E501
    PythonDocxLabelerMarkdown,
)
from skriptoteket.infrastructure.llm.openai.decisions_item_labeler import (
    OpenAIDecisionsItemTypeLabeler,
)
from skriptoteket.infrastructure.llm.openai.docx_conversion_profiles import (
    build_luna_docx_conversion_profile,
    build_luna_docx_grouping_profile,
    build_luna_item_label_profile,
)
from skriptoteket.infrastructure.llm.openai.responses_item_labeler import (
    ResponsesSecondPassItemTypeLabeler,
)
from skriptoteket.protocols.docx_conversion_progress import DocxConversionProgressProtocol
from skriptoteket.protocols.exam_answer_key import (
    AnswerKeyStructuredProviderProtocol,
)
from skriptoteket.protocols.sleeper import SleeperProtocol


def build_docx_conversion_pipeline(
    *,
    client: httpx.AsyncClient,
    provider: AnswerKeyStructuredProviderProtocol,
    sleeper: SleeperProtocol,
    uow: SerializedUnitOfWork,
    settings: Settings,
    progress: DocxConversionProgressProtocol,
) -> DocxConversionPipeline:
    """Grouping, the second label pass and batch conversion share one Responses provider.

    The Decisions first pass calls its own endpoint on ``client``.
    """
    exchange = DocxBuildRoundExchange(provider)
    return DocxConversionPipeline(
        grouper=ResponsesExamGrouper(
            exchange=exchange, profile=build_luna_docx_grouping_profile(settings)
        ),
        labeler=TwoPassItemTypeLabeler(
            first_pass=OpenAIDecisionsItemTypeLabeler(
                client=client,
                base_url=settings.LLM_ANSWER_KEY_BASE_URL,
                api_key=settings.OPENAI_LLM_ANSWER_KEY_API_KEY,
                timeout_seconds=float(settings.LLM_ITEM_LABELER_TIMEOUT_SECONDS),
                sleeper=sleeper,
            ),
            second_pass=ResponsesSecondPassItemTypeLabeler(
                provider=provider, profile=build_luna_item_label_profile(settings), sleeper=sleeper
            ),
        ),
        content_classifier=MeteredExamContentTagClassifier(
            classifier=OpenAIDecisionsItemTypeLabeler(
                client=client,
                base_url=settings.LLM_ANSWER_KEY_BASE_URL,
                api_key=settings.OPENAI_LLM_ANSWER_KEY_API_KEY,
                timeout_seconds=float(settings.LLM_ITEM_LABELER_TIMEOUT_SECONDS),
                sleeper=sleeper,
                max_attempts=1,
            ),
        ),
        labeler_source=PythonDocxLabelerMarkdown(),
        exchange=exchange,
        profile=build_luna_docx_conversion_profile(settings),
        progress=progress,
        uow=uow,
        families_per_batch=settings.LLM_DOCX_BATCH_FAMILIES,
        enabled=settings.LLM_ANSWER_KEY_ENABLED,
    )
