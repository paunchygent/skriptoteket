from __future__ import annotations

import logging
from typing import Literal

import structlog
from structlog.types import EventDict, WrappedLogger

LogFormat = Literal["json", "console"]


def _add_service_context(*, service_name: str, environment: str):
    def processor(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
        event_dict["service.name"] = service_name
        event_dict["deployment.environment"] = environment
        return event_dict

    return processor


def _add_trace_context(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    try:
        from opentelemetry import trace  # type: ignore[import-not-found]

        span = trace.get_current_span()
        if span and span.is_recording():
            ctx = span.get_span_context()
            if ctx.is_valid:
                event_dict["trace_id"] = format(ctx.trace_id, "032x")
                event_dict["span_id"] = format(ctx.span_id, "016x")
    except Exception:  # noqa: BLE001 - optional dependency; never break logging
        pass
    return event_dict


def configure_logging(
    *,
    service_name: str,
    environment: str,
    log_level: str = "INFO",
    log_format: LogFormat = "json",
) -> None:
    """Configure structured logging compatible with HuleEdu observability.

    Fields follow `docs/reference/reports/ref-external-observability-integration.md`.
    """
    level_name = log_level.upper().strip() or "INFO"
    level = getattr(logging, level_name, logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        _add_service_context(service_name=service_name, environment=environment),
        _add_trace_context,
        structlog.processors.TimeStamper(fmt="iso", key="timestamp"),
        structlog.processors.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ],
        ),
        structlog.processors.format_exc_info,
    ]

    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if log_format == "json"
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    handler = logging.StreamHandler()
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=renderer,
            foreign_pre_chain=shared_processors,
        )
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    for name in (
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "fastapi",
        "alembic",
        "sqlalchemy.engine",
    ):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
