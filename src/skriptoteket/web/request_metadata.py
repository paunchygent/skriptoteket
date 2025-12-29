from __future__ import annotations

from uuid import UUID

from fastapi import Request


def get_client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip() or None

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip() or None

    if request.client:
        return request.client.host
    return None


def get_user_agent(request: Request) -> str | None:
    user_agent = request.headers.get("user-agent")
    return user_agent.strip() if user_agent else None


def get_correlation_id(request: Request) -> UUID | None:
    correlation_id = getattr(request.state, "correlation_id", None)
    return correlation_id if isinstance(correlation_id, UUID) else None
