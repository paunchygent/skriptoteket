"""HTTP request metadata helpers for Skriptoteket.

Purpose:
    Extract correlation, user-agent, and client IP metadata at the web
    boundary. The client IP is the direct peer uvicorn already resolved through
    its single trusted-proxy chain (`--proxy-headers` with `FORWARDED_ALLOW_IPS`);
    forwarding headers are never read here because uvicorn has consumed them.

Relationships:
    - Used by auth routes when recording login events.
    - Used by public routes as the rate-limiter caller identity.
"""

from __future__ import annotations

import ipaddress
from uuid import UUID

from fastapi import Request


def _parse_ip_address(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None
    normalized = raw_value.strip()
    if not normalized:
        return None
    try:
        return ipaddress.ip_address(normalized).compressed
    except ValueError:
        return None


def get_client_ip(request: Request) -> str | None:
    """Return the client IP for audit logging and rate limiting.

    Uvicorn's `ProxyHeadersMiddleware` already resolved `request.client` from
    the verified proxy chain, so forwarding headers must not be consulted here:
    the leftmost `X-Forwarded-For` entry is caller-controlled.
    """

    direct_client_host = request.client.host if request.client else None
    return _parse_ip_address(direct_client_host) or direct_client_host


def get_user_agent(request: Request) -> str | None:
    user_agent = request.headers.get("user-agent")
    return user_agent.strip() if user_agent else None


def get_correlation_id(request: Request) -> UUID | None:
    correlation_id = getattr(request.state, "correlation_id", None)
    return correlation_id if isinstance(correlation_id, UUID) else None
