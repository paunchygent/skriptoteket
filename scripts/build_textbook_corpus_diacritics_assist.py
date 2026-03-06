"""Generate LanguageTool-assisted diacritics patch proposals for textbook markdown.

Purpose:
    Produce conservative, auditable patch proposals that restore Swedish diacritics
    (a/o variants) in OCR-corrupted markdown without performing blind auto-rewrites.

Relationships:
    - Reads one restored markdown file from textbook corpus artifacts.
    - Queries a LanguageTool-compatible API:
      - Preferred: HuleEdu LanguageTool service (`POST /v1/check`)
      - Compatible fallback: LanguageTool public API (`POST /v2/check`)
    - Writes patch YAML files compatible with:
      `scripts/build_textbook_corpus_manual_restoration_workflow.py`.
    - Leaves all patch statuses as `proposed` so semantic approvals remain manual.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import socket
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from bisect import bisect_right
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import yaml

DEFAULT_PRIMARY_BASE_URL = "http://127.0.0.1:18085"
DEFAULT_FALLBACK_BASE_URL = "https://api.languagetool.org"
DEFAULT_OUTPUT_DIR = Path(".artifacts/textbook_corpus/diacritics")
DEFAULT_LANGUAGE = "sv-SE"

WORD_TOKEN_RE = re.compile(r"[A-Za-zÅÄÖåäö]+")
CHEM_LINE_RE = re.compile(
    r"(\d|[+\-=→⇌]|"
    r"\((?:aq|s|l|g)\)|"
    r"\b(?:mol|mmol|dm3|cm3|ml|mL|ph|pH|reaktion|jon|joner)\b)",
    re.IGNORECASE,
)

ELEMENT_SYMBOLS = {
    "H",
    "He",
    "Li",
    "Be",
    "B",
    "C",
    "N",
    "O",
    "F",
    "Ne",
    "Na",
    "Mg",
    "Al",
    "Si",
    "P",
    "S",
    "Cl",
    "Ar",
    "K",
    "Ca",
    "Sc",
    "Ti",
    "V",
    "Cr",
    "Mn",
    "Fe",
    "Co",
    "Ni",
    "Cu",
    "Zn",
    "Ga",
    "Ge",
    "As",
    "Se",
    "Br",
    "Kr",
    "Rb",
    "Sr",
    "Y",
    "Zr",
    "Nb",
    "Mo",
    "Tc",
    "Ru",
    "Rh",
    "Pd",
    "Ag",
    "Cd",
    "In",
    "Sn",
    "Sb",
    "Te",
    "I",
    "Xe",
    "Cs",
    "Ba",
    "La",
    "Ce",
    "Pr",
    "Nd",
    "Pm",
    "Sm",
    "Eu",
    "Gd",
    "Tb",
    "Dy",
    "Ho",
    "Er",
    "Tm",
    "Yb",
    "Lu",
    "Hf",
    "Ta",
    "W",
    "Re",
    "Os",
    "Ir",
    "Pt",
    "Au",
    "Hg",
    "Tl",
    "Pb",
    "Bi",
    "Po",
    "At",
    "Rn",
    "Fr",
    "Ra",
    "Ac",
    "Th",
    "Pa",
    "U",
    "Np",
    "Pu",
    "Am",
    "Cm",
    "Bk",
    "Cf",
    "Es",
    "Fm",
    "Md",
    "No",
    "Lr",
    "Rf",
    "Db",
    "Sg",
    "Bh",
    "Hs",
    "Mt",
    "Ds",
    "Rg",
    "Cn",
    "Nh",
    "Fl",
    "Mc",
    "Lv",
    "Ts",
    "Og",
}


class LanguageToolClientProtocol(Protocol):
    """Protocol for LanguageTool-compatible check clients."""

    def check(self, *, text: str, language: str) -> list["LanguageToolMatch"]:
        """Return match entries for a text segment."""

    @property
    def service_name(self) -> str:
        """Return a short client identifier."""

    @property
    def base_url(self) -> str:
        """Return the service base URL."""


@dataclass(frozen=True, slots=True)
class LanguageToolMatch:
    """Normalized LanguageTool match payload."""

    offset: int
    length: int
    replacements: tuple[str, ...]
    rule_id: str
    message: str


@dataclass(frozen=True, slots=True)
class LineReplacement:
    """One replacement decision within a specific line."""

    offset: int
    length: int
    before: str
    after: str
    rule_id: str
    message: str


@dataclass(frozen=True, slots=True)
class DiacriticsPatchSuggestion:
    """A line-scoped patch suggestion for manual workflow."""

    issue_id: str
    patch_id: str
    line_no: int
    expected_original: str
    replacement_line: str
    replacements: tuple[LineReplacement, ...]


@dataclass(frozen=True, slots=True)
class TextChunk:
    """Chunk of markdown text used for bounded LanguageTool requests."""

    start_line_no: int
    lines: tuple[str, ...]
    line_start_offsets: tuple[int, ...]
    text: str


@dataclass(frozen=True, slots=True)
class RunSummary:
    """Summary payload written after proposal generation."""

    generated_at: str
    input_markdown: str
    output_dir: str
    service_name: str
    service_base_url: str
    language: str
    request_count: int
    failed_chunk_count: int
    suggestion_count: int
    patch_files_written: int


class HuleEduV1LanguageToolClient(LanguageToolClientProtocol):
    """Client for HuleEdu LanguageTool service (`POST /v1/check`)."""

    def __init__(self, *, base_url: str, timeout_s: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s

    @property
    def service_name(self) -> str:
        return "huleedu-v1"

    @property
    def base_url(self) -> str:
        return self._base_url

    def check(self, *, text: str, language: str) -> list[LanguageToolMatch]:
        payload = {"text": text, "language": language}
        request = urllib.request.Request(
            f"{self._base_url}/v1/check",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        response_payload = _read_json_response(request=request, timeout_s=self._timeout_s)
        errors_obj = response_payload.get("errors")
        if not isinstance(errors_obj, list):
            return []
        return [_normalize_match(item) for item in errors_obj if isinstance(item, dict)]


class LanguageToolV2Client(LanguageToolClientProtocol):
    """Client for LanguageTool v2 (`POST /v2/check`)."""

    def __init__(self, *, base_url: str, timeout_s: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s

    @property
    def service_name(self) -> str:
        return "languagetool-v2"

    @property
    def base_url(self) -> str:
        return self._base_url

    def check(self, *, text: str, language: str) -> list[LanguageToolMatch]:
        payload = urllib.parse.urlencode({"text": text, "language": language}).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base_url}/v2/check",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response_payload = _read_json_response(request=request, timeout_s=self._timeout_s)
        matches_obj = response_payload.get("matches")
        if not isinstance(matches_obj, list):
            return []
        return [_normalize_match(item) for item in matches_obj if isinstance(item, dict)]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-markdown", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--language", default=DEFAULT_LANGUAGE)
    parser.add_argument("--primary-base-url", default=DEFAULT_PRIMARY_BASE_URL)
    parser.add_argument("--fallback-base-url", default=DEFAULT_FALLBACK_BASE_URL)
    parser.add_argument("--timeout-s", type=float, default=20.0)
    parser.add_argument("--chunk-max-chars", type=int, default=1800)
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Retries per chunk when the LanguageTool endpoint times out.",
    )
    parser.add_argument(
        "--retry-backoff-s",
        type=float,
        default=1.0,
        help="Base backoff for retries (exponential by attempt).",
    )
    parser.add_argument(
        "--max-requests-per-second",
        type=float,
        default=3.0,
        help="Throttle outbound LanguageTool requests to avoid rate limiting.",
    )
    parser.add_argument(
        "--max-suggestions",
        type=int,
        default=0,
        help="Optional cap for emitted suggestions; 0 means no cap.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def _read_json_response(*, request: urllib.request.Request, timeout_s: float) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {request.full_url}: {detail[:300]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Connection error for {request.full_url}: {exc}") from exc
    except TimeoutError as exc:
        raise RuntimeError(f"Timeout for {request.full_url}: {exc}") from exc
    except socket.timeout as exc:
        raise RuntimeError(f"Timeout for {request.full_url}: {exc}") from exc

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from {request.full_url}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Unexpected JSON shape from {request.full_url}: {type(payload)}")
    return payload


def _normalize_match(match_obj: dict[str, Any]) -> LanguageToolMatch:
    offset = _as_positive_int(match_obj.get("offset"))
    length = _as_positive_int(match_obj.get("length"))
    replacements_obj = match_obj.get("replacements")
    replacements: list[str] = []
    if isinstance(replacements_obj, list):
        for item in replacements_obj:
            if isinstance(item, dict):
                value = item.get("value")
                if isinstance(value, str) and value:
                    replacements.append(value)
            elif isinstance(item, str) and item:
                replacements.append(item)

    rule_id = ""
    rule_obj = match_obj.get("rule")
    if isinstance(rule_obj, dict):
        rule_id_obj = rule_obj.get("id")
        if isinstance(rule_id_obj, str):
            rule_id = rule_id_obj
    if not rule_id:
        rule_id_obj = match_obj.get("rule_id")
        if isinstance(rule_id_obj, str):
            rule_id = rule_id_obj

    message_obj = match_obj.get("message")
    message = message_obj if isinstance(message_obj, str) else ""
    return LanguageToolMatch(
        offset=offset,
        length=length,
        replacements=tuple(replacements),
        rule_id=rule_id,
        message=message,
    )


def _as_positive_int(value: object) -> int:
    if isinstance(value, int) and value >= 0:
        return value
    return 0


def _build_chunks(*, lines: list[str], max_chars: int) -> list[TextChunk]:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive.")

    chunks: list[TextChunk] = []
    current_lines: list[str] = []
    current_offsets: list[int] = []
    current_len = 0
    start_line_no = 1

    for index, line in enumerate(lines, start=1):
        additional = len(line) if not current_lines else len(line) + 1
        if current_lines and current_len + additional > max_chars:
            chunks.append(
                TextChunk(
                    start_line_no=start_line_no,
                    lines=tuple(current_lines),
                    line_start_offsets=tuple(current_offsets),
                    text="\n".join(current_lines),
                )
            )
            current_lines = []
            current_offsets = []
            current_len = 0
            start_line_no = index

        if not current_lines:
            current_offsets.append(0)
            current_len = len(line)
        else:
            current_offsets.append(current_len + 1)
            current_len += len(line) + 1
        current_lines.append(line)

    if current_lines:
        chunks.append(
            TextChunk(
                start_line_no=start_line_no,
                lines=tuple(current_lines),
                line_start_offsets=tuple(current_offsets),
                text="\n".join(current_lines),
            )
        )

    return chunks


def _fold_ascii(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _has_diacritic(value: str) -> bool:
    return any(ch in value for ch in "åäöÅÄÖ")


def _is_mixed_case_token(value: str) -> bool:
    return not (value.islower() or value.isupper() or value.istitle())


def _is_strict_diacritic_only_change(*, original: str, replacement: str) -> bool:
    if len(original) != len(replacement):
        return False
    changed = False
    for before, after in zip(original, replacement, strict=True):
        if before == after:
            continue
        changed = True
        if before.lower() not in {"a", "o"}:
            return False
        if after not in "åäöÅÄÖ":
            return False
        if _fold_ascii(before).casefold() != _fold_ascii(after).casefold():
            return False
    return changed


def _looks_like_chemistry_sensitive_token(*, token: str, line_text: str) -> bool:
    if token in ELEMENT_SYMBOLS:
        return True
    if _is_mixed_case_token(token):
        return True
    if CHEM_LINE_RE.search(line_text) and token[:1].isupper() and len(token) <= 4:
        return True
    return False


def _match_case(*, source: str, target: str) -> str:
    if source.isupper():
        return target.upper()
    if source[:1].isupper() and source[1:].islower():
        return target[:1].upper() + target[1:]
    if source.islower():
        return target.lower()
    return target


def _select_diacritic_replacement(*, original: str, replacements: tuple[str, ...]) -> str | None:
    if not WORD_TOKEN_RE.fullmatch(original):
        return None

    folded_original = _fold_ascii(original).casefold()
    candidates: list[str] = []
    for replacement in replacements:
        if not WORD_TOKEN_RE.fullmatch(replacement):
            continue
        if replacement == original:
            continue
        if not _has_diacritic(replacement):
            continue
        if _fold_ascii(replacement).casefold() != folded_original:
            continue
        adjusted = _match_case(source=original, target=replacement)
        if adjusted not in candidates:
            candidates.append(adjusted)

    if len(candidates) != 1:
        return None
    return candidates[0]


def _allow_candidate(*, original: str, replacement: str, line_text: str) -> bool:
    if not _is_strict_diacritic_only_change(original=original, replacement=replacement):
        return False
    if _looks_like_chemistry_sensitive_token(token=original, line_text=line_text):
        return False
    return True


def _non_overlapping(events: list[LineReplacement]) -> bool:
    ordered = sorted(events, key=lambda item: item.offset)
    for first, second in zip(ordered, ordered[1:], strict=False):
        if first.offset + first.length > second.offset:
            return False
    return True


def _build_issue_id(*, line_no: int, before: str, after: str) -> str:
    digest = hashlib.sha1(f"{line_no}:{before}->{after}".encode("utf-8")).hexdigest()[:10].upper()
    return f"ISSUE-DIACRITIC-L{line_no:05d}-{digest}"


def suggest_diacritics_patches(
    *,
    markdown_text: str,
    language: str,
    checker: LanguageToolClientProtocol,
    chunk_max_chars: int,
    max_requests_per_second: float,
    max_suggestions: int,
    max_retries: int,
    retry_backoff_s: float,
) -> tuple[list[DiacriticsPatchSuggestion], int, int]:
    """Return conservative line replacement suggestions from LanguageTool matches."""
    lines = markdown_text.splitlines()
    chunks = _build_chunks(lines=lines, max_chars=chunk_max_chars)
    requests_made = 0
    failed_chunks = 0
    suggestions: list[DiacriticsPatchSuggestion] = []
    interval_s = 0.0 if max_requests_per_second <= 0 else (1.0 / max_requests_per_second)

    for chunk in chunks:
        if max_suggestions > 0 and len(suggestions) >= max_suggestions:
            break

        before_request = time.monotonic()
        matches: list[LanguageToolMatch] = []
        for attempt in range(max_retries + 1):
            try:
                matches = checker.check(text=chunk.text, language=language)
                requests_made += 1
                break
            except RuntimeError:
                requests_made += 1
                if attempt >= max_retries:
                    failed_chunks += 1
                    matches = []
                    break
                backoff = max(0.0, retry_backoff_s) * (2**attempt)
                if backoff > 0:
                    time.sleep(backoff)

        line_events: dict[int, list[LineReplacement]] = {}
        for match in matches:
            if match.length <= 0 or match.offset < 0:
                continue
            end_offset = match.offset + match.length
            if end_offset > len(chunk.text):
                continue

            line_index = bisect_right(chunk.line_start_offsets, match.offset) - 1
            if line_index < 0 or line_index >= len(chunk.lines):
                continue

            line_start = chunk.line_start_offsets[line_index]
            line_text = chunk.lines[line_index]
            line_end = line_start + len(line_text)
            if end_offset > line_end:
                continue

            local_offset = match.offset - line_start
            original_token = line_text[local_offset : local_offset + match.length]
            replacement_token = _select_diacritic_replacement(
                original=original_token,
                replacements=match.replacements,
            )
            if not replacement_token:
                continue
            if not _allow_candidate(
                original=original_token,
                replacement=replacement_token,
                line_text=line_text,
            ):
                continue

            if replacement_token == original_token:
                continue

            line_no = chunk.start_line_no + line_index
            line_events.setdefault(line_no, []).append(
                LineReplacement(
                    offset=local_offset,
                    length=match.length,
                    before=original_token,
                    after=replacement_token,
                    rule_id=match.rule_id,
                    message=match.message,
                )
            )

        for line_no, events in line_events.items():
            if not _non_overlapping(events):
                continue
            original_line = lines[line_no - 1]
            updated_line = original_line
            for event in sorted(events, key=lambda item: item.offset, reverse=True):
                updated_line = (
                    updated_line[: event.offset]
                    + event.after
                    + updated_line[event.offset + event.length :]
                )
            if updated_line == original_line:
                continue

            issue_id = _build_issue_id(line_no=line_no, before=original_line, after=updated_line)
            suggestions.append(
                DiacriticsPatchSuggestion(
                    issue_id=issue_id,
                    patch_id=f"PATCH-{issue_id}",
                    line_no=line_no,
                    expected_original=original_line,
                    replacement_line=updated_line,
                    replacements=tuple(sorted(events, key=lambda item: item.offset)),
                )
            )
            if max_suggestions > 0 and len(suggestions) >= max_suggestions:
                break

        elapsed = time.monotonic() - before_request
        if interval_s > elapsed:
            time.sleep(interval_s - elapsed)

    return suggestions, requests_made, failed_chunks


def _patch_payload(
    *,
    suggestion: DiacriticsPatchSuggestion,
    service_name: str,
    service_base_url: str,
    language: str,
) -> dict[str, Any]:
    return {
        "version": 1,
        "patch_id": suggestion.patch_id,
        "issue_id": suggestion.issue_id,
        "status": "proposed",
        "author": "",
        "verifier": "",
        "verified_at": "",
        "rationale": "LanguageTool diacritics-only suggestion. Manual verification required.",
        "source": {
            "line_no": suggestion.line_no,
            "expected_original": suggestion.expected_original,
        },
        "change": {
            "mode": "replace_line",
            "replacement": suggestion.replacement_line,
        },
        "review": {
            "decision": "pending",
            "notes": "",
        },
        "metadata": {
            "service_name": service_name,
            "service_base_url": service_base_url,
            "language": language,
            "replacements": [asdict(item) for item in suggestion.replacements],
        },
    }


def _write_yaml(path: Path, payload: dict[str, Any], *, dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any], *, dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _resolve_client(
    *,
    primary_base_url: str,
    fallback_base_url: str,
    timeout_s: float,
    language: str,
) -> LanguageToolClientProtocol:
    attempts: list[tuple[str, str]] = [
        ("huleedu-v1", primary_base_url),
        ("languagetool-v2", primary_base_url),
    ]
    if fallback_base_url.strip() and fallback_base_url.strip() != primary_base_url.strip():
        attempts.extend(
            [
                ("huleedu-v1", fallback_base_url),
                ("languagetool-v2", fallback_base_url),
            ]
        )

    errors: list[str] = []
    for mode, base_url in attempts:
        client: LanguageToolClientProtocol
        if mode == "huleedu-v1":
            client = HuleEduV1LanguageToolClient(base_url=base_url, timeout_s=timeout_s)
        else:
            client = LanguageToolV2Client(base_url=base_url, timeout_s=timeout_s)

        try:
            client.check(text="Det ar ett test.", language=language)
            return client
        except RuntimeError as exc:
            errors.append(f"{mode}@{base_url}: {exc}")

    details = "\n".join(errors)
    raise SystemExit(f"Could not connect to any LanguageTool endpoint.\n{details}")


def run(
    *,
    input_markdown: Path,
    output_dir: Path,
    language: str,
    primary_base_url: str,
    fallback_base_url: str,
    timeout_s: float,
    chunk_max_chars: int,
    max_requests_per_second: float,
    max_suggestions: int,
    max_retries: int,
    retry_backoff_s: float,
    dry_run: bool,
) -> RunSummary:
    """Generate diacritics patch proposals and write artifact reports."""
    source_text = input_markdown.read_text(encoding="utf-8")
    client = _resolve_client(
        primary_base_url=primary_base_url,
        fallback_base_url=fallback_base_url,
        timeout_s=timeout_s,
        language=language,
    )
    suggestions, request_count, failed_chunk_count = suggest_diacritics_patches(
        markdown_text=source_text,
        language=language,
        checker=client,
        chunk_max_chars=chunk_max_chars,
        max_requests_per_second=max_requests_per_second,
        max_suggestions=max_suggestions,
        max_retries=max_retries,
        retry_backoff_s=retry_backoff_s,
    )

    patch_dir = output_dir / "manual_fixes"
    report_dir = output_dir / "reports"
    rows = []
    for suggestion in suggestions:
        payload = _patch_payload(
            suggestion=suggestion,
            service_name=client.service_name,
            service_base_url=client.base_url,
            language=language,
        )
        rows.append(payload)
        _write_yaml(patch_dir / f"{suggestion.issue_id}.yaml", payload, dry_run=dry_run)

    suggestions_json = {
        "generated_at": datetime.now(UTC).isoformat(),
        "input_markdown": str(input_markdown),
        "language": language,
        "service_name": client.service_name,
        "service_base_url": client.base_url,
        "request_count": request_count,
        "failed_chunk_count": failed_chunk_count,
        "suggestion_count": len(suggestions),
        "suggestions": rows,
    }
    _write_json(
        report_dir / f"{input_markdown.stem}.diacritics-suggestions.json",
        suggestions_json,
        dry_run=dry_run,
    )

    summary = RunSummary(
        generated_at=datetime.now(UTC).isoformat(),
        input_markdown=str(input_markdown),
        output_dir=str(output_dir),
        service_name=client.service_name,
        service_base_url=client.base_url,
        language=language,
        request_count=request_count,
        failed_chunk_count=failed_chunk_count,
        suggestion_count=len(suggestions),
        patch_files_written=0 if dry_run else len(suggestions),
    )
    _write_json(
        report_dir / f"{input_markdown.stem}.diacritics-summary.json",
        asdict(summary),
        dry_run=dry_run,
    )
    return summary


def main() -> None:
    args = _parse_args()
    summary = run(
        input_markdown=args.input_markdown.resolve(),
        output_dir=args.output_dir.resolve(),
        language=args.language,
        primary_base_url=args.primary_base_url,
        fallback_base_url=args.fallback_base_url,
        timeout_s=args.timeout_s,
        chunk_max_chars=args.chunk_max_chars,
        max_requests_per_second=args.max_requests_per_second,
        max_suggestions=args.max_suggestions,
        max_retries=args.max_retries,
        retry_backoff_s=args.retry_backoff_s,
        dry_run=args.dry_run,
    )
    print(
        json.dumps(
            asdict(summary),
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
