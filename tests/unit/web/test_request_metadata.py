"""Unit tests for request metadata extraction helpers.

Purpose:
    Verify the client IP is the direct peer uvicorn already resolved and that
    caller-controlled forwarding headers can never change it.

Relationships:
    - Exercises `skriptoteket.web.request_metadata`.
    - Covers the proxy-identity hardening lane for spoof-resistant client IP logging.
"""

from __future__ import annotations

from starlette.requests import Request

from skriptoteket.web.request_metadata import forwarded_chain_untrusted, get_client_ip


def _make_request(
    *,
    client_host: str | None,
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
        "client": (client_host, 12345) if client_host is not None else None,
    }
    return Request(scope)


def test_get_client_ip_returns_direct_peer() -> None:
    request = _make_request(client_host="172.18.0.10")

    assert get_client_ip(request) == "172.18.0.10"


def test_get_client_ip_ignores_forged_forwarded_headers() -> None:
    request = _make_request(
        client_host="172.18.0.10",
        headers={
            "x-forwarded-for": "203.0.113.77, 198.51.100.24",
            "x-real-ip": "198.51.100.24",
        },
    )

    assert get_client_ip(request) == "172.18.0.10"


def test_get_client_ip_ignores_spoofed_forwarding_from_untrusted_direct_peer() -> None:
    request = _make_request(
        client_host="198.51.100.7",
        headers={"x-forwarded-for": "6.6.6.6, 203.0.113.9"},
    )

    assert get_client_ip(request) == "198.51.100.7"


def test_get_client_ip_normalizes_ipv6_direct_peer() -> None:
    request = _make_request(client_host="::ffff:127.0.0.1")

    assert get_client_ip(request) == "::ffff:127.0.0.1"


def test_get_client_ip_returns_none_without_direct_peer() -> None:
    request = _make_request(client_host=None)

    assert get_client_ip(request) is None


def test_forwarded_chain_untrusted_is_false_without_forwarded_header() -> None:
    request = _make_request(client_host="172.18.0.5")

    assert forwarded_chain_untrusted(request) is False


def test_forwarded_chain_untrusted_is_false_when_client_is_among_chain_hosts() -> None:
    request = _make_request(
        client_host="203.0.113.9",
        headers={"x-forwarded-for": "6.6.6.6, 203.0.113.9"},
    )

    assert forwarded_chain_untrusted(request) is False


def test_forwarded_chain_untrusted_is_true_when_client_is_absent_from_chain() -> None:
    request = _make_request(
        client_host="172.18.0.5",
        headers={"x-forwarded-for": "6.6.6.6, 203.0.113.9"},
    )

    assert forwarded_chain_untrusted(request) is True


def test_forwarded_chain_untrusted_ignores_malformed_chain_entries() -> None:
    request = _make_request(
        client_host="203.0.113.9",
        headers={"x-forwarded-for": "not-an-address, 203.0.113.9"},
    )

    assert forwarded_chain_untrusted(request) is False
