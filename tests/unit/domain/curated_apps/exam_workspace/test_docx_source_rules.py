"""Source-structure rules judged against real recorded model output and real corpus chunks."""

import json
import re
from pathlib import Path

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
    ProducedMetadata,
    ProducedSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    content_rule_violation,
    definition_context,
    item_rule_violation,
    opening_heading,
    points_line,
    title_rule_violation,
    with_accepted_forms,
    with_printed_hints,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)

_FIXTURES = Path("tests/fixtures/exam_conversion")


def _chunks(docx: str) -> dict[str, DocxChunk]:
    chunks = PythonDocxExamChunker().chunk(
        content=(_FIXTURES / f"docx_corpus/{docx}.docx").read_bytes()
    )
    return {chunk.anchor: chunk for chunk in chunks}


def _items(recording: str) -> list[ProducedItem]:
    content = json.loads((_FIXTURES / recording).read_text())
    return [ProducedItem.model_validate(raw) for raw in content["items"]]


def _violations(recording: str, docx: str) -> dict[tuple[str, ...], str | None]:
    chunks = _chunks(docx)
    return {
        item.source_anchors: item_rule_violation(item, [chunks[a] for a in item.source_anchors])
        for item in _items(recording)
    }


def test_blank_marker_without_gap_or_options_violates_and_other_items_pass():
    violations = _violations(
        "bf26_diagnostic_grammar_docx_build_response.json",
        "bf26_diagnostic_grammar_test_ht26_med_facit",
    )
    blank_anchors = {"body:0043", "body:0117", "body:0123", "body:0181", "body:0217", "body:0223"}
    flagged = {anchors for anchors, violation in violations.items() if violation is not None}
    assert {a for anchors in flagged for a in anchors} == blank_anchors
    for anchors in flagged:
        assert "blank marker" in (violations[anchors] or "")
    assert len(flagged) == len(blank_anchors)


@pytest.mark.parametrize(
    ("recording", "docx"),
    [
        (
            "svenska_2_grammatik_variant_1_docx_build_response.json",
            "svenska_2_grammatik_omprov_variant_1_med_facit",
        ),
        (
            "svenska_2_grammatik_variant_2_docx_build_response.json",
            "svenska_2_grammatik_omprov_variant_2_med_facit",
        ),
    ],
)
def test_facit_that_splits_units_requires_free_text_and_other_items_pass(recording: str, docx: str):
    violations = _violations(recording, docx)
    flagged = {anchors[0]: v for anchors, v in violations.items() if v is not None}
    restated = {anchor for anchor, v in flagged.items() if "restates context" in v}
    assert set(flagged) - restated == {"body:0008", "body:0045"}
    assert all("free_text" in flagged[anchor] for anchor in set(flagged) - restated)
    assert len(violations) - len(set(flagged) - restated) == 6


@pytest.mark.parametrize(
    ("recording", "docx"),
    [
        (
            "svenska_2_grammatik_variant_1_docx_build_response.json",
            "svenska_2_grammatik_omprov_variant_1_med_facit",
        ),
        (
            "svenska_2_grammatik_variant_2_docx_build_response.json",
            "svenska_2_grammatik_omprov_variant_2_med_facit",
        ),
    ],
)
def test_gap_for_a_clause_its_line_already_shows_violates_and_gold_gap_counts_follow(
    recording: str, docx: str
):
    """A recorded round gapped the clause each line prints beside its new facit fields."""
    violations = _violations(recording, docx)
    restated = {anchors for anchors, v in violations.items() if v and "restates context" in v}
    assert len(restated) == 1
    (anchors,) = restated
    gold = json.loads((_FIXTURES / "docx_corpus/gold" / f"{docx}.json").read_text())
    gold_item = next(i for i in gold["items"] if i["source_label"].endswith(" 6"))
    item = next(i for i in _items(recording) if i.source_anchors == anchors)
    gaps = sum(1 for p in item.body for s in p.segments if s.kind == "gap")
    assert gaps > len(gold_item["gaps"])


def test_gaps_beyond_blank_markers_violate_as_facit_created_gaps():
    violations = _violations(
        "bf26_english_1_docx_build_response.json", "bf26_english_1_unit_test_kap_1_2_med_facit"
    )
    flagged = {anchors: v for anchors, v in violations.items() if v is not None}
    assert set(flagged) == {("body:0121",)}
    assert "never creates a gap" in (flagged[("body:0121",)] or "")


@pytest.mark.parametrize(
    ("recording", "docx"),
    [
        (
            "svenska_2_kursavslutande_prov_docx_build_response.json",
            "svenska_2_kursavslutande_prov_med_facit",
        ),
        (
            "sa24_solid_gold_3_docx_build_response_round1.json",
            "sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit",
        ),
        (
            "chapter_4_poetry_docx_build_response.json",
            "chapter_4_poetry_and_lyrics_quiz_med_facit",
        ),
    ],
)
def test_items_whose_gaps_match_source_slots_pass(recording: str, docx: str):
    violations = _violations(recording, docx)
    assert violations
    assert {anchors: v for anchors, v in violations.items() if v is not None} == {}


def test_review_outcome_never_violates():
    chunks = _chunks("svenska_2_grammatik_omprov_variant_1_med_facit")
    item = next(
        item
        for item in _items("svenska_2_grammatik_variant_1_docx_build_response.json")
        if item.source_anchors[0] == "body:0008"
    )
    sources = [chunks[a] for a in item.source_anchors]
    assert item_rule_violation(item, sources) is not None
    review = item.model_copy(update={"outcome": "review", "review_reason": "x"})
    assert item_rule_violation(review, sources) is None


def _title(text: str, *anchors: str) -> ProducedMetadata:
    return ProducedMetadata.model_validate({"text": text, "source_anchors": list(anchors)})


def _title_violation(chunks: dict[str, DocxChunk], title: ProducedMetadata) -> str | None:
    heading = opening_heading(tuple(chunks.values()))
    return title_rule_violation(title, [chunks[a] for a in title.source_anchors], heading)


def test_title_copying_opening_heading_verbatim_passes():
    chunks = _chunks("sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit")
    assert _title_violation(chunks, _title(chunks["body:0002"].text, "body:0002")) is None


def test_title_with_words_beyond_its_source_violates():
    chunks = _chunks("sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit")
    title = _title(f"{chunks['body:0002'].text} extra", "body:0002")
    assert _title_violation(chunks, title) is not None


def test_title_anchored_away_from_opening_heading_names_the_heading():
    chunks = _chunks("sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit")
    violation = _title_violation(chunks, _title(chunks["body:0003"].text, "body:0003"))
    assert violation is not None
    assert "body:0002" in violation


def test_title_joining_opening_heading_and_next_chunk_with_separator_passes():
    chunks = _chunks("svenska_2_grammatik_omprov_variant_1_med_facit")
    text = f"{chunks['body:0002'].text} — {chunks['body:0003'].text}"
    assert _title_violation(chunks, _title(text, "body:0002", "body:0003")) is None


def _gaps(item: ProducedItem) -> list[list[str]]:
    return [list(s.accepted_values) for p in item.body for s in p.segments if s.kind == "gap"]


def _gold_gaps(docx: str) -> list[list[list[str]]]:
    gold = json.loads((_FIXTURES / f"docx_corpus/gold/{docx}.json").read_text())
    return [[gap["accepted_values"] for gap in item.get("gaps", [])] for item in gold["items"]]


def _widened(recording: str, docx: str) -> list[tuple[ProducedItem, ProducedItem]]:
    chunks = PythonDocxExamChunker().chunk(
        content=(_FIXTURES / f"docx_corpus/{docx}.docx").read_bytes()
    )
    return [
        (item, with_accepted_forms(item, definition_context(chunks, item.source_anchors)))
        for item in _items(recording)
    ]


def test_facit_term_defined_in_the_section_instruction_also_accepts_its_short_form():
    docx = "svenska_2_grammatik_omprov_variant_2_med_facit"
    pairs = _widened("svenska_2_grammatik_variant_2_docx_build_response.json", docx)
    gold = _gold_gaps(docx)
    # The comparator pairs recorded and gold items by position.
    item, widened = pairs[3]
    assert item.source_anchors[0] == "body:0037"
    for original, values, gold_values in zip(_gaps(item), _gaps(widened), gold[3], strict=True):
        assert len(values) > len(original)
        # Every gold answer is accepted, including each part of a slash-joined facit form,
        # and nothing outside gold is added.
        assert {g.casefold() for g in gold_values} <= {v.casefold() for v in values}
        assert {v.casefold() for v in values} <= {g.casefold() for g in gold_values}
    # Short forms listed without "=" define nothing.
    item, widened = pairs[1]
    assert item.source_anchors[0] == "body:0016"
    assert _gaps(widened) == _gaps(item)


def test_facit_already_in_short_form_gains_no_term():
    docx = "svenska_2_kursavslutande_prov_med_facit"
    chunks = _chunks(docx)
    # The questions' own instructions define their labels with "=".
    assert sum(chunks[a].text.count("=") for a in chunks) >= 6
    pairs = _widened("svenska_2_kursavslutande_prov_docx_build_response.json", docx)
    assert [_gaps(widened) for _, widened in pairs] == [_gaps(item) for item, _ in pairs]


def test_term_added_beside_a_short_form_facit_is_kept():
    """A live round added each defined term next to the short form the inline facit writes."""
    chunks = PythonDocxExamChunker().chunk(
        content=(
            _FIXTURES / "docx_corpus/svenska_2_kursavslutande_prov_med_facit.docx"
        ).read_bytes()
    )
    by_anchor = {chunk.anchor: chunk for chunk in chunks}
    item = next(
        item
        for item in _items("svenska_2_kursavslutande_prov_docx_build_response.json")
        if item.source_anchors[0] == "body:0061"
    )
    instruction = by_anchor["body:0062"].text
    assert instruction.count(" = ") == 3

    def defined_term(short: str) -> str:
        match = re.search(re.escape(short) + r" = (\w+)", instruction)
        assert match is not None
        return match.group(1)

    padded = item.model_copy(
        update={
            "body": tuple(
                p.model_copy(
                    update={
                        "segments": tuple(
                            s.model_copy(
                                update={
                                    "accepted_values": (
                                        *s.accepted_values,
                                        *(defined_term(v) for v in s.accepted_values),
                                    )
                                }
                            )
                            if s.kind == "gap"
                            else s
                            for s in p.segments
                        )
                    }
                )
                for p in item.body
            )
        }
    )
    assert padded != item

    widened = with_accepted_forms(padded, definition_context(chunks, item.source_anchors))

    assert _gaps(widened) == _gaps(padded)


def test_facit_printed_with_a_typographic_apostrophe_also_accepts_the_keyboard_form():
    """The source prints the facit and its "also accepted" form with the same curly apostrophe."""
    docx = "bf26_english_1_unit_test_kap_1_2_med_facit"
    chunks = _chunks(docx)
    pairs = _widened(f"docx_build_v5/{docx}/round1.json", docx)
    gold = _gold_gaps(docx)
    curly = [
        index
        for index, (item, _) in enumerate(pairs)
        if any("\u2019" in value for gap in _gaps(item) for value in gap)
    ]
    assert curly
    for index in curly:
        item, widened = pairs[index]
        facit = " ".join(chunks[a].text for a in chunks if a not in item.source_anchors)
        assert all(value in facit for gap in _gaps(item) for value in gap)
        for values, gold_values in zip(_gaps(widened), gold[index], strict=True):
            assert set(gold_values) <= set(values)


_HINT_DOCX = "sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit"
_HINT_RECORDING = f"docx_build_v6/{_HINT_DOCX}/round1.json"


def _recorded(recording: str, anchor: str) -> ProducedItem:
    return next(item for item in _items(recording) if item.source_anchors[0] == anchor)


def _body_segments(item: ProducedItem) -> list[ProducedSegment]:
    return [segment for paragraph in item.body for segment in paragraph.segments]


def _text_of(item: ProducedItem) -> str:
    return "".join(s.text or "" for s in _body_segments(item))


def _gap_hints(item: ProducedItem) -> list[str | None]:
    return [s.hint for s in _body_segments(item) if s.kind == "gap"]


def _with_hints(item: ProducedItem, hints: list[str]) -> ProducedItem:
    """The item with each gap's hint set, in gap order."""
    pending = iter(hints)
    paragraphs = tuple(
        paragraph.model_copy(
            update={
                "segments": tuple(
                    segment.model_copy(update={"hint": next(pending)})
                    if segment.kind == "gap"
                    else segment
                    for segment in paragraph.segments
                )
            }
        )
        for paragraph in item.body
    )
    return item.model_copy(update={"body": paragraphs})


def test_cue_the_source_prints_in_brackets_becomes_bracketed_text_after_its_gap():
    chunks = _chunks(_HINT_DOCX)
    item = _recorded(_HINT_RECORDING, "body:0034")
    (cue,) = _gap_hints(item)
    assert cue
    sources = [chunks[a] for a in item.source_anchors]
    assert f"({cue})" in sources[0].text
    assert cue not in _text_of(item)

    folded = with_printed_hints(item, sources)

    before, after = _body_segments(item), _body_segments(folded)
    assert after[0].kind == "gap"
    assert after[0].hint is None
    assert after[0].accepted_values == before[0].accepted_values
    assert (after[1].kind, after[1].text) == ("text", f" ({cue})")
    assert after[2:] == before[1:]


def test_cue_already_printed_in_the_paragraph_is_not_added_twice():
    chunks = _chunks(_HINT_DOCX)
    item = _recorded(_HINT_RECORDING, "body:0034")
    sources = [chunks[a] for a in item.source_anchors]
    (cue,) = _gap_hints(item)
    assert cue

    folded = with_printed_hints(item, sources)
    refolded = with_printed_hints(_with_hints(folded, [cue]), sources)

    assert _text_of(refolded) == _text_of(folded)
    assert _text_of(refolded).count(f"({cue})") == 1
    assert _gap_hints(refolded) == [None]


def test_every_gap_cue_the_text_already_prints_is_folded_away_without_new_text():
    docx = "bf26_diagnostic_grammar_test_ht26_med_facit"
    chunks = _chunks(docx)
    item = _recorded(f"docx_build_v6/{docx}/round1.json", "body:0017")
    sources = [chunks[a] for a in item.source_anchors]
    cues = [cue for cue in re.findall(r"\(([^()]+)\)", sources[0].text) if cue in _text_of(item)]
    assert len(cues) == len(_gap_hints(item)) == 2
    assert _gap_hints(item) == [None, None]

    folded = with_printed_hints(_with_hints(item, cues), sources)

    assert _body_segments(folded) == _body_segments(item)


def test_cue_the_source_does_not_bracket_is_appended_as_plain_text():
    chunks = _chunks(_HINT_DOCX)
    item = _recorded(_HINT_RECORDING, "body:0034")
    sources = [chunks[a] for a in item.source_anchors]
    plain = sources[0].text.split(".", 1)[0] + "."
    assert plain in sources[0].text
    assert f"({plain})" not in sources[0].text

    folded = with_printed_hints(_with_hints(item, [plain]), sources)

    assert _body_segments(folded)[1].text == f" {plain}"
    assert _gap_hints(folded) == [None]


_BUILD_V6 = _FIXTURES / "docx_build_v6"
_V6_EXAMS = sorted(path.name for path in _BUILD_V6.iterdir())
# Items the model converted that the content rule rejects; the next round receives the message.
_KNOWN_DROPS = {
    "bf26_diagnostic_grammar_test_ht26_med_facit": "body:0078",
    "chapter_4_poetry_and_lyrics_quiz_med_facit": "body:0130",
}


def _converted(stem: str) -> list[tuple[ProducedItem, list[DocxChunk]]]:
    chunks = _chunks(stem)
    return [
        (item, [chunks[a] for a in item.source_anchors])
        for item in _items(f"docx_build_v6/{stem}/round1.json")
        if item.outcome == "converted"
    ]


@pytest.mark.parametrize("stem", _V6_EXAMS)
def test_converted_items_keep_every_source_word_except_the_known_drops(stem: str):
    converted = _converted(stem)
    assert converted
    flagged = {
        item.source_anchors: violation
        for item, sources in converted
        if (violation := content_rule_violation(item, sources))
    }

    drop = _KNOWN_DROPS.get(stem)
    if drop is None:
        assert flagged == {}
    else:
        ((anchors, violation),) = flagged.items()
        assert drop in anchors
        assert drop in violation


def _occurrences(item: ProducedItem, word: str) -> int:
    answers = [v for s in _body_segments(item) for v in s.accepted_values]
    answers.extend(choice.text for choice in item.choices)
    answers.extend(pair.right for pair in item.match_pairs)
    texts = [
        item.title or "",
        *(s.text or "" for s in _body_segments(item)),
        *item.match_left,
        *item.match_right,
        *answers,
    ]
    return sum(re.findall(r"\w+", text.casefold()).count(word) for text in texts)


def _without_one_word(item: ProducedItem) -> ProducedItem:
    """The item with one word removed that nothing else in the item shows."""
    for paragraph_index, paragraph in enumerate(item.body):
        for segment_index, segment in enumerate(paragraph.segments):
            if segment.kind != "text":
                continue
            text = segment.text or ""
            for match in re.finditer(r"\w+", text):
                word = match.group().casefold()
                if len(word) < 2 or word.isdigit() or _occurrences(item, word) != 1:
                    continue
                shortened = " ".join((text[: match.start()] + text[match.end() :]).split())
                if not shortened:
                    continue
                segments = list(paragraph.segments)
                segments[segment_index] = segment.model_copy(update={"text": shortened})
                paragraphs = list(item.body)
                paragraphs[paragraph_index] = paragraph.model_copy(
                    update={"segments": tuple(segments)}
                )
                return item.model_copy(update={"body": tuple(paragraphs)})
    raise AssertionError("no word unique to the item's text")


@pytest.mark.parametrize("stem", [s for s in _V6_EXAMS if s not in _KNOWN_DROPS])
def test_removing_one_word_from_a_passing_item_makes_it_violate(stem: str):
    item, sources = next(
        (item, sources)
        for item, sources in _converted(stem)
        if any(
            s.kind == "text" and s.text and len(s.text.split()) > 2 for s in _body_segments(item)
        )
    )
    assert content_rule_violation(item, sources) is None

    violation = content_rule_violation(_without_one_word(item), sources)

    assert violation is not None
    assert "omits 1 word(s)" in violation
    assert any(chunk.anchor in violation for chunk in sources)


@pytest.mark.parametrize(
    ("docx", "anchor"),
    [
        ("svenska_2_grammatik_omprov_variant_1_med_facit", "body:0004"),
        ("svenska_2_grammatik_omprov_variant_1_med_facit", "body:0013"),
        ("bf26_diagnostic_grammar_test_ht26_med_facit", "body:0003"),
        ("bf26_english_1_unit_test_kap_1_2_med_facit", "body:0003"),
    ],
)
def test_total_and_points_lines_are_points_lines(docx: str, anchor: str):
    text = _chunks(docx)[anchor].text
    assert text.startswith(("Total:", "Poäng:"))
    assert points_line(text)


@pytest.mark.parametrize(
    ("docx", "anchor"),
    [
        ("bf26_english_1_unit_test_kap_1_2_med_facit", "body:0058"),
        ("chapter_4_poetry_and_lyrics_quiz_med_facit", "body:0129"),
    ],
)
def test_sentence_or_heading_that_mentions_points_is_not_a_points_line(docx: str, anchor: str):
    text = _chunks(docx)[anchor].text
    assert "point" in text
    assert not points_line(text)
