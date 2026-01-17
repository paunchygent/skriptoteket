from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Final

from skriptoteket.protocols.editor_patches import (
    PatchApplyErrorDetails,
    PatchApplyMeta,
    PatchApplyResult,
    PreparedUnifiedDiff,
    UnifiedDiffApplierProtocol,
    UnifiedDiffHunk,
)
from skriptoteket.protocols.llm import VirtualFileId

_INVISIBLE_CHARS: Final[tuple[str, ...]] = ("\ufeff", "\u200b", "\u200c", "\u200d")

_CODE_FENCE_RE = re.compile(r"^\s*```")
_HUNK_HEADER_RE = re.compile(
    r"^@@\s+-(?P<old_start>\d+)(?:,(?P<old_count>\d+))?\s+\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))?\s+@@"
)
_FILE_HEADER_RE = re.compile(r"^(?P<kind>---|\+\+\+)\s+(?P<path>\S+)(?:\s+.*)?$")
_DIFF_GIT_RE = re.compile(r"^diff --git\s+(?P<old>\S+)\s+(?P<new>\S+)\s*$")

_MALFORMED_PATCH_ERROR: Final[str] = "Diffen är felaktigt formaterad (ogiltig @@-hunk). Regenerera."
_MAX_BLANK_SKIPS_DEFAULT: Final[int] = 5
_PATCH_WRAPPER_PREFIXES: Final[tuple[str, ...]] = (
    "*** Begin Patch",
    "*** End Patch",
    "*** Update File:",
    "*** Delete File:",
    "*** Add File:",
    "*** End of File",
)


@dataclass(frozen=True, slots=True)
class _NormalizationResult:
    text: str
    applied: list[str]


@dataclass(frozen=True, slots=True)
class _ParsedLine:
    tag: str
    text: str


@dataclass(frozen=True, slots=True)
class _ParsedHunk:
    index: int
    header: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[_ParsedLine]


@dataclass(frozen=True, slots=True)
class _HunkMatch:
    mapping: list[int]
    offset: int
    fuzz: int
    blank_skips: int
    whitespace_ignored: bool
    lead_skip: int
    tail_skip: int


def _normalize_newlines(text: str) -> _NormalizationResult:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    applied: list[str] = []
    if normalized != text:
        applied.append("normalized_line_endings")
    return _NormalizationResult(text=normalized, applied=applied)


def _strip_invisible_chars(text: str) -> _NormalizationResult:
    applied: list[str] = []
    next_text = text
    for ch in _INVISIBLE_CHARS:
        if ch in next_text:
            next_text = next_text.replace(ch, "")
            applied.append("stripped_invisible_chars")
    return _NormalizationResult(text=next_text, applied=applied)


def _strip_code_fences(text: str) -> _NormalizationResult:
    lines = text.split("\n")
    stripped: list[str] = []
    applied: list[str] = []
    for line in lines:
        if _CODE_FENCE_RE.match(line):
            applied.append("stripped_code_fences")
            continue
        stripped.append(line)
    # Avoid double-reporting when multiple fences exist.
    applied = list(dict.fromkeys(applied))
    return _NormalizationResult(text="\n".join(stripped), applied=applied)


def _strip_patch_wrappers(text: str) -> _NormalizationResult:
    lines = text.split("\n")
    stripped: list[str] = []
    applied = False
    for line in lines:
        if line.startswith(_PATCH_WRAPPER_PREFIXES):
            applied = True
            continue
        stripped.append(line)
    if not applied:
        return _NormalizationResult(text=text, applied=[])
    return _NormalizationResult(text="\n".join(stripped), applied=["stripped_patch_wrappers"])


def _strip_common_indentation(text: str) -> _NormalizationResult:
    lines = text.split("\n")
    indents: list[int] = []
    for line in lines:
        if not line.strip():
            continue
        # Consider unified diff marker lines and common headers.
        stripped = line.lstrip(" \t")
        if stripped.startswith(("diff --git", "--- ", "+++ ", "@@ ", "@@")):
            indents.append(len(line) - len(stripped))
            continue
        if stripped and stripped[0] in {"+", "-", " ", "\\"}:
            indents.append(len(line) - len(stripped))
            continue

    if not indents:
        return _NormalizationResult(text=text, applied=[])

    min_indent = min(indents)
    if min_indent <= 0:
        return _NormalizationResult(text=text, applied=[])

    out: list[str] = []
    for line in lines:
        if len(line) >= min_indent:
            out.append(line[min_indent:])
        else:
            out.append(line.lstrip(" \t"))
    return _NormalizationResult(text="\n".join(out), applied=["stripped_leading_indentation"])


def _ensure_trailing_newline(text: str) -> _NormalizationResult:
    if text.endswith("\n"):
        return _NormalizationResult(text=text, applied=[])
    return _NormalizationResult(text=f"{text}\n", applied=["added_trailing_newline"])


def _strip_bom_from_lines(text: str) -> _NormalizationResult:
    if not text.startswith("\ufeff"):
        return _NormalizationResult(text=text, applied=[])
    return _NormalizationResult(text=text.lstrip("\ufeff"), applied=["stripped_bom"])


def _strip_empty_leading_trailing_lines(text: str) -> _NormalizationResult:
    lines = text.split("\n")
    start = 0
    while start < len(lines) and lines[start] == "":
        start += 1
    end = len(lines)
    while end > start and lines[end - 1] == "":
        end -= 1
    if start == 0 and end == len(lines):
        return _NormalizationResult(text=text, applied=[])
    return _NormalizationResult(text="\n".join(lines[start:end]), applied=["trimmed_blank_lines"])


def _path_basename(path: str) -> str:
    # Drop timestamps and prefixes such as a/ or b/.
    cleaned = path
    if cleaned.startswith("a/") or cleaned.startswith("b/"):
        cleaned = cleaned[2:]
    if cleaned.startswith("./"):
        cleaned = cleaned[2:]
    return cleaned


def _sha256_id(payload: str) -> str:
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _extract_file_headers(lines: list[str]) -> tuple[str | None, str | None]:
    old_path: str | None = None
    new_path: str | None = None
    for line in lines:
        match = _FILE_HEADER_RE.match(line)
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


def _extract_diff_git_header(lines: list[str]) -> tuple[str | None, str | None]:
    for line in lines:
        match = _DIFF_GIT_RE.match(line)
        if match:
            return match.group("old"), match.group("new")
    return None, None


def _parse_hunks(lines: list[str]) -> list[UnifiedDiffHunk]:
    hunks: list[UnifiedDiffHunk] = []
    for line in lines:
        match = _HUNK_HEADER_RE.match(line)
        if not match:
            continue
        old_start = int(match.group("old_start"))
        old_count = int(match.group("old_count") or "1")
        new_start = int(match.group("new_start"))
        new_count = int(match.group("new_count") or "1")
        hunks.append(
            UnifiedDiffHunk(
                index=len(hunks) + 1,
                header=line.strip(),
                old_start=old_start,
                old_count=old_count,
                new_start=new_start,
                new_count=new_count,
            )
        )
    return hunks


def _parse_hunk_blocks(normalized_diff: str) -> list[_ParsedHunk]:
    lines = normalized_diff.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]

    hunks: list[_ParsedHunk] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        match = _HUNK_HEADER_RE.match(line)
        if not match:
            idx += 1
            continue

        old_start = int(match.group("old_start"))
        old_count = int(match.group("old_count") or "1")
        new_start = int(match.group("new_start"))
        new_count = int(match.group("new_count") or "1")
        header = line.strip()

        idx += 1
        body: list[_ParsedLine] = []
        while idx < len(lines) and not _HUNK_HEADER_RE.match(lines[idx]):
            body_line = lines[idx]
            if not body_line:
                raise ValueError(_MALFORMED_PATCH_ERROR)
            marker = body_line[0]
            if marker not in {" ", "+", "-", "\\"}:
                raise ValueError(_MALFORMED_PATCH_ERROR)
            if marker != "\\":
                body.append(_ParsedLine(tag=marker, text=body_line[1:]))
            idx += 1

        if not body:
            raise ValueError(_MALFORMED_PATCH_ERROR)

        hunks.append(
            _ParsedHunk(
                index=len(hunks) + 1,
                header=header,
                old_start=old_start,
                old_count=old_count,
                new_start=new_start,
                new_count=new_count,
                lines=body,
            )
        )
    return hunks


def _is_diff_body_line(line: str) -> bool:
    if not line:
        return False
    return line[0] in {" ", "+", "-", "\\"}


def _is_file_header_line(line: str) -> bool:
    return bool(_FILE_HEADER_RE.match(line) or _DIFF_GIT_RE.match(line))


def _split_hunk_sections(
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
            if _is_file_header_line(line):
                prefix.append(line)
            elif _is_diff_body_line(line):
                current_body.append(line)
            else:
                prefix.append(line)
            continue

        if _is_diff_body_line(line):
            current_body.append(line)

    if saw_header:
        hunks.append((current_header, current_body))
    elif current_body:
        hunks.append((None, current_body))

    return prefix, hunks, saw_header


def _compute_hunk_counts(body_lines: list[str]) -> tuple[int, int]:
    old_count = 0
    new_count = 0
    for body_line in body_lines:
        if body_line.startswith("\\"):
            continue
        if not body_line:
            raise ValueError(_MALFORMED_PATCH_ERROR)
        marker = body_line[0]
        if marker == " ":
            old_count += 1
            new_count += 1
        elif marker == "-":
            old_count += 1
        elif marker == "+":
            new_count += 1
        else:
            raise ValueError(_MALFORMED_PATCH_ERROR)
    return old_count, new_count


def _repair_missing_hunk_ranges(
    *,
    lines: list[str],
    target_file: VirtualFileId,
    base_text: str | None,
) -> tuple[list[str], list[str]]:
    if base_text is None:
        return lines, []

    prefix, hunks, saw_header = _split_hunk_sections(lines)
    if not hunks:
        return lines, []

    normalizations: list[str] = []
    base_text_norm = base_text.replace("\r\n", "\n").replace("\r", "\n")
    base_lines = base_text_norm.split("\n")
    if base_text_norm.endswith("\n") and base_lines:
        base_lines = base_lines[:-1]

    repaired_lines: list[str] = []
    if prefix:
        repaired_lines.extend(prefix)

    for header_line, body_lines in hunks:
        if not body_lines:
            raise ValueError(_MALFORMED_PATCH_ERROR)

        if header_line is not None and _HUNK_HEADER_RE.match(header_line):
            repaired_lines.append(header_line)
            repaired_lines.extend(body_lines)
            continue

        parsed_lines: list[_ParsedLine] = []
        for body_line in body_lines:
            if body_line.startswith("\\"):
                continue
            if not body_line:
                raise ValueError(_MALFORMED_PATCH_ERROR)
            marker = body_line[0]
            if marker not in {" ", "+", "-"}:
                raise ValueError(_MALFORMED_PATCH_ERROR)
            parsed_lines.append(_ParsedLine(tag=marker, text=body_line[1:]))

        old_lines, _ = _build_apply_plan(parsed_lines)
        if not old_lines:
            raise ValueError("Diffen saknar kontext för att reparera @@-hunks. Regenerera.")

        match = _find_hunk_match(
            base_lines=base_lines,
            old_lines=old_lines,
            expected_index=0,
            max_offset_lines=len(base_lines),
            max_fuzz=0,
            ignore_ws=False,
            max_blank_skips=_MAX_BLANK_SKIPS_DEFAULT,
        )
        if match is None:
            match = _find_hunk_match(
                base_lines=base_lines,
                old_lines=old_lines,
                expected_index=0,
                max_offset_lines=len(base_lines),
                max_fuzz=0,
                ignore_ws=True,
                max_blank_skips=_MAX_BLANK_SKIPS_DEFAULT,
            )

        if match is None:
            raise ValueError("Diffen saknar giltiga @@-hunks. Regenerera.")

        old_start = match.mapping[0] + 1
        old_count, new_count = _compute_hunk_counts(body_lines)
        repaired_lines.append(f"@@ -{old_start},{old_count} +{old_start},{new_count} @@")
        repaired_lines.extend(body_lines)
        normalizations.append(
            "repaired_missing_hunk_ranges" if saw_header else "synthesized_hunk_header"
        )

    normalizations = list(dict.fromkeys(normalizations))
    return repaired_lines, normalizations


def _normalize_ws(line: str) -> str:
    return " ".join(line.strip().split())


def _line_matches(base_line: str, expected: str, *, ignore_ws: bool) -> bool:
    if ignore_ws:
        return _normalize_ws(base_line) == _normalize_ws(expected)
    return base_line == expected


def _is_blank(line: str) -> bool:
    return line.strip() == ""


def _leading_context_count(old_lines: list[_ParsedLine]) -> int:
    count = 0
    for line in old_lines:
        if line.tag != " ":
            break
        count += 1
    return count


def _trailing_context_count(old_lines: list[_ParsedLine]) -> int:
    count = 0
    for line in reversed(old_lines):
        if line.tag != " ":
            break
        count += 1
    return count


def _build_apply_plan(
    hunk_lines: list[_ParsedLine],
) -> tuple[list[_ParsedLine], dict[int, list[str]]]:
    old_lines: list[_ParsedLine] = []
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
    old_lines: list[_ParsedLine],
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


def _find_hunk_match(
    *,
    base_lines: list[str],
    old_lines: list[_ParsedLine],
    expected_index: int,
    max_offset_lines: int,
    max_fuzz: int,
    ignore_ws: bool,
    max_blank_skips: int,
) -> _HunkMatch | None:
    if not old_lines:
        return None

    leading_context = _leading_context_count(old_lines)
    trailing_context = _trailing_context_count(old_lines)

    best: _HunkMatch | None = None
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
                        best = _HunkMatch(
                            mapping=mapping,
                            offset=offset,
                            fuzz=fuzz,
                            blank_skips=blank_skips,
                            whitespace_ignored=ignore_ws,
                            lead_skip=lead_skip,
                            tail_skip=tail_skip,
                        )

    return best


def _repair_hunk_header_counts(lines: list[str]) -> tuple[list[str], list[str]]:
    normalizations: list[str] = []
    out: list[str] = []
    idx = 0

    while idx < len(lines):
        line = lines[idx]
        match = _HUNK_HEADER_RE.match(line)
        if not match:
            out.append(line)
            idx += 1
            continue

        old_start = int(match.group("old_start"))
        old_count_declared = int(match.group("old_count") or "1")
        new_start = int(match.group("new_start"))
        new_count_declared = int(match.group("new_count") or "1")
        header_suffix = line[match.end() :]

        body_start = idx + 1
        body_end = body_start
        while body_end < len(lines) and not _HUNK_HEADER_RE.match(lines[body_end]):
            body_end += 1

        body = lines[body_start:body_end]
        if not body:
            raise ValueError(_MALFORMED_PATCH_ERROR)

        old_count = 0
        new_count = 0
        for body_line in body:
            if body_line.startswith("\\"):
                continue
            if not body_line:
                raise ValueError(_MALFORMED_PATCH_ERROR)
            marker = body_line[0]
            if marker == " ":
                old_count += 1
                new_count += 1
            elif marker == "-":
                old_count += 1
            elif marker == "+":
                new_count += 1
            else:
                raise ValueError(_MALFORMED_PATCH_ERROR)

        if old_count != old_count_declared or new_count != new_count_declared:
            out.append(f"@@ -{old_start},{old_count} +{new_start},{new_count} @@{header_suffix}")
            normalizations.append("rewrote_hunk_header_counts")
        else:
            out.append(line)

        out.extend(body)
        idx = body_end

    # Deduplicate normalization flags.
    normalizations = list(dict.fromkeys(normalizations))
    return out, normalizations


def _standardize_headers(
    *, lines: list[str], target_file: VirtualFileId
) -> tuple[list[str], list[str]]:
    normalizations: list[str] = []

    old_path, new_path = _extract_file_headers(lines)
    if old_path is None or new_path is None:
        git_old, git_new = _extract_diff_git_header(lines)
        if git_old and git_new:
            old_path, new_path = git_old, git_new
            normalizations.append("inferred_headers_from_diff_git")
        else:
            # Synthesize missing headers.
            old_path = f"a/{target_file}"
            new_path = f"b/{target_file}"
            normalizations.append("synthesized_file_headers")

    # Reject /dev/null scenarios for virtual files.
    if old_path == "/dev/null" or new_path == "/dev/null":
        raise ValueError("Diffen försöker skapa eller radera filer, vilket inte stöds.")

    # Ensure the diff targets the expected file.
    old_base = _path_basename(old_path)
    new_base = _path_basename(new_path)
    if old_base != target_file or new_base != target_file:
        raise ValueError("Diffen berör en annan fil än den förväntade. Regenerera.")

    # Replace headers in-place to normalized a/<id> / b/<id>.
    out: list[str] = []
    saw_old = False
    saw_new = False
    for line in lines:
        match = _FILE_HEADER_RE.match(line)
        if match:
            kind = match.group("kind")
            if kind == "---" and not saw_old:
                out.append(f"--- a/{target_file}")
                saw_old = True
                if line != out[-1]:
                    normalizations.append("standardized_file_headers")
                continue
            if kind == "+++" and not saw_new:
                out.append(f"+++ b/{target_file}")
                saw_new = True
                if line != out[-1]:
                    normalizations.append("standardized_file_headers")
                continue
        out.append(line)

    # Ensure headers exist near the top (patch is lenient but we want predictable parsing).
    # If we never saw them (because they were missing or embedded), inject.
    if not saw_old or not saw_new:
        injected: list[str] = [f"--- a/{target_file}", f"+++ b/{target_file}"]
        # Drop any existing partial headers and re-add them at the front.
        filtered = [line for line in out if not _FILE_HEADER_RE.match(line)]
        out = injected + filtered
        normalizations.append("injected_standard_headers")

    # Deduplicate normalization flags.
    normalizations = list(dict.fromkeys(normalizations))
    return out, normalizations


def _reject_multi_file_diff(lines: list[str]) -> None:
    # If the diff contains multiple file sections, reject early.
    header_count = sum(1 for line in lines if line.startswith("--- "))
    if header_count > 1:
        raise ValueError("Diffen innehåller flera filer. Regenerera med en fil i taget.")
    diff_git_count = sum(1 for line in lines if line.startswith("diff --git "))
    if diff_git_count > 1:
        raise ValueError("Diffen innehåller flera filer. Regenerera med en fil i taget.")


def _extract_expected_snippet(prepared: PreparedUnifiedDiff, *, hunk_index: int) -> str | None:
    lines = prepared.normalized_diff.split("\n")
    current_hunk = 0
    snippet_lines: list[str] = []
    in_hunk = False
    for line in lines:
        if line.startswith("@@"):
            current_hunk += 1
            in_hunk = current_hunk == hunk_index
            continue
        if not in_hunk:
            continue
        if line.startswith(("+", "-", " ")):
            snippet_lines.append(line)
        if len(snippet_lines) >= 12:
            break
    if not snippet_lines:
        return None
    return "\n".join(snippet_lines).strip()


def _extract_base_snippet(base_text: str, *, expected_line: int) -> str:
    lines = base_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    # expected_line is 1-based
    center = max(expected_line - 1, 0)
    start = max(center - 4, 0)
    end = min(center + 8, len(lines))
    snippet = "\n".join(lines[start:end]).strip("\n")
    return snippet


class NativeUnifiedDiffApplier(UnifiedDiffApplierProtocol):
    def prepare(
        self,
        *,
        target_file: VirtualFileId,
        unified_diff: str,
        base_text: str | None = None,
    ) -> PreparedUnifiedDiff:
        normalizations: list[str] = []
        text = unified_diff

        for step in (
            _strip_bom_from_lines,
            _normalize_newlines,
            _strip_invisible_chars,
            _strip_code_fences,
            _strip_patch_wrappers,
            _strip_common_indentation,
            _strip_empty_leading_trailing_lines,
            _ensure_trailing_newline,
        ):
            result = step(text)
            text = result.text
            normalizations.extend(result.applied)

        lines = text.split("\n")
        if lines and lines[-1] == "":
            lines = lines[:-1]
        _reject_multi_file_diff(lines)
        try:
            normalized_lines, header_norm = _standardize_headers(
                lines=lines, target_file=target_file
            )
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        normalizations.extend(header_norm)

        try:
            normalized_lines, hunk_repair_norm = _repair_missing_hunk_ranges(
                lines=normalized_lines, target_file=target_file, base_text=base_text
            )
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        normalizations.extend(hunk_repair_norm)

        try:
            normalized_lines, hunk_norm = _repair_hunk_header_counts(normalized_lines)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        normalizations.extend(hunk_norm)

        normalized = "\n".join(normalized_lines)
        normalized = _ensure_trailing_newline(normalized).text
        hunks = _parse_hunks(normalized_lines)
        if not hunks:
            raise ValueError("Diffen saknar giltiga @@-hunks. Regenerera.")

        patch_id = _sha256_id(normalized)
        # Deduplicate normalization flags
        normalizations = list(dict.fromkeys([n for n in normalizations if n]))
        return PreparedUnifiedDiff(
            target_file=target_file,
            normalized_diff=normalized,
            patch_id=patch_id,
            normalizations_applied=normalizations,
            hunks=hunks,
        )

    def apply(
        self,
        *,
        target_file: VirtualFileId,
        base_text: str,
        prepared: PreparedUnifiedDiff,
        max_fuzz: int,
        max_offset_lines: int,
        enable_whitespace_stage: bool,
    ) -> PatchApplyResult:
        if prepared.target_file != target_file:
            return PatchApplyResult(
                ok=False,
                next_text=base_text,
                error="Diffen matchar inte target_file. Regenerera.",
            )

        normalized_base = base_text.replace("\r\n", "\n").replace("\r", "\n")
        has_trailing_newline = normalized_base.endswith("\n")
        if normalized_base == "":
            base_lines: list[str] = []
        else:
            base_lines = normalized_base.split("\n")
            if has_trailing_newline and base_lines:
                base_lines = base_lines[:-1]

        hunks = _parse_hunk_blocks(prepared.normalized_diff)
        offsets: list[int] = []
        fuzz_level_used = 0
        whitespace_ignored = False
        blank_skips_total = 0
        line_delta = 0

        for hunk in hunks:
            old_lines, inserts = _build_apply_plan(hunk.lines)
            expected_index_raw = hunk.old_start - 1 + line_delta

            if not old_lines:
                insert_lines = inserts.get(-1, [])
                insert_at = min(max(expected_index_raw, 0), len(base_lines))
                offset = insert_at - expected_index_raw
                if abs(offset) > max_offset_lines:
                    return PatchApplyResult(
                        ok=False,
                        next_text=base_text,
                        error=(
                            "Patchen matchade bara med stor förskjutning i filen. "
                            "Regenerera patchen mot aktuell version."
                        ),
                        error_details=PatchApplyErrorDetails(
                            hunk_index=hunk.index,
                            hunk_header=hunk.header,
                            expected_snippet=_extract_expected_snippet(
                                prepared, hunk_index=hunk.index
                            ),
                            base_snippet=_extract_base_snippet(
                                base_text, expected_line=hunk.old_start
                            ),
                        ),
                    )
                base_lines = base_lines[:insert_at] + insert_lines + base_lines[insert_at:]
                offsets.append(offset)
                line_delta += hunk.new_count - hunk.old_count
                continue

            match = _find_hunk_match(
                base_lines=base_lines,
                old_lines=old_lines,
                expected_index=expected_index_raw,
                max_offset_lines=max_offset_lines,
                max_fuzz=0,
                ignore_ws=False,
                max_blank_skips=_MAX_BLANK_SKIPS_DEFAULT,
            )
            if match is None and enable_whitespace_stage:
                match = _find_hunk_match(
                    base_lines=base_lines,
                    old_lines=old_lines,
                    expected_index=expected_index_raw,
                    max_offset_lines=max_offset_lines,
                    max_fuzz=0,
                    ignore_ws=True,
                    max_blank_skips=_MAX_BLANK_SKIPS_DEFAULT,
                )
            if match is None and max_fuzz > 0:
                match = _find_hunk_match(
                    base_lines=base_lines,
                    old_lines=old_lines,
                    expected_index=expected_index_raw,
                    max_offset_lines=max_offset_lines,
                    max_fuzz=max_fuzz,
                    ignore_ws=False,
                    max_blank_skips=_MAX_BLANK_SKIPS_DEFAULT,
                )

            if match is None:
                return PatchApplyResult(
                    ok=False,
                    next_text=base_text,
                    error="Patchen kunde inte appliceras. Regenerera.",
                    error_details=PatchApplyErrorDetails(
                        hunk_index=hunk.index,
                        hunk_header=hunk.header,
                        expected_snippet=_extract_expected_snippet(prepared, hunk_index=hunk.index),
                        base_snippet=_extract_base_snippet(base_text, expected_line=hunk.old_start),
                    ),
                )

            offsets.append(match.offset)
            hunk_fuzz = match.fuzz
            if match.blank_skips > 0 or match.whitespace_ignored:
                hunk_fuzz = max(hunk_fuzz, 1)
            fuzz_level_used = max(fuzz_level_used, hunk_fuzz)
            whitespace_ignored = whitespace_ignored or match.whitespace_ignored
            blank_skips_total += match.blank_skips

            mapping_full: list[int | None] = [None] * len(old_lines)
            for idx, base_idx in enumerate(match.mapping):
                mapping_full[match.lead_skip + idx] = base_idx

            mapped_indices = [
                idx for idx, base_idx in enumerate(mapping_full) if base_idx is not None
            ]
            if not mapped_indices:
                return PatchApplyResult(
                    ok=False,
                    next_text=base_text,
                    error="Patchen kunde inte appliceras. Regenerera.",
                    error_details=PatchApplyErrorDetails(
                        hunk_index=hunk.index,
                        hunk_header=hunk.header,
                        expected_snippet=_extract_expected_snippet(prepared, hunk_index=hunk.index),
                        base_snippet=_extract_base_snippet(base_text, expected_line=hunk.old_start),
                    ),
                )

            first_mapped = min(mapped_indices)
            last_mapped = max(mapped_indices)
            start_idx = mapping_full[first_mapped]
            end_idx = mapping_full[last_mapped]
            if start_idx is None or end_idx is None:
                return PatchApplyResult(
                    ok=False,
                    next_text=base_text,
                    error="Patchen kunde inte appliceras. Regenerera.",
                    error_details=PatchApplyErrorDetails(
                        hunk_index=hunk.index,
                        hunk_header=hunk.header,
                        expected_snippet=_extract_expected_snippet(prepared, hunk_index=hunk.index),
                        base_snippet=_extract_base_snippet(base_text, expected_line=hunk.old_start),
                    ),
                )

            before_inserts: list[str] = []
            after_inserts: list[str] = []
            for key in sorted(inserts):
                if key < first_mapped:
                    before_inserts.extend(inserts[key])
                elif key > last_mapped:
                    after_inserts.extend(inserts[key])

            reverse_map = {
                base_idx: old_idx
                for old_idx, base_idx in enumerate(mapping_full)
                if base_idx is not None
            }

            next_lines: list[str] = []
            next_lines.extend(base_lines[:start_idx])
            next_lines.extend(before_inserts)
            for line_index in range(start_idx, end_idx + 1):
                if line_index in reverse_map:
                    old_index = reverse_map[line_index]
                    tag = old_lines[old_index].tag
                    if tag == " ":
                        next_lines.append(base_lines[line_index])
                    elif tag == "-":
                        pass
                    next_lines.extend(inserts.get(old_index, []))
                else:
                    next_lines.append(base_lines[line_index])
            next_lines.extend(after_inserts)
            next_lines.extend(base_lines[end_idx + 1 :])

            base_lines = next_lines
            line_delta += hunk.new_count - hunk.old_count

        max_offset = max((abs(offset) for offset in offsets), default=0)
        if max_offset > max_offset_lines:
            worst_hunk = (
                max(range(len(offsets)), key=lambda idx: abs(offsets[idx])) + 1 if offsets else None
            )
            worst_hunk_model = (
                prepared.hunks[worst_hunk - 1]
                if worst_hunk and worst_hunk <= len(prepared.hunks)
                else None
            )
            return PatchApplyResult(
                ok=False,
                next_text=base_text,
                error=(
                    "Patchen matchade bara med stor förskjutning i filen. "
                    "Regenerera patchen mot aktuell version."
                ),
                error_details=PatchApplyErrorDetails(
                    hunk_index=worst_hunk,
                    hunk_header=worst_hunk_model.header if worst_hunk_model else None,
                    expected_snippet=_extract_expected_snippet(prepared, hunk_index=worst_hunk)
                    if worst_hunk
                    else None,
                    base_snippet=_extract_base_snippet(
                        base_text, expected_line=worst_hunk_model.old_start
                    )
                    if worst_hunk_model
                    else None,
                ),
            )

        applied_cleanly = fuzz_level_used == 0 and max_offset <= 5 and blank_skips_total == 0
        next_text = "\n".join(base_lines)
        if has_trailing_newline:
            next_text += "\n"

        meta = PatchApplyMeta(
            fuzz_level_used=fuzz_level_used,
            hunks_total=len(hunks),
            offsets_per_hunk=offsets,
            max_offset=max_offset,
            whitespace_ignored=whitespace_ignored,
            applied_cleanly=applied_cleanly,
        )
        return PatchApplyResult(ok=True, next_text=next_text, meta=meta)
