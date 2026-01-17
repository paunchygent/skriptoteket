from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from skriptoteket.protocols.editor_patches import UnifiedDiffHunk

from .errors import MALFORMED_PATCH_ERROR

HUNK_HEADER_RE: Final[re.Pattern[str]] = re.compile(
    r"^@@\s+-(?P<old_start>\d+)(?:,(?P<old_count>\d+))?\s+"
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))?\s+@@"
)
FILE_HEADER_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<kind>---|\+\+\+)\s+(?P<path>\S+)(?:\s+.*)?$"
)
DIFF_GIT_RE: Final[re.Pattern[str]] = re.compile(r"^diff --git\s+(?P<old>\S+)\s+(?P<new>\S+)\s*$")
MAX_BLANK_SKIPS_DEFAULT: Final[int] = 5


@dataclass(frozen=True, slots=True)
class HunkHeader:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    suffix: str


@dataclass(frozen=True, slots=True)
class ParsedLine:
    tag: str
    text: str


@dataclass(frozen=True, slots=True)
class ParsedHunk:
    index: int
    header: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[ParsedLine]


@dataclass(frozen=True, slots=True)
class HunkMatch:
    mapping: list[int]
    offset: int
    fuzz: int
    blank_skips: int
    whitespace_ignored: bool
    lead_skip: int
    tail_skip: int


def parse_hunk_header(line: str) -> HunkHeader | None:
    match = HUNK_HEADER_RE.match(line)
    if not match:
        return None
    old_start = int(match.group("old_start"))
    old_count = int(match.group("old_count") or "1")
    new_start = int(match.group("new_start"))
    new_count = int(match.group("new_count") or "1")
    return HunkHeader(
        old_start=old_start,
        old_count=old_count,
        new_start=new_start,
        new_count=new_count,
        suffix=line[match.end() :],
    )


def parse_hunks(lines: list[str]) -> list[UnifiedDiffHunk]:
    hunks: list[UnifiedDiffHunk] = []
    for line in lines:
        header = parse_hunk_header(line)
        if not header:
            continue
        hunks.append(
            UnifiedDiffHunk(
                index=len(hunks) + 1,
                header=line.strip(),
                old_start=header.old_start,
                old_count=header.old_count,
                new_start=header.new_start,
                new_count=header.new_count,
            )
        )
    return hunks


def extract_file_headers(lines: list[str]) -> tuple[str | None, str | None]:
    old_path: str | None = None
    new_path: str | None = None
    for line in lines:
        match = FILE_HEADER_RE.match(line)
        if not match:
            continue
        kind = match.group("kind")
        path = match.group("path")
        if kind == "---":
            old_path = path
        else:
            new_path = path
        if old_path and new_path:
            break
    return old_path, new_path


def extract_diff_git_header(lines: list[str]) -> tuple[str | None, str | None]:
    for line in lines:
        match = DIFF_GIT_RE.match(line)
        if match:
            return match.group("old"), match.group("new")
    return None, None


def is_diff_body_line(line: str) -> bool:
    if not line:
        return False
    return line[0] in {" ", "+", "-", "\\"}


def is_file_header_line(line: str) -> bool:
    return bool(FILE_HEADER_RE.match(line) or DIFF_GIT_RE.match(line))


def split_hunk_sections(
    lines: list[str],
) -> tuple[list[str], list[tuple[str | None, list[str]]], bool]:
    prefix: list[str] = []
    hunks: list[tuple[str | None, list[str]]] = []
    current_header: str | None = None
    current_body: list[str] = []
    saw_header = False

    for line in lines:
        if line.startswith("@@"):
            if saw_header:
                hunks.append((current_header, current_body))
            current_header = line
            current_body = []
            saw_header = True
            continue

        if not saw_header:
            if is_file_header_line(line):
                prefix.append(line)
            elif is_diff_body_line(line):
                current_body.append(line)
            else:
                prefix.append(line)
            continue

        if is_diff_body_line(line):
            current_body.append(line)

    if saw_header:
        hunks.append((current_header, current_body))
    elif current_body:
        hunks.append((None, current_body))

    return prefix, hunks, saw_header


def parse_hunk_blocks(normalized_diff: str) -> list[ParsedHunk]:
    lines = normalized_diff.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]

    hunks: list[ParsedHunk] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        header = parse_hunk_header(line)
        if not header:
            idx += 1
            continue

        idx += 1
        body: list[ParsedLine] = []
        while idx < len(lines) and not parse_hunk_header(lines[idx]):
            body_line = lines[idx]
            if not body_line:
                raise ValueError(MALFORMED_PATCH_ERROR)
            marker = body_line[0]
            if marker not in {" ", "+", "-", "\\"}:
                raise ValueError(MALFORMED_PATCH_ERROR)
            if marker != "\\":
                body.append(ParsedLine(tag=marker, text=body_line[1:]))
            idx += 1

        if not body:
            raise ValueError(MALFORMED_PATCH_ERROR)

        hunks.append(
            ParsedHunk(
                index=len(hunks) + 1,
                header=line.strip(),
                old_start=header.old_start,
                old_count=header.old_count,
                new_start=header.new_start,
                new_count=header.new_count,
                lines=body,
            )
        )
    return hunks


def _normalize_ws(line: str) -> str:
    return " ".join(line.strip().split())


def _line_matches(base_line: str, expected: str, *, ignore_ws: bool) -> bool:
    if ignore_ws:
        return _normalize_ws(base_line) == _normalize_ws(expected)
    return base_line == expected


def _is_blank(line: str) -> bool:
    return line.strip() == ""


def _leading_context_count(old_lines: list[ParsedLine]) -> int:
    count = 0
    for line in old_lines:
        if line.tag != " ":
            break
        count += 1
    return count


def _trailing_context_count(old_lines: list[ParsedLine]) -> int:
    count = 0
    for line in reversed(old_lines):
        if line.tag != " ":
            break
        count += 1
    return count


def build_apply_plan(hunk_lines: list[ParsedLine]) -> tuple[list[ParsedLine], dict[int, list[str]]]:
    old_lines: list[ParsedLine] = []
    inserts: dict[int, list[str]] = {}
    current_old_index = -1

    for line in hunk_lines:
        if line.tag == "+":
            inserts.setdefault(current_old_index, []).append(line.text)
        elif line.tag in {" ", "-"}:
            old_lines.append(line)
            current_old_index += 1

    return old_lines, inserts


def _match_from(
    *,
    base_lines: list[str],
    old_lines: list[ParsedLine],
    start_index: int,
    ignore_ws: bool,
    max_blank_skips: int,
) -> tuple[list[int], int] | None:
    mapping: list[int] = []
    blank_skips = 0
    base_index = start_index

    for old_line in old_lines:
        expected = old_line.text
        while base_index < len(base_lines):
            if _line_matches(base_lines[base_index], expected, ignore_ws=ignore_ws):
                mapping.append(base_index)
                base_index += 1
                break

            if _is_blank(base_lines[base_index]) and expected.strip() != "":
                blank_skips += 1
                if blank_skips > max_blank_skips:
                    return None
                base_index += 1
                continue

            return None
        else:
            return None

    return mapping, blank_skips


def find_hunk_match(
    *,
    base_lines: list[str],
    old_lines: list[ParsedLine],
    expected_index: int,
    max_offset_lines: int,
    max_fuzz: int,
    ignore_ws: bool,
    max_blank_skips: int,
) -> HunkMatch | None:
    if not old_lines:
        return None

    leading_context = _leading_context_count(old_lines)
    trailing_context = _trailing_context_count(old_lines)

    best: HunkMatch | None = None
    best_score: tuple[int, int, int, int] | None = None

    for fuzz in range(0, max_fuzz + 1):
        lead_max = min(fuzz, leading_context)
        tail_max = min(fuzz, trailing_context)
        for lead_skip in range(0, lead_max + 1):
            for tail_skip in range(0, tail_max + 1):
                trimmed_old = old_lines[lead_skip : len(old_lines) - tail_skip]
                if not trimmed_old:
                    continue

                expected_trim = max(0, expected_index + lead_skip)
                start_min = max(0, expected_trim - max_offset_lines)
                start_max = min(len(base_lines), expected_trim + max_offset_lines)

                for candidate_start in range(start_min, start_max + 1):
                    match = _match_from(
                        base_lines=base_lines,
                        old_lines=trimmed_old,
                        start_index=candidate_start,
                        ignore_ws=ignore_ws,
                        max_blank_skips=max_blank_skips,
                    )
                    if match is None:
                        continue

                    mapping, blank_skips = match
                    offset = mapping[0] - expected_index
                    if abs(offset) > max_offset_lines:
                        continue

                    score = (abs(offset), blank_skips, fuzz, lead_skip + tail_skip)
                    if best_score is None or score < best_score:
                        best_score = score
                        best = HunkMatch(
                            mapping=mapping,
                            offset=offset,
                            fuzz=fuzz,
                            blank_skips=blank_skips,
                            whitespace_ignored=ignore_ws,
                            lead_skip=lead_skip,
                            tail_skip=tail_skip,
                        )
                        if score == (0, 0, 0, 0):
                            return best

    return best
