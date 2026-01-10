from __future__ import annotations

import hashlib
import os
import re
import subprocess
import tempfile
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


@dataclass(frozen=True, slots=True)
class _NormalizationResult:
    text: str
    applied: list[str]


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


def _parse_patch_output_for_hunks(
    output: str, *, hunks_total: int
) -> tuple[list[int], list[int], int | None]:
    offsets_by_hunk: dict[int, int] = {}
    fuzzes_by_hunk: dict[int, int] = {}
    failed_hunk: int | None = None

    for line in output.splitlines():
        if "Hunk #" not in line:
            continue
        hunk_match = re.search(r"Hunk\s+#(\d+)", line)
        if not hunk_match:
            continue
        hunk_index = int(hunk_match.group(1))

        if "FAILED" in line:
            failed_hunk = hunk_index
            continue

        if "succeeded" in line:
            # Examples:
            # Hunk #1 succeeded at 3.
            # Hunk #2 succeeded at 10 (offset 2 lines).
            # Hunk #3 succeeded at 20 with fuzz 1 (offset -3 lines).
            fuzz_match = re.search(r"with fuzz\s+(\d+)", line)
            offset_match = re.search(r"offset\s+(-?\d+)\s+lines", line)
            fuzzes_by_hunk[hunk_index] = int(fuzz_match.group(1)) if fuzz_match else 0
            offsets_by_hunk[hunk_index] = int(offset_match.group(1)) if offset_match else 0

    offsets = [offsets_by_hunk.get(idx, 0) for idx in range(1, hunks_total + 1)]
    fuzzes = [fuzzes_by_hunk.get(idx, 0) for idx in range(1, hunks_total + 1)]
    return offsets, fuzzes, failed_hunk


class SubprocessUnifiedDiffApplier(UnifiedDiffApplierProtocol):
    def prepare(self, *, target_file: VirtualFileId, unified_diff: str) -> PreparedUnifiedDiff:
        normalizations: list[str] = []
        text = unified_diff

        for step in (
            _strip_bom_from_lines,
            _normalize_newlines,
            _strip_invisible_chars,
            _strip_code_fences,
            _strip_common_indentation,
            _strip_empty_leading_trailing_lines,
            _ensure_trailing_newline,
        ):
            result = step(text)
            text = result.text
            normalizations.extend(result.applied)

        lines = text.split("\n")
        _reject_multi_file_diff(lines)
        try:
            normalized_lines, header_norm = _standardize_headers(
                lines=lines, target_file=target_file
            )
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        normalizations.extend(header_norm)

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

        stages: list[tuple[int, bool]] = [(0, False)]
        if enable_whitespace_stage:
            stages.append((0, True))
        for fuzz in range(1, max_fuzz + 1):
            stages.append((fuzz, False))

        last_error: str | None = None
        last_error_details: PatchApplyErrorDetails | None = None

        for fuzz, ignore_ws in stages:
            with tempfile.TemporaryDirectory(prefix="skriptoteket-edit-ops-") as tmpdir:
                file_path = os.path.join(tmpdir, str(target_file))
                patch_path = os.path.join(tmpdir, "proposal.patch")
                with open(file_path, "w", encoding="utf-8", newline="\n") as fp:
                    fp.write(base_text)
                with open(patch_path, "w", encoding="utf-8", newline="\n") as fp:
                    fp.write(prepared.normalized_diff)

                cmd: list[str] = [
                    "patch",
                    "-p1",
                    "-F",
                    str(fuzz),
                    "-i",
                    patch_path,
                    "-d",
                    tmpdir,
                    "-N",
                    "-t",
                ]
                if ignore_ws:
                    cmd.append("-l")

                env = dict(os.environ)
                env.setdefault("LC_ALL", "C")

                try:
                    proc = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        env=env,
                        timeout=10,
                    )
                except FileNotFoundError:
                    return PatchApplyResult(
                        ok=False,
                        next_text=base_text,
                        error="Servern saknar verktyget 'patch'.",
                    )
                except subprocess.TimeoutExpired:
                    return PatchApplyResult(
                        ok=False,
                        next_text=base_text,
                        error="Patchen tog för lång tid att applicera. Regenerera och försök igen.",
                    )

                combined_output = (proc.stdout or "") + "\n" + (proc.stderr or "")
                offsets, fuzzes, failed_hunk = _parse_patch_output_for_hunks(
                    combined_output, hunks_total=len(prepared.hunks)
                )
                fuzz_used = max(fuzzes) if fuzzes else 0
                max_offset = max((abs(o) for o in offsets), default=0)

                if proc.returncode != 0:
                    last_error = "Patchen kunde inte appliceras. Regenerera."
                    if failed_hunk is not None and 1 <= failed_hunk <= len(prepared.hunks):
                        hunk = prepared.hunks[failed_hunk - 1]
                        last_error_details = PatchApplyErrorDetails(
                            hunk_index=failed_hunk,
                            hunk_header=hunk.header,
                            expected_snippet=_extract_expected_snippet(
                                prepared, hunk_index=failed_hunk
                            ),
                            base_snippet=_extract_base_snippet(
                                base_text, expected_line=hunk.old_start
                            ),
                        )
                    continue

                with open(file_path, "r", encoding="utf-8") as fp:
                    patched = fp.read()

                if max_offset > max_offset_lines:
                    worst_hunk = (
                        max(range(len(offsets)), key=lambda idx: abs(offsets[idx])) + 1
                        if offsets
                        else None
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
                            expected_snippet=_extract_expected_snippet(
                                prepared, hunk_index=worst_hunk
                            )
                            if worst_hunk
                            else None,
                            base_snippet=_extract_base_snippet(
                                base_text, expected_line=worst_hunk_model.old_start
                            )
                            if worst_hunk_model
                            else None,
                        ),
                    )

                meta = PatchApplyMeta(
                    fuzz_level_used=fuzz_used,
                    hunks_total=len(prepared.hunks),
                    offsets_per_hunk=offsets,
                    max_offset=max_offset,
                    whitespace_ignored=ignore_ws,
                    applied_cleanly=(fuzz_used == 0 and max_offset <= 5),
                )
                return PatchApplyResult(ok=True, next_text=patched, meta=meta)

        return PatchApplyResult(
            ok=False,
            next_text=base_text,
            error=last_error or "Patchen kunde inte appliceras. Regenerera.",
            error_details=last_error_details,
        )
