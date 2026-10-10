from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

def convert_file(
    source_file: str | Path,
    to: str,
    format: str | None = None,
    extra_args: Iterable[str] = (),
    outputfile: str | Path | None = None,
) -> str: ...
def get_pandoc_version() -> str: ...
