"""Narrowing helpers for JSON read back from Playwright pages and responses.

Purpose:
    Turn parsed JSON (`JsonValue`) into the typed leaves a proof script reads,
    raising `TypeError` when the producer sends another type.
Relationships:
    - Used by the `playwright_pr_*` proof scripts that read `page.evaluate`,
      request bodies and API responses by fixed keys.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import JsonValue


def json_object(value: JsonValue, *, label: str) -> dict[str, JsonValue]:
    """Return the value as a JSON object or raise `TypeError`."""

    if not isinstance(value, dict):
        raise TypeError(f"Expected {label} to be a JSON object, got {type(value).__name__}.")
    return value


def json_array(value: JsonValue, *, label: str) -> list[JsonValue]:
    """Return the value as a JSON array or raise `TypeError`."""

    if not isinstance(value, list):
        raise TypeError(f"Expected {label} to be a JSON array, got {type(value).__name__}.")
    return value


def json_str(obj: Mapping[str, JsonValue], key: str) -> str:
    """Return `obj[key]` as a string or raise `KeyError`/`TypeError`."""

    value = obj[key]
    if not isinstance(value, str):
        raise TypeError(f"Expected {key} to be a string, got {type(value).__name__}.")
    return value


def json_int(obj: Mapping[str, JsonValue], key: str) -> int:
    """Return `obj[key]` as an integer or raise `KeyError`/`TypeError`."""

    value = obj[key]
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"Expected {key} to be an integer, got {type(value).__name__}.")
    return value
