from __future__ import annotations

from pydantic import JsonValue

from ._json_canonical import _canonical_json_bytes


def _enforce_state_budget(
    state: dict[str, JsonValue],
    *,
    max_bytes: int,
) -> tuple[dict[str, JsonValue], int]:
    if max_bytes < 2:
        return ({}, len(state) if state else 0)

    items = [(key, state[key]) for key in sorted(state.keys())]
    if _canonical_json_bytes({k: v for k, v in items}) <= max_bytes:
        return ({k: v for k, v in items}, 0)

    low = 0
    high = len(items)
    best = 0
    while low <= high:
        mid = (low + high) // 2
        candidate = {k: v for k, v in items[:mid]}
        if _canonical_json_bytes(candidate) <= max_bytes:
            best = mid
            low = mid + 1
        else:
            high = mid - 1

    candidate = {k: v for k, v in items[:best]}
    dropped = len(items) - best
    return (candidate, dropped)
