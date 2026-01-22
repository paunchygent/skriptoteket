"""Inline completion normalization helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Literal

_CODE_FENCE_PATTERN = re.compile(r"```[a-zA-Z0-9_-]*\n(.*?)```", re.DOTALL)
_QUOTE_CHARS = ("'", '"')

_CURSOR_OVERLAP_WINDOW_CHARS = 512
_REPLACE_SUFFIX_MAX_CHARS = 24

DropReason = Literal[
    "empty_input",
    "empty_after_cleanup",
    "cursor_overlap_wiped_all",
    "contiguous_echo",
    "dedup_wiped_all",
]


@dataclass(frozen=True, slots=True)
class NormalizedInlineCompletion:
    completion: str
    prefix_overlap_chars: int = 0
    suffix_overlap_chars: int = 0
    replace_suffix_chars: int = 0
    drop_reason: DropReason | None = None


def _looks_like_fence_tag(line: str) -> bool:
    tag = line.strip()
    if not tag:
        return False
    if len(tag) > 32:
        return False
    return all(ch.isalnum() or ch in ("-", "_", "+", ".") for ch in tag)


def _extract_first_fenced_block(text: str) -> str | None:
    match = _CODE_FENCE_PATTERN.search(text)
    if not match:
        if "```" not in text:
            return None
        parts = text.split("```", 2)
        if len(parts) < 2:
            return None
        content = parts[1]
    else:
        content = match.group(1)

    if "\n" in content:
        first_line, rest = content.split("\n", 1)
        if _looks_like_fence_tag(first_line):
            content = rest
    return content


def _strip_surrounding_quotes(text: str) -> str:
    stripped = text.strip()
    if len(stripped) < 2:
        return text
    if stripped[0] == stripped[-1] and stripped[0] in _QUOTE_CHARS:
        try:
            loaded = json.loads(stripped)
            return loaded if isinstance(loaded, str) else stripped[1:-1]
        except json.JSONDecodeError:
            return stripped[1:-1]
    return text


def _choose_sentinel(*parts: str) -> str:
    for codepoint in range(1, 32):
        sentinel = chr(codepoint)
        if all(sentinel not in part for part in parts):
            return sentinel
    return "\x00"


def _slice_tail(text: str, limit: int) -> str:
    if limit <= 0:
        return ""
    return text[-limit:] if len(text) > limit else text


def _slice_head(text: str, limit: int) -> str:
    if limit <= 0:
        return ""
    return text[:limit] if len(text) > limit else text


def _tokenize_non_whitespace(text: str) -> list[tuple[str, int, int]]:
    tokens: list[tuple[str, int, int]] = []
    idx = 0
    while idx < len(text):
        ch = text[idx]
        if ch.isspace():
            idx += 1
            continue
        start = idx
        if ch.isalnum() or ch == "_":
            idx += 1
            while idx < len(text) and (text[idx].isalnum() or text[idx] == "_"):
                idx += 1
        else:
            idx += 1
        tokens.append((text[start:idx], start, idx))
    return tokens


def _is_identifier_char(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def _longest_suffix_prefix_overlap(prefix: str, completion: str) -> int:
    if not prefix or not completion:
        return 0
    max_len = min(len(prefix), len(completion))
    if max_len <= 0:
        return 0
    pattern = completion[:max_len]
    tail = prefix[-max_len:]
    sentinel = _choose_sentinel(pattern, tail)
    combined = f"{pattern}{sentinel}{tail}"
    pi = [0] * len(combined)
    for idx in range(1, len(combined)):
        j = pi[idx - 1]
        while j > 0 and combined[idx] != combined[j]:
            j = pi[j - 1]
        if combined[idx] == combined[j]:
            j += 1
        pi[idx] = j
    return pi[-1]


def _longest_suffix_prefix_token_overlap(prefix: str, completion: str) -> int:
    prefix_tokens = _tokenize_non_whitespace(prefix)
    completion_tokens = _tokenize_non_whitespace(completion)
    if not prefix_tokens or not completion_tokens:
        return 0
    prefix_values = [token[0] for token in prefix_tokens]
    completion_values = [token[0] for token in completion_tokens]
    max_tokens = min(len(prefix_values), len(completion_values))
    for size in range(max_tokens, 0, -1):
        if prefix_values[-size:] == completion_values[:size]:
            return completion_tokens[size - 1][2]
    return 0


def _longest_prefix_suffix_token_overlap(completion: str, suffix: str) -> int:
    completion_tokens = _tokenize_non_whitespace(completion)
    suffix_tokens = _tokenize_non_whitespace(suffix)
    if not completion_tokens or not suffix_tokens:
        return 0
    completion_values = [token[0] for token in completion_tokens]
    suffix_values = [token[0] for token in suffix_tokens]
    max_tokens = min(len(completion_values), len(suffix_values))
    for size in range(max_tokens, 0, -1):
        if completion_values[-size:] == suffix_values[:size]:
            start_offset = completion_tokens[-size][1]
            return len(completion) - start_offset
    return 0


def _compute_replace_suffix_chars(prefix: str, completion: str, suffix: str) -> int:
    if not prefix or not completion or not suffix:
        return 0
    if not _is_identifier_char(prefix[-1]):
        return 0
    if not _is_identifier_char(completion[0]):
        return 0
    if not _is_identifier_char(suffix[0]):
        return 0
    max_len = min(len(completion), len(suffix), _REPLACE_SUFFIX_MAX_CHARS)
    overlap = 0
    while overlap < max_len:
        if completion[overlap] != suffix[overlap]:
            break
        if not _is_identifier_char(completion[overlap]):
            break
        overlap += 1
    return overlap


def _prefix_overlap_chars(prefix: str, completion: str) -> int:
    prefix_tail = _slice_tail(prefix, _CURSOR_OVERLAP_WINDOW_CHARS)
    completion_head = _slice_head(completion, _CURSOR_OVERLAP_WINDOW_CHARS)
    exact = _longest_suffix_prefix_overlap(prefix_tail, completion_head)
    token_overlap = _longest_suffix_prefix_token_overlap(prefix_tail, completion_head)
    return max(exact, token_overlap)


def _suffix_overlap_chars(completion: str, suffix: str) -> int:
    completion_tail = _slice_tail(completion, _CURSOR_OVERLAP_WINDOW_CHARS)
    suffix_head = _slice_head(suffix, _CURSOR_OVERLAP_WINDOW_CHARS)
    exact = _longest_suffix_prefix_overlap(completion_tail, suffix_head)
    token_overlap = _longest_prefix_suffix_token_overlap(completion_tail, suffix_head)
    return max(exact, token_overlap)


def _strip_prefix_overlap(prefix: str, completion: str) -> tuple[str, int]:
    removed = 0
    while completion:
        overlap = _prefix_overlap_chars(prefix, completion)
        if overlap <= 0:
            break
        if overlap == 1 and len(completion) == 1:
            break
        completion = completion[overlap:]
        removed += overlap
    return completion, removed


def _strip_suffix_overlap(completion: str, suffix: str) -> tuple[str, int]:
    removed = 0
    while completion:
        overlap = _suffix_overlap_chars(completion, suffix)
        if overlap <= 0:
            break
        completion = completion[:-overlap]
        removed += overlap
    return completion, removed


def _strip_cursor_overlaps(
    *, completion: str, prefix: str, suffix: str
) -> NormalizedInlineCompletion:
    if not completion:
        return NormalizedInlineCompletion(completion="")
    stripped, prefix_removed = _strip_prefix_overlap(prefix, completion)
    replace_suffix_chars = _compute_replace_suffix_chars(prefix, stripped, suffix)
    replace_suffix_chars = min(replace_suffix_chars, len(stripped), len(suffix))
    stripped_after_suffix, suffix_removed = _strip_suffix_overlap(stripped, suffix)
    if not stripped_after_suffix and replace_suffix_chars > 0:
        stripped_after_suffix = stripped
        suffix_removed = 0
    return NormalizedInlineCompletion(
        completion=stripped_after_suffix,
        prefix_overlap_chars=prefix_removed,
        suffix_overlap_chars=suffix_removed,
        replace_suffix_chars=replace_suffix_chars,
    )


def _contiguous_echo_ratio(prefix: str, suffix: str, completion: str) -> float:
    completion_lines = [line for line in completion.splitlines() if line.strip()]
    if len(completion_lines) < 2:
        return 0.0
    echoed_indexes: set[int] = set()
    for idx in range(len(completion_lines) - 1):
        chunk = "\n".join(completion_lines[idx : idx + 2])
        if chunk in prefix or chunk in suffix:
            echoed_indexes.add(idx)
            echoed_indexes.add(idx + 1)
    if not completion_lines:
        return 0.0
    return len(echoed_indexes) / len(completion_lines)


def _should_drop_contiguous_echo(prefix: str, suffix: str, completion: str) -> bool:
    completion_lines = [line for line in completion.splitlines() if line.strip()]
    if len(completion_lines) < 2:
        return False
    ratio = _contiguous_echo_ratio(prefix=prefix, suffix=suffix, completion=completion)
    if ratio >= 0.999:
        return True
    if len(completion_lines) <= 4 and ratio >= 0.6:
        return True
    return False


def _strip_duplicate_lines(prefix: str, suffix: str, completion: str) -> str:
    prefix_lines = {line.strip() for line in prefix.splitlines() if line.strip()}
    suffix_lines = {line.strip() for line in suffix.splitlines() if line.strip()}
    cleaned_lines: list[str] = []
    for line in completion.splitlines():
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append(line)
            continue
        non_ws_len = len(re.sub(r"\s+", "", line))
        if non_ws_len >= 12 and (stripped in prefix_lines or stripped in suffix_lines):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip("\n")


def normalize_inline_completion(
    *, completion: str, prefix: str, suffix: str
) -> NormalizedInlineCompletion:
    if not completion:
        return NormalizedInlineCompletion(completion="", drop_reason="empty_input")
    fenced = _extract_first_fenced_block(completion)
    if fenced is not None:
        completion = fenced
    completion = _strip_surrounding_quotes(completion)
    completion = completion.strip("\n")
    if not completion:
        return NormalizedInlineCompletion(completion="", drop_reason="empty_after_cleanup")

    overlap_result = _strip_cursor_overlaps(
        completion=completion,
        prefix=prefix,
        suffix=suffix,
    )
    completion = overlap_result.completion.strip("\n")
    if not completion:
        return NormalizedInlineCompletion(
            completion="",
            prefix_overlap_chars=overlap_result.prefix_overlap_chars,
            suffix_overlap_chars=overlap_result.suffix_overlap_chars,
            replace_suffix_chars=overlap_result.replace_suffix_chars,
            drop_reason="cursor_overlap_wiped_all",
        )
    if _should_drop_contiguous_echo(prefix, suffix, completion):
        return NormalizedInlineCompletion(
            completion="",
            prefix_overlap_chars=overlap_result.prefix_overlap_chars,
            suffix_overlap_chars=overlap_result.suffix_overlap_chars,
            replace_suffix_chars=overlap_result.replace_suffix_chars,
            drop_reason="contiguous_echo",
        )
    completion = _strip_duplicate_lines(prefix, suffix, completion)
    completion = completion.strip("\n")
    if not completion:
        return NormalizedInlineCompletion(
            completion="",
            prefix_overlap_chars=overlap_result.prefix_overlap_chars,
            suffix_overlap_chars=overlap_result.suffix_overlap_chars,
            replace_suffix_chars=overlap_result.replace_suffix_chars,
            drop_reason="dedup_wiped_all",
        )
    return NormalizedInlineCompletion(
        completion=completion,
        prefix_overlap_chars=overlap_result.prefix_overlap_chars,
        suffix_overlap_chars=overlap_result.suffix_overlap_chars,
        replace_suffix_chars=overlap_result.replace_suffix_chars,
    )
