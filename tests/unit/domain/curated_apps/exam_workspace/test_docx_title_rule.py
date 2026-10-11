"""The title rule judged against real corpus opening headings."""

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedMetadata
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    opening_heading,
    title_rule_violation,
)
from tests.unit.domain.curated_apps.exam_workspace.source_rules_test_support import (
    chunks_by_anchor,
)


def _title(text: str, *anchors: str) -> ProducedMetadata:
    return ProducedMetadata.model_validate({"text": text, "source_anchors": list(anchors)})


def _title_violation(chunks: dict[str, DocxChunk], title: ProducedMetadata) -> str | None:
    heading = opening_heading(tuple(chunks.values()))
    return title_rule_violation(title, [chunks[a] for a in title.source_anchors], heading)


def test_title_copying_opening_heading_verbatim_passes():
    chunks = chunks_by_anchor("sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit")
    assert _title_violation(chunks, _title(chunks["body:0002"].text, "body:0002")) is None


def test_title_with_words_beyond_its_source_violates():
    chunks = chunks_by_anchor("sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit")
    title = _title(f"{chunks['body:0002'].text} extra", "body:0002")
    assert _title_violation(chunks, title) is not None


def test_title_anchored_away_from_opening_heading_names_the_heading():
    chunks = chunks_by_anchor("sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit")
    violation = _title_violation(chunks, _title(chunks["body:0003"].text, "body:0003"))
    assert violation is not None
    assert "body:0002" in violation


def test_title_joining_opening_heading_and_next_chunk_with_separator_passes():
    chunks = chunks_by_anchor("svenska_2_grammatik_omprov_variant_1_med_facit")
    text = f"{chunks['body:0002'].text} — {chunks['body:0003'].text}"
    assert _title_violation(chunks, _title(text, "body:0002", "body:0003")) is None
