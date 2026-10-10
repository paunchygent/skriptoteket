"""Native exam adapter for the Exam.net-oriented PDF target.

Purpose:
    Build the fail-closed Exam.net PDF document plan from a native exam
    document by adapting items into source-neutral PDF item semantics and
    delegating target policy to the existing Exam.net PDF item strategies.

Relationships:
    - Consumes `domain.curated_apps.exam_workspace.native_exam_document`.
    - Reuses the neutral types in
      `domain.curated_apps.exam_conversion.exam_pdf_item_semantics`, the
      default strategy registry in `examnet_pdf_item_strategies`, and the
      document assembly in `digiexam_examnet_pdf_html`.
    - Mirrors the fail-closed coordination of
      `domain.curated_apps.exam_conversion.digiexam_examnet_pdf`.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from html import escape
from types import MappingProxyType

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfAssetFile,
    DigiExamExamNetPdfDocument,
    DigiExamExamNetPdfItemRender,
    DigiExamExamNetPdfStatus,
    DigiExamExamNetPdfWarning,
    DigiExamExamNetPdfWarningCode,
    blocking_examnet_pdf_warnings,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_html import (
    build_examnet_pdf_html,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_prompt import (
    prompt_has_renderable_content,
)
from skriptoteket.domain.curated_apps.exam_conversion.exam_pdf_item_semantics import (
    PdfExamAnswerKeySemantics,
    PdfExamGapAnswerSemantics,
    PdfExamGapSemantics,
    PdfExamItemKind,
    PdfExamItemSemantics,
    PdfExamOptionSemantics,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_pdf_item_strategies import (
    DEFAULT_EXAMNET_PDF_ITEM_STRATEGY_REGISTRY,
    DEFAULT_EXAMNET_PDF_TARGET_PROFILE_CONTEXT,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKeyOrigin,
    NativeExamDocument,
    NativeExamItem,
    NativeExamItemKind,
    NativeGapSegment,
    NativeTextSegment,
)

NO_PDF_EXPORT_ASSETS: Mapping[str, bytes] = MappingProxyType({})

_GAP_PLACEHOLDER_HTML = '<span class="gap-placeholder">[____]</span>'
_ASSET_SUFFIX_BY_MEDIA_TYPE = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
}
_PDF_ITEM_KIND_BY_NATIVE_KIND = {
    NativeExamItemKind.FREE_TEXT: PdfExamItemKind.OPEN_RESPONSE,
    NativeExamItemKind.SINGLE_CHOICE: PdfExamItemKind.SINGLE_CHOICE,
    NativeExamItemKind.MULTIPLE_RESPONSE: PdfExamItemKind.MULTIPLE_RESPONSE,
    NativeExamItemKind.GAP_FILL: PdfExamItemKind.GAP_OPEN_CLOZE,
}
# Defensive second guard: `native_export_blockers` (reason `missing_answer_key`)
# already blocks keyed items without a key before export. An unkeyed keyed item
# must never be exported; Exam.net would drop or mis-handle it.
_UNKEYED_ORIGINS = frozenset({NativeAnswerKeyOrigin.ABSENT, NativeAnswerKeyOrigin.NOT_APPLICABLE})


def native_exam_to_pdf_document(
    document: NativeExamDocument,
    *,
    assets_by_id: Mapping[str, bytes] = NO_PDF_EXPORT_ASSETS,
) -> DigiExamExamNetPdfDocument:
    """Build an Exam.net PDF-converter HTML plan from a native exam document."""

    asset_files, asset_paths_by_id, asset_warnings = _prepare_assets(document, assets_by_id)
    if asset_warnings:
        return _blocked(asset_warnings)

    items: list[DigiExamExamNetPdfItemRender] = []
    warnings: list[DigiExamExamNetPdfWarning] = []
    for item in document.items:
        item_render, item_warnings = _render_item(
            item=item,
            asset_paths_by_id=asset_paths_by_id,
        )
        warnings.extend(item_warnings)
        if item_render is not None:
            items.append(item_render)
    if blocking_examnet_pdf_warnings(tuple(warnings)):
        return _blocked(tuple(warnings))

    return DigiExamExamNetPdfDocument(
        status=DigiExamExamNetPdfStatus.SUCCESS,
        html=build_examnet_pdf_html(source_filename=document.title, items=tuple(items)),
        asset_files=asset_files,
        warnings=tuple(warnings),
    )


def _render_item(
    *,
    item: NativeExamItem,
    asset_paths_by_id: Mapping[str, str],
) -> tuple[DigiExamExamNetPdfItemRender | None, tuple[DigiExamExamNetPdfWarning, ...]]:
    if item.points is None:
        return None, (
            DigiExamExamNetPdfWarning(
                code=DigiExamExamNetPdfWarningCode.MISSING_POINT_VALUE,
                message=f"Item {item.item_id} has no point value.",
                item_id=item.item_id,
            ),
        )

    prompt_html = _prompt_html(item=item, asset_paths_by_id=asset_paths_by_id)
    if not prompt_has_renderable_content(prompt_html):
        return None, (
            DigiExamExamNetPdfWarning(
                code=DigiExamExamNetPdfWarningCode.EMPTY_PROMPT,
                message=f"Item {item.item_id} has no renderable prompt.",
                item_id=item.item_id,
            ),
        )

    item_semantics = _pdf_item_semantics(item=item, points=item.points, prompt_html=prompt_html)
    strategy_result = DEFAULT_EXAMNET_PDF_ITEM_STRATEGY_REGISTRY.render(
        item=item_semantics,
        context=DEFAULT_EXAMNET_PDF_TARGET_PROFILE_CONTEXT,
    )
    return strategy_result.item, strategy_result.warnings


def _pdf_item_semantics(
    *,
    item: NativeExamItem,
    points: int | float,
    prompt_html: str,
) -> PdfExamItemSemantics:
    return PdfExamItemSemantics(
        item_id=item.item_id,
        sequence=item.sequence,
        kind=_PDF_ITEM_KIND_BY_NATIVE_KIND[item.kind],
        points=points,
        prompt_html=prompt_html,
        source_item_type_label=item.kind.value,
        options=tuple(
            PdfExamOptionSemantics(option_id=_choice_number(choice.choice_id), text=choice.text)
            for choice in item.choices
        ),
        gaps=tuple(PdfExamGapSemantics(gap_id=gap.gap_id) for gap in item.gaps),
        answer_key=PdfExamAnswerKeySemantics(
            available=item.answer_key.origin not in _UNKEYED_ORIGINS,
            correct_option_ids=tuple(
                _choice_number(choice_id) for choice_id in item.answer_key.correct_choice_ids
            ),
            correct_gap_answers=tuple(
                PdfExamGapAnswerSemantics(gap_id=gap.gap_id, value=value)
                for gap in item.gaps
                for value in gap.accepted_values
            ),
        ),
    )


def _prompt_html(*, item: NativeExamItem, asset_paths_by_id: Mapping[str, str]) -> str:
    paragraphs: list[str] = []
    for paragraph in item.body:
        parts: list[str] = []
        for segment in paragraph.segments:
            if isinstance(segment, NativeTextSegment):
                parts.append(escape(segment.text))
            elif isinstance(segment, NativeGapSegment):
                parts.append(_GAP_PLACEHOLDER_HTML)
            else:
                parts.append(_image_html(segment.asset_id, asset_paths_by_id))
        paragraphs.append(f"<p>{''.join(parts)}</p>")
    return "".join(paragraphs)


def _image_html(asset_id: str, asset_paths_by_id: Mapping[str, str]) -> str:
    relative_path = asset_paths_by_id[asset_id]
    return (
        '<img class="prompt-image" '
        f'src="{escape(relative_path, quote=True)}" '
        f'alt="Bild {escape(asset_id, quote=True)}">'
    )


def _prepare_assets(
    document: NativeExamDocument,
    assets_by_id: Mapping[str, bytes],
) -> tuple[
    tuple[DigiExamExamNetPdfAssetFile, ...],
    Mapping[str, str],
    tuple[DigiExamExamNetPdfWarning, ...],
]:
    asset_files: list[DigiExamExamNetPdfAssetFile] = []
    paths_by_id: dict[str, str] = {}
    warnings: list[DigiExamExamNetPdfWarning] = []
    for asset in document.assets:
        payload = assets_by_id.get(asset.asset_id)
        if payload is None:
            warnings.append(
                DigiExamExamNetPdfWarning(
                    code=DigiExamExamNetPdfWarningCode.EMBEDDED_ASSET_PAYLOAD_MISSING,
                    message=f"Asset {asset.asset_id} has no renderable payload.",
                    item_id=None,
                )
            )
            continue
        if len(payload) != asset.byte_length or hashlib.sha256(payload).hexdigest() != asset.sha256:
            warnings.append(
                DigiExamExamNetPdfWarning(
                    code=DigiExamExamNetPdfWarningCode.EMBEDDED_ASSET_PAYLOAD_INVALID,
                    message=f"Asset {asset.asset_id} payload does not match document metadata.",
                    item_id=None,
                )
            )
            continue
        relative_path = f"assets/{asset.asset_id}{_ASSET_SUFFIX_BY_MEDIA_TYPE[asset.media_type]}"
        asset_files.append(
            DigiExamExamNetPdfAssetFile(
                asset_id=asset.asset_id,
                relative_path=relative_path,
                media_type=asset.media_type,
                payload=payload,
            )
        )
        paths_by_id[asset.asset_id] = relative_path
    return tuple(asset_files), paths_by_id, tuple(warnings)


def _choice_number(choice_id: str) -> int:
    return int(choice_id.removeprefix("choice_"))


def _blocked(
    warnings: tuple[DigiExamExamNetPdfWarning, ...],
) -> DigiExamExamNetPdfDocument:
    return DigiExamExamNetPdfDocument(
        status=DigiExamExamNetPdfStatus.BLOCKED,
        html="",
        asset_files=(),
        warnings=warnings,
    )
