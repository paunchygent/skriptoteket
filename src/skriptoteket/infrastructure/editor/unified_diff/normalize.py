from __future__ import annotations

import hashlib

from skriptoteket.protocols.editor_patches import PreparedUnifiedDiff
from skriptoteket.protocols.llm import VirtualFileId

from .errors import MALFORMED_PATCH_ERROR
from .normalize_steps import (
    ensure_trailing_newline,
    normalize_newlines,
    strip_bom_from_lines,
    strip_code_fences,
    strip_common_indentation,
    strip_empty_leading_trailing_lines,
    strip_invisible_chars,
    strip_patch_wrappers,
)
from .parse import (
    FILE_HEADER_RE,
    MAX_BLANK_SKIPS_DEFAULT,
    ParsedLine,
    build_apply_plan,
    extract_diff_git_header,
    extract_file_headers,
    find_hunk_match,
    parse_hunk_header,
    parse_hunks,
    split_hunk_sections,
)


def _path_basename(path: str) -> str:
    cleaned = path
    if cleaned.startswith("a/") or cleaned.startswith("b/"):
        cleaned = cleaned[2:]
    if cleaned.startswith("./"):
        cleaned = cleaned[2:]
    return cleaned


def _sha256_id(payload: str) -> str:
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _compute_hunk_counts(body_lines: list[str]) -> tuple[int, int]:
    old_count = 0
    new_count = 0
    for body_line in body_lines:
        if body_line.startswith("\\"):
            continue
        if not body_line:
            raise ValueError(MALFORMED_PATCH_ERROR)
        marker = body_line[0]
        if marker == " ":
            old_count += 1
            new_count += 1
        elif marker == "-":
            old_count += 1
        elif marker == "+":
            new_count += 1
        else:
            raise ValueError(MALFORMED_PATCH_ERROR)
    return old_count, new_count


def _repair_missing_hunk_ranges(
    *,
    lines: list[str],
    target_file: VirtualFileId,
    base_text: str | None,
) -> tuple[list[str], list[str]]:
    if base_text is None:
        return lines, []

    prefix, hunks, saw_header = split_hunk_sections(lines)
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
            raise ValueError(MALFORMED_PATCH_ERROR)

        if header_line is not None and parse_hunk_header(header_line):
            repaired_lines.append(header_line)
            repaired_lines.extend(body_lines)
            continue

        parsed_lines: list[ParsedLine] = []
        for body_line in body_lines:
            if body_line.startswith("\\"):
                continue
            if not body_line:
                raise ValueError(MALFORMED_PATCH_ERROR)
            marker = body_line[0]
            if marker not in {" ", "+", "-"}:
                raise ValueError(MALFORMED_PATCH_ERROR)
            parsed_lines.append(ParsedLine(tag=marker, text=body_line[1:]))

        old_lines, _ = build_apply_plan(parsed_lines)
        if not old_lines:
            raise ValueError("Diffen saknar kontext för att reparera @@-hunks. Regenerera.")

        match = find_hunk_match(
            base_lines=base_lines,
            old_lines=old_lines,
            expected_index=0,
            max_offset_lines=len(base_lines),
            max_fuzz=0,
            ignore_ws=False,
            max_blank_skips=MAX_BLANK_SKIPS_DEFAULT,
        )
        if match is None:
            match = find_hunk_match(
                base_lines=base_lines,
                old_lines=old_lines,
                expected_index=0,
                max_offset_lines=len(base_lines),
                max_fuzz=0,
                ignore_ws=True,
                max_blank_skips=MAX_BLANK_SKIPS_DEFAULT,
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


def _repair_hunk_header_counts(lines: list[str]) -> tuple[list[str], list[str]]:
    normalizations: list[str] = []
    out: list[str] = []
    idx = 0

    while idx < len(lines):
        line = lines[idx]
        header = parse_hunk_header(line)
        if not header:
            out.append(line)
            idx += 1
            continue

        body_start = idx + 1
        body_end = body_start
        while body_end < len(lines) and not parse_hunk_header(lines[body_end]):
            body_end += 1

        body = lines[body_start:body_end]
        if not body:
            raise ValueError(MALFORMED_PATCH_ERROR)

        old_count = 0
        new_count = 0
        for body_line in body:
            if body_line.startswith("\\"):
                continue
            if not body_line:
                raise ValueError(MALFORMED_PATCH_ERROR)
            marker = body_line[0]
            if marker == " ":
                old_count += 1
                new_count += 1
            elif marker == "-":
                old_count += 1
            elif marker == "+":
                new_count += 1
            else:
                raise ValueError(MALFORMED_PATCH_ERROR)

        if old_count != header.old_count or new_count != header.new_count:
            header_text = (
                f"@@ -{header.old_start},{old_count} +{header.new_start},{new_count} @@"
                f"{header.suffix}"
            )
            out.append(header_text)
            normalizations.append("rewrote_hunk_header_counts")
        else:
            out.append(line)

        out.extend(body)
        idx = body_end

    normalizations = list(dict.fromkeys(normalizations))
    return out, normalizations


def _repair_hunk_header_ranges(
    *, lines: list[str], base_text: str | None
) -> tuple[list[str], list[str]]:
    if base_text is None:
        return lines, []

    normalizations: list[str] = []
    base_text_norm = base_text.replace("\r\n", "\n").replace("\r", "\n")
    base_lines = base_text_norm.split("\n")
    if base_text_norm.endswith("\n") and base_lines:
        base_lines = base_lines[:-1]

    out: list[str] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        header = parse_hunk_header(line)
        if not header:
            out.append(line)
            idx += 1
            continue

        body_start = idx + 1
        body_end = body_start
        while body_end < len(lines) and not parse_hunk_header(lines[body_end]):
            body_end += 1

        body = lines[body_start:body_end]
        if not body:
            raise ValueError(MALFORMED_PATCH_ERROR)

        parsed_lines: list[ParsedLine] = []
        for body_line in body:
            if body_line.startswith("\\"):
                continue
            if not body_line:
                raise ValueError(MALFORMED_PATCH_ERROR)
            marker = body_line[0]
            if marker not in {" ", "+", "-"}:
                raise ValueError(MALFORMED_PATCH_ERROR)
            parsed_lines.append(ParsedLine(tag=marker, text=body_line[1:]))

        old_lines, _ = build_apply_plan(parsed_lines)
        if not old_lines:
            out.append(line)
            out.extend(body)
            idx = body_end
            continue

        expected_index = min(max(header.old_start - 1, 0), len(base_lines))
        match = find_hunk_match(
            base_lines=base_lines,
            old_lines=old_lines,
            expected_index=expected_index,
            max_offset_lines=len(base_lines),
            max_fuzz=0,
            ignore_ws=False,
            max_blank_skips=MAX_BLANK_SKIPS_DEFAULT,
        )
        if match is None:
            match = find_hunk_match(
                base_lines=base_lines,
                old_lines=old_lines,
                expected_index=expected_index,
                max_offset_lines=len(base_lines),
                max_fuzz=0,
                ignore_ws=True,
                max_blank_skips=MAX_BLANK_SKIPS_DEFAULT,
            )

        if match is None:
            out.append(line)
            out.extend(body)
            idx = body_end
            continue

        old_start = match.mapping[0] + 1
        new_start = old_start
        if old_start == header.old_start and new_start == header.new_start:
            out.append(line)
        else:
            out.append(
                f"@@ -{old_start},{header.old_count} +{new_start},{header.new_count} @@"
                f"{header.suffix}"
            )
            normalizations.append("rewrote_hunk_header_ranges")

        out.extend(body)
        idx = body_end

    normalizations = list(dict.fromkeys(normalizations))
    return out, normalizations


def _standardize_headers(
    *, lines: list[str], target_file: VirtualFileId
) -> tuple[list[str], list[str]]:
    normalizations: list[str] = []

    old_path, new_path = extract_file_headers(lines)
    if old_path is None or new_path is None:
        git_old, git_new = extract_diff_git_header(lines)
        if git_old and git_new:
            old_path, new_path = git_old, git_new
            normalizations.append("inferred_headers_from_diff_git")
        else:
            old_path = f"a/{target_file}"
            new_path = f"b/{target_file}"
            normalizations.append("synthesized_file_headers")

    if old_path == "/dev/null" or new_path == "/dev/null":
        raise ValueError("Diffen försöker skapa eller radera filer, vilket inte stöds.")

    old_base = _path_basename(old_path)
    new_base = _path_basename(new_path)
    if old_base != target_file or new_base != target_file:
        raise ValueError("Diffen berör en annan fil än den förväntade. Regenerera.")

    out: list[str] = []
    saw_old = False
    saw_new = False
    for line in lines:
        match = FILE_HEADER_RE.match(line)
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

    if not saw_old or not saw_new:
        injected: list[str] = [f"--- a/{target_file}", f"+++ b/{target_file}"]
        filtered = [line for line in out if not FILE_HEADER_RE.match(line)]
        out = injected + filtered
        normalizations.append("injected_standard_headers")

    normalizations = list(dict.fromkeys(normalizations))
    return out, normalizations


def _reject_multi_file_diff(lines: list[str]) -> None:
    header_count = sum(1 for line in lines if line.startswith("--- "))
    if header_count > 1:
        raise ValueError("Diffen innehåller flera filer. Regenerera med en fil i taget.")
    diff_git_count = sum(1 for line in lines if line.startswith("diff --git "))
    if diff_git_count > 1:
        raise ValueError("Diffen innehåller flera filer. Regenerera med en fil i taget.")


def prepare_unified_diff(
    *,
    target_file: VirtualFileId,
    unified_diff: str,
    base_text: str | None = None,
) -> PreparedUnifiedDiff:
    normalizations: list[str] = []
    text = unified_diff

    for step in (
        strip_bom_from_lines,
        normalize_newlines,
        strip_invisible_chars,
        strip_code_fences,
        strip_patch_wrappers,
        strip_common_indentation,
        strip_empty_leading_trailing_lines,
    ):
        result = step(text)
        text = result.text
        normalizations.extend(result.applied)

    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    _reject_multi_file_diff(lines)

    normalized_lines, header_norm = _standardize_headers(lines=lines, target_file=target_file)
    normalizations.extend(header_norm)

    normalized_lines, hunk_repair_norm = _repair_missing_hunk_ranges(
        lines=normalized_lines, target_file=target_file, base_text=base_text
    )
    normalizations.extend(hunk_repair_norm)

    normalized_lines, hunk_norm = _repair_hunk_header_counts(normalized_lines)
    normalizations.extend(hunk_norm)

    normalized_lines, range_norm = _repair_hunk_header_ranges(
        lines=normalized_lines, base_text=base_text
    )
    normalizations.extend(range_norm)

    normalized = "\n".join(normalized_lines)
    normalized = ensure_trailing_newline(normalized).text
    hunks = parse_hunks(normalized_lines)
    if not hunks:
        raise ValueError("Diffen saknar giltiga @@-hunks. Regenerera.")

    patch_id = _sha256_id(normalized)
    normalizations = list(dict.fromkeys([n for n in normalizations if n]))
    return PreparedUnifiedDiff(
        target_file=target_file,
        normalized_diff=normalized,
        patch_id=patch_id,
        normalizations_applied=normalizations,
        hunks=hunks,
    )
