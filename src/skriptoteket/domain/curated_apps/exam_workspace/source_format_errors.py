"""The error every source-formatting module raises when no source-backed rendering exists."""

from __future__ import annotations


class FormattingTransferError(ValueError):
    """No source-backed rendering can preserve the model's response structure."""
