"""Destination admission rejects URL marker spoofing before local proof submission."""

from __future__ import annotations

import pytest

from scripts._sir_convert_trust_lane_preflight import (
    SirConvertTrustLanePreflightError,
    TrustLanePreflightInput,
    run_trust_lane_preflight,
)

PRIVATE_TUNNEL = "http://host.docker.internal:28085"
GATEWAY = "https://api.hule.education/sir-convert/v2/convert"
FINGERPRINT = "46aefc0edc2f71267e2df783ca27f4df2b0da269cc7e84b43cbe2de6ac7c1992"


def _input(**overrides: object) -> TrustLanePreflightInput:
    values = {
        "base_url": "http://127.0.0.1:5173",
        "gateway_backend_url": PRIVATE_TUNNEL,
        "producer_backend_url": PRIVATE_TUNNEL,
        "gateway_signer_fingerprint": FINGERPRINT,
        "sir_convert_trusted_fingerprint": FINGERPRINT,
        "sir_convert_service_profile": "prod",
        "allow_mixed_sir_convert_tunnel": True,
        "proof_lane": "auto",
    }
    values.update(overrides)
    return TrustLanePreflightInput(**values)


@pytest.mark.parametrize(
    ("destination", "profile", "lane"),
    [
        ("https://convert.hule.education", "prod", "auto"),
        (
            "https://convert.hule.education/?backend=sir_convert_a_lot_prod",
            None,
            "mixed-tunnel-debug",
        ),
    ],
)
def test_review_gateway_bypasses_fail_closed(
    destination: str, profile: str | None, lane: str
) -> None:
    with pytest.raises(SirConvertTrustLanePreflightError) as exc_info:
        run_trust_lane_preflight(
            _input(
                gateway_backend_url=destination,
                sir_convert_service_profile=profile,
                proof_lane=lane,
            )
        )

    error = exc_info.value
    assert error.blocker_kind == "sir_convert_trust_lane_unresolved"
    assert error.metadata["base_url_kind"] == "local"
    assert error.metadata["remote_compute"] is False
    assert error.metadata["job_submit_allowed"] is False
    assert error.metadata["gateway_backend_url"] == "https://convert.hule.education"


def test_review_producer_query_bypass_fails_closed() -> None:
    with pytest.raises(SirConvertTrustLanePreflightError) as exc_info:
        run_trust_lane_preflight(
            _input(
                gateway_backend_url=GATEWAY,
                producer_backend_url=(
                    "https://convert.hule.education/?backend=sir_convert_a_lot_prod"
                ),
                sir_convert_service_profile=None,
                proof_lane="remote-proof-gateway",
                allow_mixed_sir_convert_tunnel=False,
            )
        )

    error = exc_info.value
    assert error.blocker_kind == "sir_convert_producer_lane_unresolved"
    assert error.metadata["remote_compute"] is True
    assert error.metadata["job_submit_allowed"] is False
    assert error.metadata["gateway_backend_url"] == "https://api.hule.education"
    assert error.metadata["producer_backend_url"] == "https://convert.hule.education"


SPOOFED_DESTINATIONS = [
    "https://sir_convert_a_lot_prod:secret@public.example.test/",
    "https://public.example.test/sir_convert_a_lot_prod/v2",
    "https://convert.hule.education/?backend=127.0.0.1:28085&token=secret",
    "https://public.example.test/#host.docker.internal:28085",
    "http://sir_convert_a_lot_prod.public.example.test:8085",
    "http://public-sir_convert_a_lot_prod:8085",
    "http://host.docker.internal.public.example.test:28085",
]


@pytest.mark.parametrize("destination", SPOOFED_DESTINATIONS)
@pytest.mark.parametrize(("profile", "lane"), [("prod", "auto"), (None, "mixed-tunnel-debug")])
def test_profile_and_debug_opt_in_cannot_admit_spoofed_gateway(
    destination: str, profile: str | None, lane: str
) -> None:
    with pytest.raises(SirConvertTrustLanePreflightError) as exc_info:
        run_trust_lane_preflight(
            _input(
                gateway_backend_url=destination,
                sir_convert_service_profile=profile,
                proof_lane=lane,
            )
        )

    error = exc_info.value
    assert error.blocker_kind == "sir_convert_trust_lane_unresolved"
    assert error.metadata["remote_compute"] is False
    assert error.metadata["job_submit_allowed"] is False
    assert "secret" not in str(error.metadata)
    assert "backend=" not in str(error.metadata)


@pytest.mark.parametrize("destination", SPOOFED_DESTINATIONS)
@pytest.mark.parametrize(("profile", "lane"), [("prod", "auto"), (None, "mixed-tunnel-debug")])
def test_profile_and_debug_opt_in_cannot_admit_spoofed_producer(
    destination: str, profile: str | None, lane: str
) -> None:
    with pytest.raises(SirConvertTrustLanePreflightError) as exc_info:
        run_trust_lane_preflight(
            _input(
                producer_backend_url=destination,
                sir_convert_service_profile=profile,
                proof_lane=lane,
            )
        )

    error = exc_info.value
    assert error.blocker_kind == "sir_convert_producer_lane_unresolved"
    assert error.metadata["remote_compute"] is True
    assert error.metadata["job_submit_allowed"] is False
    assert "secret" not in str(error.metadata)
    assert "backend=" not in str(error.metadata)


@pytest.mark.parametrize(
    "destination",
    [
        "https://127.0.0.1:28085",
        "ftp://host.docker.internal:28085",
        "http://localhost:8085",
        "http://127.0.0.1:not-a-port",
        "http://host.docker.internal:99999",
        "https://sir_convert_a_lot_prod:8085",
        "ftp://sir_convert_a_lot_prod:8085",
        "http://sir_convert_a_lot_prod:28085",
        "http://sir_convert_a_lot_prod:not-a-port",
        "http://sir_convert_a_lot_prod:99999",
        "http://sir_convert_a_lot_prod",
    ],
)
@pytest.mark.parametrize("target", ["gateway_backend_url", "producer_backend_url"])
def test_private_routes_reject_wrong_scheme_or_wrong_or_malformed_port(
    destination: str, target: str
) -> None:
    with pytest.raises(SirConvertTrustLanePreflightError) as exc_info:
        run_trust_lane_preflight(_input(**{target: destination}))

    error = exc_info.value
    is_gateway = target == "gateway_backend_url"
    assert error.blocker_kind == (
        "sir_convert_trust_lane_unresolved"
        if is_gateway
        else "sir_convert_producer_lane_unresolved"
    )
    assert error.metadata["remote_compute"] is (not is_gateway)
    assert error.metadata["job_submit_allowed"] is False


@pytest.mark.parametrize(
    "destination",
    [
        "http://127.0.0.1:28085",
        "http://localhost:28085",
        "http://host.docker.internal:28085",
        "http://sir_convert_a_lot_prod:8085",
    ],
)
@pytest.mark.parametrize(("lane", "profile"), [("auto", "prod"), ("mixed-tunnel-debug", None)])
def test_exact_private_routes_allow_matching_gateway_and_producer(
    destination: str, lane: str, profile: str | None
) -> None:
    result = run_trust_lane_preflight(
        _input(
            gateway_backend_url=destination,
            producer_backend_url=destination,
            proof_lane=lane,
            sir_convert_service_profile=profile,
        )
    )

    assert result.status == "passed"
    assert result.lane_kind == "mixed_tunnel_debug"
    assert result.metadata["remote_compute"] is True
    assert result.metadata["job_submit_allowed"] is True


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "host.docker.internal"])
@pytest.mark.parametrize("port", [28085, 38085])
def test_fenced_remote_proof_preserves_tunnel_hosts_and_ports(host: str, port: int) -> None:
    destination = f"http://{host}:{port}"
    result = run_trust_lane_preflight(
        _input(
            gateway_backend_url=destination,
            producer_backend_url=destination,
            sir_convert_service_profile="remote-proof",
            proof_lane="hemma-remote-proof",
            allow_mixed_sir_convert_tunnel=False,
        )
    )

    assert result.status == "passed"
    assert result.lane_kind == "hemma_remote_proof"
    assert result.metadata["remote_compute"] is True
    assert result.metadata["mixed_tunnel"] is False
    assert result.metadata["job_submit_allowed"] is True


@pytest.mark.parametrize(
    "destination",
    [
        "https://localhost:28085",
        "http://localhost:8085",
        "http://localhost:bad",
        "http://localhost:99999",
        "http://sir_convert_a_lot_prod:8085",
    ],
)
@pytest.mark.parametrize("target", ["gateway_backend_url", "producer_backend_url"])
def test_fenced_remote_proof_rejects_invalid_tunnel_destinations(
    destination: str, target: str
) -> None:
    with pytest.raises(SirConvertTrustLanePreflightError) as exc_info:
        run_trust_lane_preflight(
            _input(
                **{target: destination},
                sir_convert_service_profile="remote-proof",
                proof_lane="hemma-remote-proof",
                allow_mixed_sir_convert_tunnel=False,
            )
        )

    error = exc_info.value
    is_gateway = target == "gateway_backend_url"
    expected_kind = (
        "sir_convert_trust_lane_unresolved"
        if is_gateway
        else "sir_convert_producer_lane_unresolved"
    )
    assert error.blocker_kind == expected_kind
    assert error.metadata["remote_compute"] is (not is_gateway)
    assert error.metadata["job_submit_allowed"] is False


@pytest.mark.parametrize("port", ["", ":443"])
def test_gateway_allows_exact_https_origin_and_conversion_path(port: str) -> None:
    result = run_trust_lane_preflight(
        _input(
            gateway_backend_url=f"https://api.hule.education{port}/sir-convert/v2/convert",
            sir_convert_service_profile=None,
            proof_lane="remote-proof-gateway",
            allow_mixed_sir_convert_tunnel=False,
        )
    )

    assert result.status == "passed"
    assert result.lane_kind == "remote_proof_gateway"
    assert result.metadata["job_submit_allowed"] is True


@pytest.mark.parametrize(
    "destination",
    [
        "http://api.hule.education/sir-convert/v2/convert",
        "https://api.hule.education:8443/sir-convert/v2/convert",
        "https://api.hule.education:bad/sir-convert/v2/convert",
        "https://api.hule.education:99999/sir-convert/v2/convert",
        "https://api.hule.education/v2/convert",
        "https://api.hule.education.public.example.test/sir-convert/v2/convert",
    ],
)
def test_gateway_rejects_other_schemes_ports_paths_and_hostname_suffixes(destination: str) -> None:
    with pytest.raises(SirConvertTrustLanePreflightError) as exc_info:
        run_trust_lane_preflight(
            _input(
                gateway_backend_url=destination,
                sir_convert_service_profile=None,
                proof_lane="remote-proof-gateway",
            )
        )

    assert exc_info.value.blocker_kind == "sir_convert_trust_lane_unresolved"
    assert exc_info.value.metadata["remote_compute"] is False
    assert exc_info.value.metadata["job_submit_allowed"] is False
