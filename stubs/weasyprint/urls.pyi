from __future__ import annotations

from email.message import EmailMessage
from typing import IO

class FatalURLFetchingError(BaseException): ...

class URLFetcherResponse:
    def __init__(
        self,
        url: str,
        body: str | bytes | IO[bytes] | None = None,
        headers: dict[str, str] | EmailMessage | None = None,
        status: int = 200,
        **kwargs: object,
    ) -> None: ...
