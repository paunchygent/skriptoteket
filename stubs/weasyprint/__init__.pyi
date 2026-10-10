from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import IO, overload

from weasyprint.text.fonts import FontConfiguration as FontConfiguration
from weasyprint.urls import URLFetcherResponse

DEFAULT_OPTIONS: dict[str, bool | None]

class CSS:
    def __init__(
        self,
        string: str | None = None,
        base_url: str | Path | None = None,
        url_fetcher: Callable[[str], URLFetcherResponse] | None = None,
        font_config: FontConfiguration | None = None,
    ) -> None: ...

class HTML:
    def __init__(
        self,
        string: str | None = None,
        base_url: str | Path | None = None,
        url_fetcher: Callable[[str], URLFetcherResponse] | None = None,
    ) -> None: ...
    @overload
    def write_pdf(
        self,
        target: None = None,
        *,
        stylesheets: Sequence[CSS] | None = None,
        font_config: FontConfiguration | None = None,
        **options: object,
    ) -> bytes: ...
    @overload
    def write_pdf(
        self,
        target: str | Path | IO[bytes],
        *,
        stylesheets: Sequence[CSS] | None = None,
        font_config: FontConfiguration | None = None,
        **options: object,
    ) -> None: ...
