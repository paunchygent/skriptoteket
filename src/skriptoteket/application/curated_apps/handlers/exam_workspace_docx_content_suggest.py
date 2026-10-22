"""Content-tag suggestions for one DOCX conversion (TASK-SKRIPT-41-01-03).

The suggestion is optional work running beside labeling and conversion: it resolves
the manifest's course, classifies every labeled question against that course's content
catalog, and records the door's first refusal on the run without failing the conversion.
Provider timeouts never hold up an otherwise complete exam; the pipeline cancels and
joins this work when the conversion finishes.
"""

from __future__ import annotations

import structlog

from skriptoteket.application.curated_apps.exam_content_tagging import (
    ExamContentTagSuggester,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_run import (
    DocxConversionRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_header import (
    resolve_header_course,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import ExamManifest
from skriptoteket.domain.curated_apps.exam_workspace.exam_content_tags import (
    load_exam_content_catalog,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_course_catalog import (
    load_exam_course_catalog,
)
from skriptoteket.domain.llm_door import AiDailyLimitReached, AiDoorBusy, AiJobOverageCapReached
from skriptoteket.protocols.item_type_labeler import (
    ContentTagClassificationRequest,
    LabelingRequest,
)

logger = structlog.get_logger(__name__)


async def suggest_content_tags(
    run: DocxConversionRun,
    manifest: ExamManifest,
    request: LabelingRequest,
    content_classifier: ExamContentTagSuggester | None,
) -> None:
    """Suggest content tags for the conversion without ever failing it.

    A refusal records the run's first limit; a busy door drops the tags with a warning,
    since optional work never fails the conversion; any other failure only logs.
    """
    if run.ai_limit is not None:
        return
    try:
        course_anchors = {entry.anchor for entry in manifest.header if entry.kind == "course"}
        hint = " ".join(
            chunk.text.strip() for chunk in run.job.chunks if chunk.anchor in course_anchors
        )
        course = resolve_header_course(hint, run.job.course_key, load_exam_course_catalog().courses)
        if course is None or content_classifier is None:
            return
        run.content_tags = await content_classifier.suggest(
            request=ContentTagClassificationRequest(
                job_id=request.job_id,
                items=request.items,
                content_items=load_exam_content_catalog()[course.key],
                caller=run.job.caller,
            )
        )
    except (AiDailyLimitReached, AiJobOverageCapReached) as exc:
        run.note_limit(exc)
    except AiDoorBusy:
        logger.warning(
            "Import content suggestions dropped at a busy door; conversion continues",
            job_id=str(run.job.job_id),
        )
    except Exception:
        logger.exception(
            "Import content suggestions failed; conversion continues",
            job_id=str(run.job.job_id),
        )
