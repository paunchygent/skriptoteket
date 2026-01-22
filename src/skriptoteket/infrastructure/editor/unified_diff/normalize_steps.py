"""Line-level normalization steps for unified diffs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

_INVISIBLE_CHARS: Final[tuple[str, ...]] = ("\ufeff", "\u200b", "\u200c", "\u200d")

_CODE_FENCE_RE = re.compile(r"^\s*```")
_PATCH_WRAPPER_PREFIXES: Final[tuple[str, ...]] = (
    "*** Begin Patch",
    "*** End Patch",
    "*** Update File:",
    "*** Delete File:",
    "*** Add File:",
    "*** End of File",
)


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    text: str
    applied: list[str]


def normalize_newlines(text: str) -> NormalizationResult:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    applied: list[str] = []
    if normalized != text:
        applied.append("normalized_line_endings")
    return NormalizationResult(text=normalized, applied=applied)


def strip_invisible_chars(text: str) -> NormalizationResult:
    applied: list[str] = []
    next_text = text
    for ch in _INVISIBLE_CHARS:
        if ch in next_text:
            next_text = next_text.replace(ch, "")
            applied.append("stripped_invisible_chars")
    return NormalizationResult(text=next_text, applied=applied)


def strip_code_fences(text: str) -> NormalizationResult:
    lines = text.split("\n")
    stripped: list[str] = []
    applied: list[str] = []
    for line in lines:
        if _CODE_FENCE_RE.match(line):
            applied.append("stripped_code_fences")
            continue
        stripped.append(line)
    applied = list(dict.fromkeys(applied))
    return NormalizationResult(text="\n".join(stripped), applied=applied)


def strip_patch_wrappers(text: str) -> NormalizationResult:
    lines = text.split("\n")
    stripped: list[str] = []
    applied = False
    for line in lines:
        if line.startswith(_PATCH_WRAPPER_PREFIXES):
            applied = True
            continue
        stripped.append(line)
    if not applied:
        return NormalizationResult(text=text, applied=[])
    return NormalizationResult(text="\n".join(stripped), applied=["stripped_patch_wrappers"])


def strip_common_indentation(text: str) -> NormalizationResult:
    lines = text.split("\n")
    indents: list[int] = []
    for line in lines:
        if not line.strip():
            continue
        stripped = line.lstrip(" \t")
        if stripped.startswith(("diff --git", "--- ", "+++ ", "@@ ", "@@")):
            indents.append(len(line) - len(stripped))
            continue
        if stripped and stripped[0] in {"+", "-", " ", "\\"}:
            indents.append(len(line) - len(stripped))
            continue

    if not indents:
        return NormalizationResult(text=text, applied=[])

    min_indent = min(indents)
    if min_indent <= 0:
        return NormalizationResult(text=text, applied=[])

    out: list[str] = []
    for line in lines:
        if len(line) >= min_indent:
            out.append(line[min_indent:])
        else:
            out.append(line.lstrip(" \t"))
    return NormalizationResult(text="\n".join(out), applied=["stripped_leading_indentation"])


def ensure_trailing_newline(text: str) -> NormalizationResult:
    if text.endswith("\n"):
        return NormalizationResult(text=text, applied=[])
    return NormalizationResult(text=f"{text}\n", applied=["added_trailing_newline"])


def strip_bom_from_lines(text: str) -> NormalizationResult:
    if not text.startswith("\ufeff"):
        return NormalizationResult(text=text, applied=[])
    return NormalizationResult(text=text.lstrip("\ufeff"), applied=["stripped_bom"])


def strip_empty_leading_trailing_lines(text: str) -> NormalizationResult:
    lines = text.split("\n")
    start = 0
    while start < len(lines) and lines[start] == "":
        start += 1
    end = len(lines)
    while end > start and lines[end - 1] == "":
        end -= 1
    if start == 0 and end == len(lines):
        return NormalizationResult(text=text, applied=[])
    return NormalizationResult(text="\n".join(lines[start:end]), applied=["trimmed_blank_lines"])


__all__ = [
    "NormalizationResult",
    "ensure_trailing_newline",
    "normalize_newlines",
    "strip_bom_from_lines",
    "strip_code_fences",
    "strip_common_indentation",
    "strip_empty_leading_trailing_lines",
    "strip_invisible_chars",
    "strip_patch_wrappers",
]
