"""Guest limiter identity through the real uvicorn proxy chain (F1 regression).

These tests drive the real public exam workspace admission
(`admit_guest_request`) behind uvicorn's real `ProxyHeadersMiddleware` with an
explicit ASGI peer, so a forged `X-Forwarded-For` entry cannot choose the
rate-limit identity the way the old wildcard chain allowed.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from uuid import UUID

import pytest
import yaml
from starlette.requests import Request
from structlog.testing import capture_logs
from uvicorn._types import (
    ASGI3Application,
    ASGIReceiveCallable,
    ASGISendCallable,
    ASGISendEvent,
    HTTPRequestEvent,
    Scope,
)
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    CuratedAppPublicAccessProfile,
    CuratedAppPublicCapability,
    CuratedAppPublicRuntimeStatus,
    CuratedAppUiMode,
    curated_app_tool_id,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.public_request_limits import (
    AdmitPublicRequestHandlerProtocol,
    PublicRequestAdmission,
    PublicRequestBucket,
)
from skriptoteket.web.api.v1 import public_apps_exam_workspace_support as support
from skriptoteket.web.api.v1.public_apps_exam_workspace_support import admit_guest_request

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PROXY_PEER = "172.18.0.5"
_PROXY_CIDR = "172.18.0.0/16"
_REAL_CLIENT = "203.0.113.9"
_FORGED_CLIENT = "6.6.6.6"
_UNTRUSTED_PEER = "198.51.100.7"


def make_registry() -> CuratedAppRegistryProtocol:
    app = CuratedAppDefinition(
        app_id="documents.conversion_hub",
        tool_id=curated_app_tool_id(app_id="documents.conversion_hub"),
        app_version="app:test",
        ui_mode=CuratedAppUiMode.BESPOKE_REQUIRED,
        title="Konvertera dokument",
        summary="Konvertera DigiExam-prov.",
        min_role=Role.USER,
        public_access_profile=CuratedAppPublicAccessProfile.AUTHENTICATED_ONLY,
        public_capabilities=[
            CuratedAppPublicCapability(
                scope="exam_converter",
                profile=CuratedAppPublicAccessProfile.PUBLIC_BROWSER_RUNTIME,
                runtime_status=CuratedAppPublicRuntimeStatus.ACTIVE,
            )
        ],
        placements=[CuratedAppPlacement(profession_slug="larare", category_slug="ovrigt")],
    )

    class Registry:
        def list_all(self) -> list[CuratedAppDefinition]:
            return [app]

        def get_by_app_id(self, *, app_id: str) -> CuratedAppDefinition | None:
            return app if app_id == "documents.conversion_hub" else None

        def get_by_tool_id(self, *, tool_id: UUID) -> CuratedAppDefinition | None:
            return app if tool_id == app.tool_id else None

    return Registry()


class FakeAdmitHandler:
    """Database-limiter double that records the client IP it was given."""

    def __init__(self) -> None:
        self.calls: list[tuple[PublicRequestBucket, str]] = []

    async def admit(self, *, bucket: PublicRequestBucket, client_ip: str) -> PublicRequestAdmission:
        self.calls.append((bucket, client_ip))
        return PublicRequestAdmission(admitted=True, refusal=None)


def make_probe_app(
    *,
    admit: AdmitPublicRequestHandlerProtocol,
    registry: CuratedAppRegistryProtocol,
    statuses: list[int],
) -> ASGI3Application:
    async def probe(scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        request = Request(dict(scope))
        await admit_guest_request(
            request=request,
            registry=registry,
            admit_handler=admit,
            bucket=PublicRequestBucket.GUEST_EDIT,
        )
        statuses.append(200)
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": b'{"admitted":"true"}'})

    return probe


async def _admitted_ip(
    *,
    peer: str,
    headers: list[tuple[bytes, bytes]],
    trusted_hosts: list[str] | str,
) -> str:
    admit = FakeAdmitHandler()
    statuses: list[int] = []
    inner = make_probe_app(admit=admit, registry=make_registry(), statuses=statuses)
    middleware = ProxyHeadersMiddleware(inner, trusted_hosts=trusted_hosts)
    sent: list[ASGISendEvent] = []

    async def receive() -> HTTPRequestEvent:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: ASGISendEvent) -> None:
        sent.append(message)

    await middleware(
        {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/probe",
            "raw_path": b"/probe",
            "query_string": b"",
            "root_path": "",
            "headers": headers,
            "client": (peer, 5000),
            "server": ("testserver", 80),
        },
        receive,
        send,
    )

    assert statuses == [200]
    assert len(admit.calls) == 1
    assert admit.calls[0][0] is PublicRequestBucket.GUEST_EDIT
    return admit.calls[0][1]


def _xff(value: str) -> list[tuple[bytes, bytes]]:
    return [(b"x-forwarded-for", value.encode("latin-1"))]


async def test_trusted_proxy_peer_resolves_real_external_peer() -> None:
    """XFF 'forged, real' from the proxy peer admits as the real peer, not the forgery."""
    seen = await _admitted_ip(
        peer=_PROXY_PEER,
        headers=_xff(f"{_FORGED_CLIENT}, {_REAL_CLIENT}"),
        trusted_hosts=[_PROXY_CIDR],
    )

    assert seen == _REAL_CLIENT


async def test_rotating_forged_entry_keeps_one_caller_identity() -> None:
    """Rotating the caller-controlled leftmost XFF entry must not rotate the limiter identity."""
    first = await _admitted_ip(
        peer=_PROXY_PEER,
        headers=_xff(f"10.9.9.9, {_REAL_CLIENT}"),
        trusted_hosts=[_PROXY_CIDR],
    )
    second = await _admitted_ip(
        peer=_PROXY_PEER,
        headers=_xff(f"11.11.11.11, {_REAL_CLIENT}"),
        trusted_hosts=[_PROXY_CIDR],
    )

    assert first == _REAL_CLIENT
    assert second == _REAL_CLIENT


async def test_untrusted_direct_peer_with_any_xff_admits_as_that_peer() -> None:
    """A direct peer outside the proxy CIDR is its own identity however it forges XFF."""
    seen = await _admitted_ip(
        peer=_UNTRUSTED_PEER,
        headers=_xff(f"{_FORGED_CLIENT}, {_REAL_CLIENT}"),
        trusted_hosts=[_PROXY_CIDR],
    )

    assert seen == _UNTRUSTED_PEER


async def test_star_trust_hands_identity_to_leftmost_xff_entry() -> None:
    """Documents why deploy must never use '*': uvicorn then takes the caller-controlled edge."""
    seen = await _admitted_ip(
        peer=_PROXY_PEER,
        headers=_xff(f"{_FORGED_CLIENT}, {_REAL_CLIENT}"),
        trusted_hosts="*",
    )

    assert seen == _FORGED_CLIENT


def test_deploy_chain_has_no_wildcard_trust() -> None:
    """`serve` keeps `--proxy-headers` without `--forwarded-allow-ips='*'`; uvicorn
    then reads the trusted set from `FORWARDED_ALLOW_IPS` (default loopback)."""
    pyproject = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text())
    serve = pyproject["tool"]["pdm"]["scripts"]["serve"]

    assert "--proxy-headers" in serve
    assert "forwarded-allow-ips" not in serve
    assert "'*'" not in serve


def test_compose_prod_derives_forwarded_allow_ips_from_proxy_cidr() -> None:
    """`compose.prod.yaml` trusts exactly the nginx-proxy CIDR from the deploy env,
    failing closed to loopback when it is unset; the old app-level trust keys are gone."""
    compose = yaml.safe_load((_REPO_ROOT / "compose.prod.yaml").read_text())
    web_env = compose["services"]["web"]["environment"]

    if isinstance(web_env, dict):
        forwarded = web_env.get("FORWARDED_ALLOW_IPS")
        assert forwarded == "${TRUSTED_PROXY_CIDRS:-127.0.0.1}"
        assert "TRUST_PROXY_HEADERS" not in web_env
        assert "TRUSTED_PROXY_CIDRS" not in web_env
    else:
        lines = [str(line) for line in web_env]
        assert any(
            line.strip() == "FORWARDED_ALLOW_IPS=${TRUSTED_PROXY_CIDRS:-127.0.0.1}"
            for line in lines
        )
        assert not any("TRUST_PROXY_HEADERS" in line for line in lines)
        assert not any(line.strip().startswith("TRUSTED_PROXY_CIDRS") for line in lines)


def test_no_compose_file_reintroduces_app_level_proxy_trust() -> None:
    """No repo-root compose file may reintroduce the removed app-level trust keys."""
    for compose_file in sorted(_REPO_ROOT.glob("compose*.yaml")):
        content = compose_file.read_text()
        assert "TRUST_PROXY_HEADERS" not in content
        for line in content.splitlines():
            assert not line.strip().startswith("TRUSTED_PROXY_CIDRS:")


_PROXY_UNTRUSTED_EVENT = "public_guest_limiter_proxy_untrusted"


@pytest.fixture
def reset_proxy_warning():
    support._PROXY_UNTRUSTED_WARNING_EMITTED = False
    yield
    support._PROXY_UNTRUSTED_WARNING_EMITTED = False


async def test_trusted_proxy_peer_emits_no_proxy_warning(reset_proxy_warning) -> None:
    """A trusted proxy hop resolves the client from the chain, so nothing warns."""
    with capture_logs() as logs:
        seen = await _admitted_ip(
            peer=_PROXY_PEER,
            headers=_xff(f"{_FORGED_CLIENT}, {_REAL_CLIENT}"),
            trusted_hosts=[_PROXY_CIDR],
        )

    assert seen == _REAL_CLIENT
    assert [entry for entry in logs if entry.get("event") == _PROXY_UNTRUSTED_EVENT] == []


async def test_untrusted_proxy_peer_warns_exactly_once_across_requests(
    reset_proxy_warning,
) -> None:
    """An untrusted proxy hop keeps every guest on the proxy address: one warning."""
    with capture_logs() as logs:
        for _ in range(3):
            seen = await _admitted_ip(
                peer=_UNTRUSTED_PEER,
                headers=_xff(f"{_FORGED_CLIENT}, {_REAL_CLIENT}"),
                trusted_hosts=[_PROXY_CIDR],
            )

    assert seen == _UNTRUSTED_PEER
    warnings = [entry for entry in logs if entry.get("event") == _PROXY_UNTRUSTED_EVENT]
    assert len(warnings) == 1
    record = repr(warnings[0])
    assert _UNTRUSTED_PEER not in record
    assert _REAL_CLIENT not in record
    assert _FORGED_CLIENT not in record
    assert _PROXY_PEER not in record
