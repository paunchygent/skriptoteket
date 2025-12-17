from __future__ import annotations

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.web.error_mapping import error_to_status
from skriptoteket.web.templating import templates
from skriptoteket.web.ui_text import ui_error_message

logger = structlog.get_logger(__name__)


async def error_handler_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except DomainError as exc:
        correlation_id = getattr(request.state, "correlation_id", None)
        status_code = error_to_status(exc.code)
        accept = request.headers.get("accept", "")
        wants_json = request.url.path.startswith("/api/") or "application/json" in accept

        logger.warning(
            "Application error",
            error_code=exc.code.value,
            http_status=status_code,
            method=request.method,
            path=request.url.path,
            correlation_id=str(correlation_id) if correlation_id else None,
        )

        if wants_json:
            return JSONResponse(
                status_code=status_code,
                content={
                    "error": {
                        "code": exc.code.value,
                        "message": exc.message,
                        "details": exc.details,
                    },
                    "correlation_id": str(correlation_id) if correlation_id else None,
                },
            )

        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "request": request,
                "error_code": exc.code.value,
                "message": ui_error_message(exc),
            },
            status_code=status_code,
        )
    except Exception:
        correlation_id = getattr(request.state, "correlation_id", None)
        logger.exception(
            "Unhandled exception",
            method=request.method,
            path=request.url.path,
            correlation_id=str(correlation_id) if correlation_id else None,
        )
        accept = request.headers.get("accept", "")
        wants_json = request.url.path.startswith("/api/") or "application/json" in accept

        if wants_json:
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": ErrorCode.INTERNAL_ERROR.value,
                        "message": "Internal server error",
                        "details": {},
                    },
                    "correlation_id": str(correlation_id) if correlation_id else None,
                },
            )

        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "request": request,
                "error_code": ErrorCode.INTERNAL_ERROR.value,
                "message": "Internt serverfel.",
            },
            status_code=500,
        )
