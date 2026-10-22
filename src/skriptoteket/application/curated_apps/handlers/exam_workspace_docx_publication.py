"""Prepare provisional and final DOCX documents for workspace publication.

Both publications attach the original retry sources, import records and source assets
before applying the document header. Final publication also resolves content tags to
native item identities and reports assembly checks. Scheduling and accepting batch
state belong to the pipeline; preparation here does not replace the run's build state.
"""

from __future__ import annotations

import time
from dataclasses import replace

import structlog

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_assembly import (
    assembly_check,
    contexts_owned_by_question,
    conversion_update,
    exam_metadata_anchors,
    exam_wide_anchors,
    governed_anchors,
    provisional_result,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_run import (
    DocxConversionOutcome,
    DocxConversionRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildEvent,
    DocxBuildResult,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import QuestionFamily
from skriptoteket.domain.curated_apps.exam_workspace.docx_header import apply_header
from skriptoteket.domain.curated_apps.exam_workspace.docx_import_records import (
    with_docx_import_records,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import ExamManifest
from skriptoteket.domain.curated_apps.exam_workspace.exam_course_catalog import (
    load_exam_course_catalog,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_source import (
    retry_sources_by_anchor,
    with_retry_sources,
    with_source_assets,
)
from skriptoteket.protocols.docx_conversion_progress import ConversionUpdate

logger = structlog.get_logger(__name__)


def _with_source_evidence(
    run: DocxConversionRun,
    result: DocxBuildResult,
    families: tuple[QuestionFamily, ...],
    events: tuple[DocxBuildEvent, ...],
) -> DocxBuildResult:
    """Apply the same source, import-history and asset rules to either publication."""
    sources = retry_sources_by_anchor(
        families=families,
        own_anchors=run.own_anchors,
        owned_contexts=contexts_owned_by_question(run.contexts, families),
        key_anchors=run.key_anchors,
        chunks=run.job.chunks,
        label_kinds=run.label_kinds,
    )
    document, assets_by_id = with_source_assets(
        document=with_docx_import_records(
            with_retry_sources(result.document, sources),
            chunks=run.job.chunks,
            events=events,
        ),
        chunks=run.job.chunks,
        assets_by_id=result.assets_by_id,
    )
    return replace(result, document=document, assets_by_id=assets_by_id)


def provisional_publication(
    run: DocxConversionRun,
    trial: DocxBuildState,
    families: tuple[QuestionFamily, ...],
    filled: tuple[str, ...],
    pending: tuple[str, ...],
) -> ConversionUpdate:
    """Prepare a batch's trial state without accepting it into the live run."""
    result = provisional_result(
        trial,
        families,
        frozenset(pending),
        governed_anchors(run.contexts, families),
        exam_wide_anchors(run.contexts, families),
        exam_metadata_anchors(run.contexts),
    )
    result = _with_source_evidence(run, result, families, tuple(trial.events))
    document = result.document
    if run.manifest is not None:
        document = apply_header(
            document,
            run.manifest,
            run.job.chunks,
            course_key=run.job.course_key,
            courses=load_exam_course_catalog().courses,
        ).document
    return conversion_update(document, families, filled, pending, assets_by_id=result.assets_by_id)


def final_publication(
    run: DocxConversionRun, manifest: ExamManifest | None
) -> DocxConversionOutcome:
    """Publish the complete document, final tags, diagnostics and assembly timing."""
    started = time.monotonic()
    result = run.state.result(
        governed_anchors(run.contexts, run.families),
        tuple(f.question_anchors for f in run.families),
        exam_wide_anchors(run.contexts, run.families),
        exam_metadata_anchors(run.contexts),
    )
    result = _with_source_evidence(run, result, run.families, result.events)
    header = apply_header(
        result.document,
        manifest,
        run.job.chunks,
        course_key=run.job.course_key,
        courses=load_exam_course_catalog().courses,
    )
    document = header.document
    update = conversion_update(
        document, run.families, tuple(run.filled), (), assets_by_id=result.assets_by_id
    )
    tags = tuple(
        tag.model_copy(
            update={
                "question_ids": tuple(
                    dict.fromkeys(
                        item_id
                        for question_id in tag.question_ids
                        for item_id in update.item_ids.get(question_id, ())
                    )
                )
            }
        )
        for tag in run.content_tags
    )
    document = document.model_copy(
        update={"header": document.header.model_copy(update={"tags": tags})}
    )
    update = replace(update, document=document)
    checks = assembly_check(document, manifest, run.families, update) if manifest else ()
    run.timed("assembly", started)
    return DocxConversionOutcome(
        result=replace(
            result,
            document=document,
            events=(*result.events, *checks),
            timings=tuple(run.timings),
            ai_limit=run.ai_limit,
        ),
        update=update,
        ai_limit=run.ai_limit,
        limit_code=run.limit_code,
    )
