from __future__ import annotations

import json
from typing import Literal
from urllib.parse import quote, unquote

from fastapi import Request
from fastapi.responses import Response

ToastType = Literal["success", "error"]

TOAST_COOKIE_NAME = "skriptoteket_toast"


def set_toast_cookie(*, response: Response, message: str, toast_type: ToastType = "success") -> None:
    payload = json.dumps(
        {"m": message, "t": toast_type},
        separators=(",", ":"),
        ensure_ascii=False,
    )
    response.set_cookie(
        key=TOAST_COOKIE_NAME,
        value=quote(payload),
        max_age=30,
        path="/",
        httponly=True,
        samesite="lax",
    )


def read_toast_cookie(request: Request) -> tuple[str, ToastType] | None:
    raw = request.cookies.get(TOAST_COOKIE_NAME)
    if not raw:
        return None

    try:
        decoded = json.loads(unquote(raw))
    except (json.JSONDecodeError, ValueError):
        return None

    message = str(decoded.get("m", "")).strip()
    if not message:
        return None

    toast_type: ToastType
    candidate_type = str(decoded.get("t", "success"))
    if candidate_type == "error":
        toast_type = "error"
    else:
        toast_type = "success"

    return message, toast_type

