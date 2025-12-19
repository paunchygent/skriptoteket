from __future__ import annotations

import json

from pydantic import JsonValue


def _canonical_json_bytes(value: object) -> int:
    dumped = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=False)
    return len(dumped.encode("utf-8"))


def _utf8_truncate(value: str, *, max_bytes: int) -> tuple[str, bool]:
    if max_bytes <= 0:
        return ("", bool(value))
    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return (value, False)
    return (encoded[:max_bytes].decode("utf-8", errors="ignore"), True)


def _canonicalize_json_value(
    value: JsonValue,
    *,
    max_depth: int,
    max_keys: int,
    max_array_len: int,
    depth: int = 0,
) -> tuple[JsonValue, bool]:
    if max_depth >= 0 and depth >= max_depth:
        if isinstance(value, dict):
            return ({}, True)
        if isinstance(value, list):
            return ([], True)
        return (value, False)

    if isinstance(value, dict):
        truncated = False
        dict_items: list[tuple[str, JsonValue]] = []
        for key in sorted(value.keys(), key=str):
            if max_keys >= 0 and len(dict_items) >= max_keys:
                truncated = True
                break
            child, child_truncated = _canonicalize_json_value(
                value[key],
                max_depth=max_depth,
                max_keys=max_keys,
                max_array_len=max_array_len,
                depth=depth + 1,
            )
            truncated = truncated or child_truncated
            dict_items.append((str(key), child))
        return ({k: v for k, v in dict_items}, truncated)

    if isinstance(value, list):
        truncated = False
        list_items: list[JsonValue] = []
        limit = len(value) if max_array_len < 0 else min(len(value), max_array_len)
        if limit < len(value):
            truncated = True
        for item in value[:limit]:
            child, child_truncated = _canonicalize_json_value(
                item,
                max_depth=max_depth,
                max_keys=max_keys,
                max_array_len=max_array_len,
                depth=depth + 1,
            )
            truncated = truncated or child_truncated
            list_items.append(child)
        return (list_items, truncated)

    return (value, False)


def _shrink_json_value_to_max_bytes(
    value: JsonValue, *, max_bytes: int
) -> tuple[JsonValue, bool, bool]:
    """Returns (value, was_truncated, fits_budget)."""
    if max_bytes < 2:
        return (value, False, False)

    current = value
    if _canonical_json_bytes(current) <= max_bytes:
        return (current, False, True)

    if isinstance(current, str):
        truncated, did_truncate = _utf8_truncate(current, max_bytes=max_bytes)
        return (truncated, did_truncate, _canonical_json_bytes(truncated) <= max_bytes)

    if isinstance(current, dict):
        dict_items = list(current.items())
        low = 0
        high = len(dict_items)
        best = 0
        while low <= high:
            mid = (low + high) // 2
            candidate_dict = {k: v for k, v in dict_items[:mid]}
            if _canonical_json_bytes(candidate_dict) <= max_bytes:
                best = mid
                low = mid + 1
            else:
                high = mid - 1
        candidate_dict = {k: v for k, v in dict_items[:best]}
        return (
            candidate_dict,
            best < len(dict_items),
            _canonical_json_bytes(candidate_dict) <= max_bytes,
        )

    if isinstance(current, list):
        low = 0
        high = len(current)
        best = 0
        while low <= high:
            mid = (low + high) // 2
            candidate_list = current[:mid]
            if _canonical_json_bytes(candidate_list) <= max_bytes:
                best = mid
                low = mid + 1
            else:
                high = mid - 1
        candidate_list = current[:best]
        return (
            candidate_list,
            best < len(current),
            _canonical_json_bytes(candidate_list) <= max_bytes,
        )

    return (current, False, _canonical_json_bytes(current) <= max_bytes)
