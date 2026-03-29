"""HTTP request metadata helpers for Skriptoteket.

Purpose:
    Extract correlation, user-agent, and client IP metadata at the web
    boundary without trusting caller-controlled forwarding headers by default.

Relationships:
    - Used by auth routes when recording login events.
    - Applies the proxy-trust policy defined in `skriptoteket.config.Settings`.
"""

from __future__ import annotations

import ipaddress
from uuid import UUID

from fastapi import Request

from skriptoteket.config import Settings


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


def _is_trusted_proxy(request_host: str | None, settings: Settings) -> bool:
    proxy_ip = _parse_ip_address(request_host)
    if proxy_ip is None or not settings.TRUST_PROXY_HEADERS:
        return False

    proxy_address = ipaddress.ip_address(proxy_ip)
    for cidr in settings.trusted_proxy_cidrs:
        try:
            if proxy_address in ipaddress.ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue
    return False


def get_client_ip(request: Request, *, settings: Settings) -> str | None:
    """Return the client IP for audit logging.

    Forwarded headers are only considered when the direct peer is a trusted
    proxy and forwarded-header trust is explicitly enabled.
    """

    direct_client_host = request.client.host if request.client else None
    if _is_trusted_proxy(direct_client_host, settings):
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            first_hop = forwarded_for.split(",")[0]
            parsed_forwarded_for = _parse_ip_address(first_hop)
            if parsed_forwarded_for is not None:
                return parsed_forwarded_for

        parsed_real_ip = _parse_ip_address(request.headers.get("x-real-ip"))
        if parsed_real_ip is not None:
            return parsed_real_ip

    return _parse_ip_address(direct_client_host) or direct_client_host


def get_user_agent(request: Request) -> str | None:
    user_agent = request.headers.get("user-agent")
    return user_agent.strip() if user_agent else None


def get_correlation_id(request: Request) -> UUID | None:
    correlation_id = getattr(request.state, "correlation_id", None)
    return correlation_id if isinstance(correlation_id, UUID) else None
