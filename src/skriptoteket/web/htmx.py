from __future__ import annotations

from fastapi import Request


def is_hx_request(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"

