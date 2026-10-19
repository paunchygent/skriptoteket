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


def _parse_forwarded_hosts(raw_value: str | None) -> tuple[str, ...]:
    if raw_value is None:
        return ()
    hosts: list[str] = []
    for entry in raw_value.split(","):
        parsed = _parse_ip_address(entry)
        if parsed is not None:
            hosts.append(parsed)
    return tuple(hosts)


def forwarded_chain_untrusted(request: Request) -> bool:
    """Return True when an X-Forwarded-For chain exists that uvicorn did not resolve.

    Uvicorn's `ProxyHeadersMiddleware` rewrites `request.client` to the
    right-most untrusted `X-Forwarded-For` entry when the direct peer is
    trusted. When the peer is NOT trusted, `request.client` stays the proxy
    address, which never appears in `X-Forwarded-For` (nginx appends the peer
    it sees, i.e. the client, not itself). A present chain that does not
    contain the resolved client therefore means the proxy hop is untrusted and
    every guest shares one limiter key. Malformed chain entries are ignored; a
    blank header carries no chain.
    """

    raw_chain = request.headers.get("x-forwarded-for")
    if raw_chain is None or not raw_chain.strip():
        return False
    direct_client_host = request.client.host if request.client else None
    normalized_client = _parse_ip_address(direct_client_host)
    return normalized_client not in _parse_forwarded_hosts(raw_chain)


def get_user_agent(request: Request) -> str | None:
    user_agent = request.headers.get("user-agent")
    return user_agent.strip() if user_agent else None


def get_correlation_id(request: Request) -> UUID | None:
    correlation_id = getattr(request.state, "correlation_id", None)
    return correlation_id if isinstance(correlation_id, UUID) else None
