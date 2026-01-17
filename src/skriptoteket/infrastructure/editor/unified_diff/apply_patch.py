from __future__ import annotations

from collections import OrderedDict
from typing import Final

from skriptoteket.protocols.editor_patches import (
    PatchApplyErrorDetails,
    PatchApplyMeta,
    PatchApplyResult,
    PreparedUnifiedDiff,
)
from skriptoteket.protocols.llm import VirtualFileId

from .parse import (
    MAX_BLANK_SKIPS_DEFAULT,
    ParsedHunk,
    build_apply_plan,
    find_hunk_match,
    parse_hunk_blocks,
)

_PARSED_HUNK_CACHE_MAX: Final[int] = 128
_PARSED_HUNK_CACHE: OrderedDict[str, list[ParsedHunk]] = OrderedDict()


def _get_parsed_hunks(prepared: PreparedUnifiedDiff) -> list[ParsedHunk]:
    cached = _PARSED_HUNK_CACHE.get(prepared.patch_id)
    if cached is not None:
        _PARSED_HUNK_CACHE.move_to_end(prepared.patch_id)
        return cached

    parsed = parse_hunk_blocks(prepared.normalized_diff)
    _PARSED_HUNK_CACHE[prepared.patch_id] = parsed
    if len(_PARSED_HUNK_CACHE) > _PARSED_HUNK_CACHE_MAX:
        _PARSED_HUNK_CACHE.popitem(last=False)
    return parsed


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
    center = max(expected_line - 1, 0)
    start = max(center - 4, 0)
    end = min(center + 8, len(lines))
    snippet = "\n".join(lines[start:end]).strip("\n")
    return snippet


def apply_prepared_patch(
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

    hunks = _get_parsed_hunks(prepared)
    offsets: list[int] = []
    fuzz_level_used = 0
    whitespace_ignored = False
    blank_skips_total = 0
    line_delta = 0

    for hunk in hunks:
        old_lines, inserts = build_apply_plan(hunk.lines)
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
                        expected_snippet=_extract_expected_snippet(prepared, hunk_index=hunk.index),
                        base_snippet=_extract_base_snippet(base_text, expected_line=hunk.old_start),
                    ),
                )
            base_lines = base_lines[:insert_at] + insert_lines + base_lines[insert_at:]
            offsets.append(offset)
            line_delta += hunk.new_count - hunk.old_count
            continue

        match = find_hunk_match(
            base_lines=base_lines,
            old_lines=old_lines,
            expected_index=expected_index_raw,
            max_offset_lines=max_offset_lines,
            max_fuzz=0,
            ignore_ws=False,
            max_blank_skips=MAX_BLANK_SKIPS_DEFAULT,
        )
        if match is None and enable_whitespace_stage:
            match = find_hunk_match(
                base_lines=base_lines,
                old_lines=old_lines,
                expected_index=expected_index_raw,
                max_offset_lines=max_offset_lines,
                max_fuzz=0,
                ignore_ws=True,
                max_blank_skips=MAX_BLANK_SKIPS_DEFAULT,
            )
        if match is None and max_fuzz > 0:
            match = find_hunk_match(
                base_lines=base_lines,
                old_lines=old_lines,
                expected_index=expected_index_raw,
                max_offset_lines=max_offset_lines,
                max_fuzz=max_fuzz,
                ignore_ws=False,
                max_blank_skips=MAX_BLANK_SKIPS_DEFAULT,
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

        mapped_indices = [idx for idx, base_idx in enumerate(mapping_full) if base_idx is not None]
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
