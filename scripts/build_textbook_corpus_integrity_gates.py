"""CLI entrypoint for textbook corpus integrity gates.

Purpose:
    Provide a stable module/CLI path for integrity validation and pristine promotion
    while delegating implementation to split modules for maintainability.

Relationships:
    - Re-exports runtime APIs from `scripts.textbook_corpus_integrity_runtime`.
    - Keeps `python -m scripts.build_textbook_corpus_integrity_gates` as canonical entrypoint.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.textbook_corpus_integrity_runtime import (
    ValidationBundle,
    build_pristine,
    build_pristine_copy,
    main,
    run_integrity_gates,
    run_integrity_validation,
    validate_integrity_gates,
    write_validation_artifacts,
)

__all__ = [
    "ValidationBundle",
    "validate_integrity_gates",
    "run_integrity_gates",
    "run_integrity_validation",
    "write_validation_artifacts",
    "build_pristine",
    "build_pristine_copy",
    "main",
]


if __name__ == "__main__":
    main()
