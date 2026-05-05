"""Unit tests for request metadata extraction helpers.

Purpose:
    Verify login-event audit metadata only trusts forwarding headers when the
    direct peer is an explicitly trusted proxy.

Relationships:
    - Exercises `skriptoteket.web.request_metadata`.
    - Covers the security hardening lane for spoof-resistant client IP logging.
"""

from __future__ import annotations

from starlette.requests import Request

from skriptoteket.config import Settings
from skriptoteket.web.request_metadata import get_client_ip


def _make_request(
    *,
    client_host: str,
    headers: dict[str, str] | None = None,
) -> Request:
    encoded_headers = []
    for key, value in (headers or {}).items():
        encoded_headers.append((key.lower().encode("latin-1"), value.encode("latin-1")))
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/profile/app-continuation",
        "headers": encoded_headers,
        "client": (client_host, 12345),
    }
    return Request(scope)


def test_get_client_ip_ignores_forwarded_headers_when_proxy_trust_is_disabled() -> None:
    request = _make_request(
        client_host="172.18.0.10",
        headers={
            "x-forwarded-for": "203.0.113.77",
            "x-real-ip": "203.0.113.78",
        },
    )
    settings = Settings.model_construct(
        TRUST_PROXY_HEADERS=False,
        TRUSTED_PROXY_CIDRS="172.16.0.0/12",
    )

    assert get_client_ip(request, settings=settings) == "172.18.0.10"


def test_get_client_ip_uses_first_forwarded_hop_from_trusted_proxy() -> None:
    request = _make_request(
        client_host="172.18.0.10",
        headers={"x-forwarded-for": "203.0.113.77, 172.18.0.10"},
    )
    settings = Settings.model_construct(
        TRUST_PROXY_HEADERS=True,
        TRUSTED_PROXY_CIDRS="172.16.0.0/12",
    )

    assert get_client_ip(request, settings=settings) == "203.0.113.77"


def test_get_client_ip_falls_back_to_x_real_ip_for_trusted_proxy() -> None:
    request = _make_request(
        client_host="172.18.0.10",
        headers={"x-real-ip": "198.51.100.24"},
    )
    settings = Settings.model_construct(
        TRUST_PROXY_HEADERS=True,
        TRUSTED_PROXY_CIDRS="172.16.0.0/12",
    )

    assert get_client_ip(request, settings=settings) == "198.51.100.24"


def test_get_client_ip_rejects_malformed_forwarded_values() -> None:
    request = _make_request(
        client_host="172.18.0.10",
        headers={"x-forwarded-for": "not-an-ip"},
    )
    settings = Settings.model_construct(
        TRUST_PROXY_HEADERS=True,
        TRUSTED_PROXY_CIDRS="172.16.0.0/12",
    )

    assert get_client_ip(request, settings=settings) == "172.18.0.10"


def test_get_client_ip_ignores_spoofed_forwarding_from_untrusted_direct_peer() -> None:
    request = _make_request(
        client_host="172.18.0.10",
        headers={
            "x-forwarded-for": "203.0.113.77, 172.18.0.10",
            "x-real-ip": "198.51.100.24",
        },
    )
    settings = Settings.model_construct(
        ENVIRONMENT="production",
        TRUST_PROXY_HEADERS=True,
        TRUSTED_PROXY_CIDRS="127.0.0.1/32,::1/128",
    )

    assert get_client_ip(request, settings=settings) == "172.18.0.10"
