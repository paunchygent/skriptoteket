from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars


class CorrelationMiddleware(BaseHTTPMiddleware):
    header_name: str = "X-Correlation-ID"

    async def dispatch(self, request: Request, call_next):
        raw_id = request.headers.get(self.header_name)
        if raw_id:
            try:
                correlation_id = UUID(raw_id)
            except ValueError:
                correlation_id = uuid4()
        else:
            correlation_id = uuid4()

        clear_contextvars()
        bind_contextvars(correlation_id=str(correlation_id))
        request.state.correlation_id = correlation_id

        try:
            response = await call_next(request)
            response.headers[self.header_name] = str(correlation_id)
            return response
        finally:
            clear_contextvars()
