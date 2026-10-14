"""Model-readable DOCX source with positioned picture references, never picture bytes.

Grouping and conversion read the same picture positions. An unavailable picture is
named explicitly, not hidden by an empty drawing chunk or presented as a real image.
"""

from html import escape

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk


def marked_source_text(chunk: DocxChunk) -> str:
    markers = [
        (image.marked_offset, f'<image asset_id="{image.asset_id}"/>') for image in chunk.images
    ]
    markers.extend(
        (
            image.marked_offset,
            f'<missing-image reference="{escape(image.reference, quote=True)}" '
            f'media_type="{escape(image.media_type, quote=True)}"/>',
        )
        for image in chunk.missing_images
    )
    parts: list[str] = []
    start = 0
    for offset, marker in sorted(markers, key=lambda entry: entry[0]):
        if not start <= offset <= len(chunk.marked_text):
            raise ValueError("Source image offset is outside the marked text")
        parts.extend((chunk.marked_text[start:offset], marker))
        start = offset
    parts.append(chunk.marked_text[start:])
    return "".join(parts)
