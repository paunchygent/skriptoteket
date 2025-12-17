from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import Response

from skriptoteket.web.toasts import TOAST_COOKIE_NAME, read_toast_cookie


async def toast_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    toast = read_toast_cookie(request)
    request.state.toast_message = toast[0] if toast else None
    request.state.toast_type = toast[1] if toast else None

    response = await call_next(request)

    if toast:
        response.delete_cookie(key=TOAST_COOKIE_NAME, path="/")

    return response

