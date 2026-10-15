"""Pure destination policy and credential-safe origins for Sir Convert proof lanes."""

from __future__ import annotations

from urllib.parse import ParseResult, urlparse

REMOTE_PRODUCT_HOSTS = {"skriptoteket.hule.education"}
REMOTE_PROOF_SERVICE_PROFILES = {"remote-proof", "hemma-remote-proof"}
TUNNEL_HOSTS = {"127.0.0.1", "localhost", "host.docker.internal"}
PRIVATE_DESTINATIONS = {
    ("http", "127.0.0.1", 28085),
    ("http", "localhost", 28085),
    ("http", "host.docker.internal", 28085),
    ("http", "sir_convert_a_lot_prod", 8085),
}


def _parse_url(value: str | None, *, require_scheme: bool = True) -> ParseResult | None:
    if not value or not value.strip():
        return None
    stripped = value.strip()
    if not require_scheme and "://" not in stripped:
        stripped = f"//{stripped}"
    try:
        parsed = urlparse(stripped)
        if require_scheme and parsed.scheme not in {"http", "https"}:
            return None
        if not parsed.netloc or not parsed.hostname:
            return None
        # Accessing port validates numeric syntax and range. An empty explicit
        # port is also malformed, even though urllib reports it as None.
        parsed.port
        if parsed.netloc.rsplit("@", 1)[-1].endswith(":"):
            return None
    except ValueError:
        return None
    return parsed


def _destination(parsed: ParseResult) -> tuple[str, str, int | None]:
    return parsed.scheme, (parsed.hostname or "").lower().rstrip("."), parsed.port


def base_url_kind(value: str) -> str:
    """Identify the canonical HTTPS production product origin."""
    parsed = _parse_url(value)
    if parsed:
        scheme, host, port = _destination(parsed)
        if scheme == "https" and host in REMOTE_PRODUCT_HOSTS and port in (None, 443):
            return "remote"
    return "local"


def is_private_destination(raw_url: str | None) -> bool:
    """Require an exact private HTTP host and port, independent of profile metadata."""
    parsed = _parse_url(raw_url)
    return parsed is not None and _destination(parsed) in PRIVATE_DESTINATIONS


def is_private_tunnel_destination(raw_url: str | None) -> bool:
    """Identify the private port-28085 tunnel for mixed-lane classification."""
    parsed = _parse_url(raw_url)
    return (
        parsed is not None and _destination(parsed) in PRIVATE_DESTINATIONS and parsed.port == 28085
    )


def is_sanctioned_gateway_url(raw_url: str | None) -> bool:
    """Require the canonical HTTPS Gateway origin and Sir Convert path boundary."""
    parsed = _parse_url(raw_url)
    if parsed is None:
        return False
    scheme, host, port = _destination(parsed)
    return (
        scheme == "https"
        and host == "api.hule.education"
        and port in (None, 443)
        and parsed.path.startswith("/sir-convert/")
    )


def is_sanctioned_hemma_remote_proof_tunnel_url(
    raw_url: str | None, *, service_profile: str | None
) -> bool:
    """Require both the fenced HTTP tunnel tuple and its remote-proof profile."""
    profile = (service_profile or "").strip().lower()
    if profile not in REMOTE_PROOF_SERVICE_PROFILES:
        return False
    parsed = _parse_url(raw_url)
    if parsed is None:
        return False
    scheme, host, port = _destination(parsed)
    return scheme == "http" and host in TUNNEL_HOSTS and port in {28085, 38085}


def redacted_url_origin(value: str | None) -> str | None:
    """Retain an origin without credentials, paths, queries, or fragments."""
    if value is None or not value.strip():
        return None
    parsed = _parse_url(value, require_scheme=False)
    if parsed is None:
        return "<redacted-url>"
    host = (parsed.hostname or "").lower()
    host_part = f"[{host}]" if ":" in host else host
    host_port = f"{host_part}:{parsed.port}" if parsed.port is not None else host_part
    if parsed.scheme and "://" in value:
        return f"{parsed.scheme.lower()}://{host_port}"
    return host_port
