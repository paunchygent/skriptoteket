"""Shared models and constants for textbook corpus integrity gates.

Purpose:
    Centralize typed gate result models and parsing constants used by integrity validation.

Relationships:
    - Imported by `scripts.textbook_corpus_integrity_gates_core`.
    - Imported by `scripts.textbook_corpus_integrity_runtime`.
    - Consumed by the CLI entrypoint `scripts.build_textbook_corpus_integrity_gates`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_OUTPUT_DIR = Path(".artifacts/textbook_corpus/integrity")
PAGE_ANCHOR_PATTERN = re.compile(r"\[\[page:(\d+)\]\]")
# Chapter exercise identifiers in corpus headings/lists, e.g. "2.19 ...".
# We intentionally do not parse scalar prefixes like "2." or "22,5 ..." because
# those frequently appear in sub-bullets and numeric prose (false positives).
LIST_NUMBER_PATTERN = re.compile(r"^\s*(?:[-*]\s*)?(\d{1,3})\.(\d{1,3})(?!\d)")
SECTION_NUMBER_PATTERN = re.compile(r"^\s*##\s+(\d+)\b")
RESOLVED_STATUSES = {"resolved", "done", "closed", "fixed", "approved"}
CRITICAL_SEVERITIES = {"critical", "high"}


@dataclass(frozen=True, slots=True)
class GateFinding:
    """Represents one deterministic validation finding."""

    code: str
    severity: str
    line_no: int | None
    message: str


@dataclass(frozen=True, slots=True)
class GateResult:
    """Represents one gate outcome with metrics and findings."""

    gate: str
    passed: bool
    critical_count: int
    warning_count: int
    metrics: dict[str, int]
    findings: list[GateFinding]
