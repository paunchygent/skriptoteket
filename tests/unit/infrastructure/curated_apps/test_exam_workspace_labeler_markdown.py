"""Challenge D14 labeler markdown against the original corpus XML, without gold input."""

from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import pytest

from scripts.item_type_labeler_live.__main__ import corpus_items
from scripts.item_type_labeler_live.records import SavedGrouping
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_labeler_markdown import (  # noqa: E501
    PythonDocxLabelerMarkdown,
)
from skriptoteket.infrastructure.llm.openai.decisions_item_labeler import render_items

pytestmark = pytest.mark.unit
FIXTURES = Path("tests/fixtures/exam_conversion")
CORPUS = FIXTURES / "docx_corpus"
DOCUMENTS = sorted([*CORPUS.glob("*.docx"), *(FIXTURES / "synthetic_shapes").glob("*.docx")])
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
W = "{" + NS["w"] + "}"
GRAMMAR = [f"svenska_2_grammatik_omprov_variant_{i}_med_facit" for i in (1, 2)]
MARKUP = ("<i>", "</i>", "**")
# Structure the renderer may put before a paragraph's own text: indentation, a Word
# bullet and a heading level. Everything after it must be the source text itself.
PREFIX = re.compile(r" *(?:- )?(?:#{1,6} )?")


def _source(path: Path) -> tuple[dict[str, ET.Element], ET.Element]:
    with ZipFile(path) as package:
        document = ET.fromstring(package.read("word/document.xml"))
        numbering = ET.fromstring(package.read("word/numbering.xml"))
    body = document.find("w:body", NS)
    assert body is not None
    return {f"body:{i:04d}": block for i, block in enumerate(body, 1)}, numbering


def _paragraph_text(element: ET.Element) -> str:
    # Read visible text directly from XML rather than trusting either extractor.
    return "".join(
        node.text or "" if node.tag == W + "t" else "\t" if node.tag == W + "tab" else "\n"
        for node in element.iter()
        if node.tag in {W + "t", W + "tab", W + "br", W + "cr"}
    )


def _check_paragraph(markdown: str, source: str) -> None:
    """Markdown is a structural prefix plus the source text with emphasis markup only."""
    assert not any(mark in source for mark in MARKUP), "markup would be ambiguous"
    plain = markdown
    for mark in MARKUP:
        plain = plain.replace(mark, "")
    assert plain.endswith(source), (markdown, source)
    assert PREFIX.fullmatch(plain[: len(plain) - len(source)]), (markdown, source)


def _check_block(markdown: str, element: ET.Element) -> None:
    if element.tag == W + "p":
        _check_paragraph(markdown, _paragraph_text(element))
        return
    assert element.tag == W + "tbl"
    rows = element.findall("w:tr", NS)
    lines = markdown.split("\n")
    assert len(lines) == len(rows) + 1
    width = len(rows[0].findall("w:tc", NS))
    assert lines.pop(1) == "| " + " | ".join("---" for _ in range(width)) + " |"
    for line, row in zip(lines, rows, strict=True):
        assert line.startswith("| ") and line.endswith(" |")
        for value, cell in zip(line[2:-2].split(" | "), row.findall("w:tc", NS), strict=True):
            for part, paragraph in zip(value.split("<br>"), cell.findall("w:p", NS), strict=True):
                _check_paragraph(part, _paragraph_text(paragraph))


@pytest.mark.parametrize("path", DOCUMENTS, ids=lambda p: p.stem)
def test_every_block_is_its_xml_text_plus_structure_and_converter_input_is_unchanged(
    path: Path,
) -> None:
    content = path.read_bytes()
    before = PythonDocxExamChunker().chunk(content=content)
    projected = PythonDocxLabelerMarkdown().source(content=content).chunks
    blocks, _ = _source(path)

    assert [(c.anchor, c.kind, c.text) for c in projected] == [
        (c.anchor, c.kind, c.text) for c in before
    ]
    for chunk in projected:
        _check_block(chunk.marked_text, blocks[chunk.anchor])
    assert PythonDocxExamChunker().chunk(content=content) == before


@pytest.mark.parametrize("path", DOCUMENTS, ids=lambda p: p.stem)
def test_italic_runs_reach_the_labeler_as_the_converter_marks_them(path: Path) -> None:
    content = path.read_bytes()
    converter = {c.anchor: c.marked_text for c in PythonDocxExamChunker().chunk(content=content)}
    for chunk in PythonDocxLabelerMarkdown().source(content=content).chunks:
        for italic in re.findall(r"<i>(.*?)</i>", converter[chunk.anchor], flags=re.S):
            assert f"<i>{italic}</i>" in chunk.marked_text.replace("**", ""), chunk.anchor


@pytest.mark.parametrize("stem", GRAMMAR)
def test_word_bullets_keep_marker_and_indentation_from_numbering_xml(stem: str) -> None:
    path = CORPUS / f"{stem}.docx"
    blocks, numbering = _source(path)
    chunks = {
        c.anchor: c for c in PythonDocxLabelerMarkdown().source(content=path.read_bytes()).chunks
    }
    listed = []
    for anchor, block in blocks.items():
        properties = block.find("w:pPr/w:numPr", NS)
        if properties is None:
            continue
        num_id = properties.find("w:numId", NS)
        level = properties.find("w:ilvl", NS)
        assert num_id is not None and level is not None
        reference = numbering.find(f'w:num[@w:numId="{num_id.get(W + "val")}"]/w:abstractNumId', NS)
        assert reference is not None
        definition = numbering.find(
            f'w:abstractNum[@w:abstractNumId="{reference.get(W + "val")}"]'
            f'/w:lvl[@w:ilvl="{level.get(W + "val")}"]',
            NS,
        )
        assert definition is not None
        fmt = definition.find("w:numFmt", NS)
        indent = definition.find("w:pPr/w:ind", NS)
        assert fmt is not None and indent is not None
        assert fmt.get(W + "val") == "bullet"
        # The bullet stands at left - hanging twips; 180 twips render as one space.
        spaces = (int(indent.get(W + "left", "0")) - int(indent.get(W + "hanging", "0"))) // 180
        assert chunks[anchor].marked_text.startswith(" " * spaces + "- ")
        assert not chunks[anchor].marked_text.startswith(" " * (spaces + 1))
        _check_block(chunks[anchor].marked_text, block)
        listed.append(anchor)
    assert listed == [f"body:{i:04d}" for i in range(88, 94)]
    # Typed question numbers have no Word numPr; they stay exactly as typed.
    for anchor in ("body:0008", "body:0045"):
        assert blocks[anchor].find("w:pPr/w:numPr", NS) is None
        assert re.match(r"Fråga [15]\. ", _paragraph_text(blocks[anchor]))
        _check_block(chunks[anchor].marked_text, blocks[anchor])


@pytest.mark.parametrize("stem", GRAMMAR)
def test_grouped_q1_and_q5_send_own_keys_instruction_and_heading_as_source_text(
    stem: str,
) -> None:
    # Exact q1/q4/q5 projection of the saved real Responses grouping in retained
    # labeler/takeover-v3-corpus/inputs/<stem>.grouping_a.json; no gold or invented data.
    variant_2 = stem == GRAMMAR[1]
    grouping: SavedGrouping = {
        "questions": [
            {
                "id": "q1",
                "anchors": ["body:0008"]
                if variant_2
                else ["body:0008", "body:0010", "body:0011", "body:0012"],
                "key_anchors": ["body:0010", "body:0011", "body:0012"] if variant_2 else [],
            },
            {
                "id": "q4",
                "anchors": ["body:0037", "body:0038", "body:0039", "body:0040", "body:0041"],
                "key_anchors": [],
            },
            {
                "id": "q5",
                "anchors": ["body:0045", "body:0046", "body:0047", "body:0048"],
                "key_anchors": [],
            },
        ],
        "contexts": [
            {"anchor": "body:0009", "governs": ["q1"], "scope": "section_instruction"},
            {"anchor": "body:0035", "governs": ["q4", "q5"], "scope": "section_instruction"},
        ],
        "title": ["body:0002"],
    }
    path = CORPUS / f"{stem}.docx"
    blocks, _ = _source(path)
    grouped = corpus_items(CORPUS, stem, grouping)
    items = [grouped[0], grouped[2]]
    # Section heading, own question/key anchors and the governing instruction, in source order.
    expected_anchors = [
        ["body:0006", "body:0008", "body:0009", "body:0010", "body:0011", "body:0012"],
        ["body:0034", "body:0035", "body:0045", "body:0046", "body:0047", "body:0048"],
    ]
    request = render_items(items)
    for number, (item, anchors) in enumerate(zip(items, expected_anchors, strict=True), 1):
        lines = item.source_text.split("\n")
        assert f"### Question q{number}\n{item.source_text}" in request
        cursor = 0
        for anchor in anchors:
            source = _paragraph_text(blocks[anchor])
            width = source.count("\n") + 1
            _check_block("\n".join(lines[cursor : cursor + width]), blocks[anchor])
            cursor += width
        assert cursor == len(lines), "rendered input carries lines absent from the source"
    for invented in ("[___]", "Answer key", "[Governing instruction", "Section heading:"):
        assert invented not in request
