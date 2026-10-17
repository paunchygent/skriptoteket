"""Parse DigiExam's HTML grammar into positioned native body segments."""

from __future__ import annotations

from html.parser import HTMLParser
from typing import Literal

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
    NativeSegment,
    NativeTextMark,
    NativeTextSegment,
)

_MARKS: dict[str, NativeTextMark] = {
    "b": "bold",
    "strong": "bold",
    "i": "italic",
    "em": "italic",
    "u": "underline",
    "sup": "superscript",
    "sub": "subscript",
}
_BLOCKS = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6"}
_HEADINGS: dict[str, Literal[1, 2, 3]] = {"h1": 1, "h2": 2, "h3": 3}
_VOID = {"br", "img", "hr", "input", "wbr", "meta", "link"}


def digiexam_body(
    *,
    html: str | None,
    lines: tuple[str, ...],
    image_ids: dict[int, str],
    gap_ids: dict[str, str],
) -> tuple[NativeParagraph, ...]:
    """Preserve source positions; references are resolved by source identity."""
    if html is None:
        return tuple(
            NativeParagraph(segments=(NativeTextSegment(text=line, marks=()),), heading_level=None)
            for line in lines
            if line
        )
    parser = _BodyParser(image_ids=image_ids, gap_ids=gap_ids)
    parser.feed(html)
    parser.close()
    parser.flush()
    return tuple(parser.paragraphs)


def digiexam_plain_text(*, html: str | None, lines: tuple[str, ...]) -> str:
    """Read original source words even when an IR producer supplies HTML only."""
    if lines:
        return "\n".join(lines)
    parser = _OriginalTextParser()
    parser.feed(html or "")
    parser.close()
    return "".join(parser.parts).strip()


class _OriginalTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _BLOCKS or tag == "br":
            self.parts.append("\n")
        if tag == "span" and dict(attrs).get("dx-wg-id"):
            self.parts.append("[___]")

    def handle_endtag(self, tag: str) -> None:
        if tag in _BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


class _BodyParser(HTMLParser):
    def __init__(self, *, image_ids: dict[int, str], gap_ids: dict[str, str]) -> None:
        super().__init__(convert_charrefs=True)
        self.paragraphs: list[NativeParagraph] = []
        self._segments: list[NativeSegment] = []
        self._stack: list[tuple[str, tuple[NativeTextMark, ...]]] = []
        self._marks: tuple[NativeTextMark, ...] = ()
        self._heading: Literal[1, 2, 3] | None = None
        self._suppressed: list[str] = []
        self._image_ids = image_ids
        self._gap_ids = gap_ids

    def flush(self) -> None:
        if self._segments:
            self.paragraphs.append(
                NativeParagraph(
                    segments=tuple(self._segments),
                    heading_level=self._heading,
                )
            )
            self._segments = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._suppressed:
            if tag not in _VOID:
                self._suppressed.append(tag)
            return
        values = dict(attrs)
        if tag in {"script", "style"}:
            self._suppressed.append(tag)
            return
        if tag in _BLOCKS or tag in {"br", "hr"}:
            self.flush()
            if tag in _BLOCKS:
                self._heading = _HEADINGS.get(tag)
        if tag == "img":
            source_id = values.get("data-image-id")
            asset_id = (
                self._image_ids.get(int(source_id)) if source_id and source_id.isdecimal() else None
            )
            if asset_id is None:
                self._segments.append(
                    NativeTextSegment(text="[Bild saknas i DigiExam-exporten]", marks=())
                )
            else:
                self._segments.append(NativeAssetSegment(asset_id=asset_id))
            return
        guid = values.get("dx-wg-id") if tag == "span" else None
        if guid:
            if guid not in self._gap_ids:
                raise ValueError("DigiExam prompt references an undeclared gap")
            self._segments.append(NativeGapSegment(gap_id=self._gap_ids[guid]))
            self._suppressed.append(tag)
            return
        if tag not in _VOID:
            self._stack.append((tag, self._marks))
            mark = _MARKS.get(tag)
            if mark is not None and mark not in self._marks:
                # The innermost baseline mark supersedes its opposite.
                if mark in {"superscript", "subscript"}:
                    self._marks = tuple(
                        m for m in self._marks if m not in {"superscript", "subscript"}
                    )
                self._marks = (*self._marks, mark)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if self._suppressed:
            if tag in self._suppressed:
                index = len(self._suppressed) - 1 - self._suppressed[::-1].index(tag)
                del self._suppressed[index:]
            return
        if tag in _BLOCKS:
            self.flush()
            self._heading = None
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index][0] == tag:
                self._marks = self._stack[index][1]
                del self._stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if self._suppressed or not data:
            return
        # HTML whitespace outside paragraphs is layout, not a question paragraph.
        if not self._segments and not data.strip():
            return
        self._segments.append(NativeTextSegment(text=data, marks=self._marks))
