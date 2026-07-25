"""Shared types and frontmatter primitives for docs validation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

type YamlScalar = str | int | float | bool | date | None
type YamlValue = YamlScalar | list[YamlValue] | dict[str, YamlValue]
type YamlMapping = dict[str, YamlValue]

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass(frozen=True)
class Violation:
    """One path-scoped docs-contract violation."""

    path: str
    message: str


def normalize_path(path: Path) -> str:
    """Return a platform-independent repository path."""
    return str(path).replace("\\", "/")


def string_list(value: YamlValue) -> list[str] | None:
    """Return a typed string list, an empty optional list, or invalidity."""
    if value is None:
        return []
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return [item for item in value if isinstance(item, str)]
    return None
