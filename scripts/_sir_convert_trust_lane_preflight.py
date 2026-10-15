"""Sir Convert hosted-runtime proof trust-lane preflight.

Domain purpose:
    Validate that Conversion Hub live proof uses a coherent HuleEdu Gateway to
    Sir Convert internal identity lane before media upload or producer job
    creation. The proof may use remote hosted model/runtime compute, but the
    signer and verifier trust profile must agree.

Relationships:
    Used by `scripts.audio_transcription_parity_live` for transcript proof
    hardening. The module is intentionally browser-free so tests can prove
    trust-lane failure before Playwright or source media handling starts.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from scripts._sir_convert_trust_lane_urls import (
    base_url_kind as _base_url_kind,
)
from scripts._sir_convert_trust_lane_urls import (
    is_private_destination,
    is_private_tunnel_destination,
    is_sanctioned_gateway_url,
)
from scripts._sir_convert_trust_lane_urls import (
    is_sanctioned_hemma_remote_proof_tunnel_url as _is_sanctioned_hemma_remote_proof_tunnel_url,
)
from scripts._sir_convert_trust_lane_urls import (
    redacted_url_origin as _redacted_url_origin,
)

ProofLane = Literal[
    "auto",
    "hemma-production",
    "remote-proof-gateway",
    "hemma-remote-proof",
    "mixed-tunnel-debug",
]

REMOTE_SERVICE_PROFILES = {"prod", "production", "hemma-production", "hemma"}
TRUST_LANE_ENV_KEYS = {
    "gateway_backend_url": (
        "SIR_CONVERT_REMOTE_INFERENCE_BACKEND_URL",
        "API_GATEWAY_SIR_CONVERT_PROTECTED_API_BACKEND_URL",
    ),
    "producer_backend_url": ("SIR_CONVERT_A_LOT_V2_BASE_URL",),
    "gateway_signer_fingerprint": (
        "HULEEDU_GATEWAY_INTERNAL_IDENTITY_PUBLIC_KEY_FINGERPRINT",
        "HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_FINGERPRINT",
    ),
    "sir_convert_trusted_fingerprint": (
        "SIR_CONVERT_TRUSTED_HULEEDU_GATEWAY_PUBLIC_KEY_FINGERPRINT",
        "SIR_CONVERT_INTERNAL_IDENTITY_TRUSTED_PUBLIC_KEY_FINGERPRINT",
    ),
    "sir_convert_ready_url": (
        "SIR_CONVERT_REMOTE_INFERENCE_READY_URL",
        "SIR_CONVERT_READY_URL",
    ),
    "proof_lane": ("SIR_CONVERT_REMOTE_INFERENCE_PROOF_LANE",),
}
PROOF_KIND = "audio_transcription_parity_live"


@dataclass(frozen=True)
class TrustLanePreflightInput:
    """Public metadata needed to validate a proof trust lane."""

    base_url: str
    gateway_backend_url: str | None = None
    producer_backend_url: str | None = None
    gateway_signer_fingerprint: str | None = None
    sir_convert_trusted_fingerprint: str | None = None
    sir_convert_service_profile: str | None = None
    allow_mixed_sir_convert_tunnel: bool = False
    proof_lane: str = "auto"


@dataclass(frozen=True)
class TrustLanePreflightResult:
    """Successful trust-lane preflight result retained in proof summaries."""

    status: Literal["passed"]
    lane_kind: str
    metadata: dict[str, object]


class SirConvertTrustLanePreflightError(RuntimeError):
    """Raised when proof would enter an incoherent Sir Convert trust lane."""

    def __init__(
        self,
        *,
        blocker_kind: str,
        message: str,
        metadata: dict[str, object],
    ) -> None:
        super().__init__(message)
        self.blocker_kind = blocker_kind
        self.metadata = metadata


def build_trust_lane_input(
    *,
    base_url: str,
    dotenv_path: Path,
    allow_mixed_sir_convert_tunnel: bool,
    proof_lane: str | None = None,
    gateway_backend_url: str | None = None,
    producer_backend_url: str | None = None,
    gateway_signer_fingerprint: str | None = None,
    sir_convert_trusted_fingerprint: str | None = None,
    sir_convert_ready_url: str | None = None,
) -> TrustLanePreflightInput:
    """Resolve preflight input from CLI values, environment, dotenv, and readyz metadata."""

    dotenv = _read_dotenv(dotenv_path)
    ready_metadata = _read_ready_metadata(
        _first_config_value(
            explicit=sir_convert_ready_url,
            keys=TRUST_LANE_ENV_KEYS["sir_convert_ready_url"],
            dotenv=dotenv,
        )
    )
    return TrustLanePreflightInput(
        base_url=base_url,
        gateway_backend_url=_first_config_value(
            explicit=gateway_backend_url,
            keys=TRUST_LANE_ENV_KEYS["gateway_backend_url"],
            dotenv=dotenv,
        ),
        producer_backend_url=_first_config_value(
            explicit=producer_backend_url,
            keys=TRUST_LANE_ENV_KEYS["producer_backend_url"],
            dotenv=dotenv,
        ),
        gateway_signer_fingerprint=_first_config_value(
            explicit=gateway_signer_fingerprint,
            keys=TRUST_LANE_ENV_KEYS["gateway_signer_fingerprint"],
            dotenv=dotenv,
        ),
        sir_convert_trusted_fingerprint=_first_config_value(
            explicit=sir_convert_trusted_fingerprint,
            keys=TRUST_LANE_ENV_KEYS["sir_convert_trusted_fingerprint"],
            dotenv=dotenv,
        ),
        sir_convert_service_profile=_service_profile(ready_metadata),
        allow_mixed_sir_convert_tunnel=allow_mixed_sir_convert_tunnel,
        proof_lane=_first_config_value(
            explicit=proof_lane,
            keys=TRUST_LANE_ENV_KEYS["proof_lane"],
            dotenv=dotenv,
        )
        or "auto",
    )


def run_trust_lane_preflight(
    value: TrustLanePreflightInput,
) -> TrustLanePreflightResult:
    """Fail closed when proof metadata describes an unsafe Sir Convert lane."""

    proof_lane = _normalized_proof_lane(value.proof_lane)
    metadata = _base_metadata(value, proof_lane=proof_lane)
    if metadata["base_url_kind"] == "remote":
        return _passed("hemma_production", metadata)

    if proof_lane == "hemma-production":
        raise _blocked(
            "sir_convert_trust_lane_unresolved",
            "Hemma production proof lane requires the canonical production base URL.",
            metadata,
        )

    if metadata["remote_compute"] is not True:
        raise _blocked(
            "sir_convert_trust_lane_unresolved",
            "Local proof did not declare a sanctioned remote Sir Convert trust lane.",
            metadata,
        )

    if proof_lane == "hemma-remote-proof":
        if not _has_sanctioned_hemma_remote_proof_tunnel(value):
            raise _blocked(
                "sir_convert_trust_lane_unresolved",
                "Hemma remote-proof lane requires the fenced remote-proof Sir Convert target.",
                metadata,
            )
        _validate_producer_backend(value, metadata, proof_lane=proof_lane)
        return _check_matching_fingerprints(
            value,
            metadata,
            lane_kind="hemma_remote_proof",
        )

    if _is_mixed_tunnel(value, proof_lane=proof_lane):
        if not value.allow_mixed_sir_convert_tunnel:
            raise _blocked(
                "sir_convert_mixed_tunnel_requires_explicit_opt_in",
                "Local Gateway to Hemma Sir Convert tunnel requires explicit debug opt-in.",
                metadata,
            )
        _validate_producer_backend(value, metadata, proof_lane=proof_lane)
        return _check_matching_fingerprints(
            value,
            metadata,
            lane_kind="mixed_tunnel_debug",
        )

    if proof_lane == "remote-proof-gateway":
        if not _has_sanctioned_remote_proof_gateway(value):
            raise _blocked(
                "sir_convert_trust_lane_unresolved",
                "Remote proof gateway lane requires a sanctioned HuleEdu Gateway target.",
                metadata,
            )
        _validate_producer_backend(value, metadata, proof_lane=proof_lane)
        return _check_matching_fingerprints(
            value,
            metadata,
            lane_kind="remote_proof_gateway",
        )

    raise _blocked(
        "sir_convert_trust_lane_unresolved",
        "Local proof did not declare a sanctioned remote Sir Convert trust lane.",
        metadata,
    )


def preflight_result_summary(result: TrustLanePreflightResult) -> dict[str, object]:
    """Create the redacted retained summary shape for a successful preflight."""

    return {
        "status": result.status,
        "lane_kind": result.lane_kind,
        **result.metadata,
    }


def preflight_failure_summary(
    error: SirConvertTrustLanePreflightError,
    *,
    base_url: str,
    app_path: str,
    artifact_dir: str,
) -> dict[str, object]:
    """Create the redacted retained summary shape for a preflight blocker."""

    return {
        "proof_kind": PROOF_KIND,
        "observed_at": _utc_now(),
        "base_url": _redacted_url_origin(base_url),
        "app_path": app_path,
        "status": "failed",
        "failure": {
            "type": "sir_convert_trust_lane_preflight_failed",
            "kind": error.blocker_kind,
            "message": str(error),
        },
        "blocker_kind": error.blocker_kind,
        "trust_lane_preflight": {
            "status": "failed",
            "blocker_kind": error.blocker_kind,
            **error.metadata,
        },
        "artifacts": {"artifact_dir": artifact_dir},
    }


def _read_dotenv(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _first_config_value(
    *,
    explicit: str | None,
    keys: tuple[str, ...],
    dotenv: Mapping[str, str],
) -> str | None:
    if explicit:
        return explicit
    for key in keys:
        value = os.environ.get(key) or dotenv.get(key)
        if value:
            return value
    return None


def _read_ready_metadata(ready_url: str | None) -> dict[str, object]:
    if not ready_url:
        return {}
    request = Request(ready_url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _service_profile(metadata: Mapping[str, object]) -> str | None:
    for key in ("service_profile", "expected_service_profile"):
        value = metadata.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _normalized_proof_lane(value: str) -> ProofLane:
    normalized = value.strip().lower().replace("_", "-") if value else "auto"
    if normalized == "hemma-production":
        return "hemma-production"
    if normalized == "remote-proof-gateway":
        return "remote-proof-gateway"
    if normalized in {"hemma-remote-proof", "remote-proof"}:
        return "hemma-remote-proof"
    if normalized == "mixed-tunnel-debug":
        return "mixed-tunnel-debug"
    return "auto"


def _base_metadata(value: TrustLanePreflightInput, *, proof_lane: ProofLane) -> dict[str, object]:
    base_url_kind = _base_url_kind(value.base_url)
    metadata = {
        "base_url": _redacted_url_origin(value.base_url),
        "base_url_kind": base_url_kind,
        "proof_lane": proof_lane,
        "gateway_backend_url": _redacted_url_origin(value.gateway_backend_url),
        "producer_backend_url": _redacted_url_origin(value.producer_backend_url),
        "sir_convert_service_profile": value.sir_convert_service_profile,
        "gateway_signer_fingerprint": _normalized_fingerprint(value.gateway_signer_fingerprint),
        "sir_convert_trusted_fingerprint": _normalized_fingerprint(
            value.sir_convert_trusted_fingerprint
        ),
        "remote_compute": _uses_remote_compute(
            value,
            base_url_kind=base_url_kind,
            proof_lane=proof_lane,
        ),
        "mixed_tunnel": _is_mixed_tunnel(value, proof_lane=proof_lane),
        "job_submit_allowed": False,
    }
    return metadata


def _uses_remote_compute(
    value: TrustLanePreflightInput,
    *,
    base_url_kind: str,
    proof_lane: ProofLane,
) -> bool:
    if base_url_kind == "remote":
        return True
    if proof_lane == "remote-proof-gateway":
        return _has_sanctioned_remote_proof_gateway(value)
    if proof_lane == "hemma-remote-proof":
        return _has_sanctioned_hemma_remote_proof_tunnel(value)
    return is_private_destination(value.gateway_backend_url)


def _has_sanctioned_remote_proof_gateway(value: TrustLanePreflightInput) -> bool:
    return is_sanctioned_gateway_url(value.gateway_backend_url)


def _has_sanctioned_hemma_remote_proof_tunnel(value: TrustLanePreflightInput) -> bool:
    return _is_sanctioned_hemma_remote_proof_tunnel_url(
        value.gateway_backend_url,
        service_profile=value.sir_convert_service_profile,
    )


def _validate_producer_backend(
    value: TrustLanePreflightInput,
    metadata: dict[str, object],
    *,
    proof_lane: ProofLane,
) -> None:
    if proof_lane == "hemma-remote-proof":
        if _is_sanctioned_hemma_remote_proof_tunnel_url(
            value.producer_backend_url,
            service_profile=value.sir_convert_service_profile,
        ):
            return
        raise _blocked(
            "sir_convert_producer_lane_unresolved",
            "Skriptoteket formatter producer must target the fenced remote-proof Sir Convert service.",
            metadata,
        )
    if value.producer_backend_url and _producer_backend_uses_remote_compute(
        value.producer_backend_url
    ):
        return
    raise _blocked(
        "sir_convert_producer_lane_unresolved",
        "Skriptoteket formatter producer must target a sanctioned remote Sir Convert service.",
        metadata,
    )


def _producer_backend_uses_remote_compute(raw_url: str) -> bool:
    return is_private_destination(raw_url)


def _is_mixed_tunnel(value: TrustLanePreflightInput, *, proof_lane: ProofLane) -> bool:
    if proof_lane == "hemma-remote-proof" or not is_private_destination(value.gateway_backend_url):
        return False
    if proof_lane == "mixed-tunnel-debug":
        return True
    profile = (value.sir_convert_service_profile or "").strip().lower()
    return (
        is_private_tunnel_destination(value.gateway_backend_url)
        or profile in REMOTE_SERVICE_PROFILES
    )


def _check_matching_fingerprints(
    value: TrustLanePreflightInput,
    metadata: dict[str, object],
    *,
    lane_kind: str,
) -> TrustLanePreflightResult:
    signer = _normalized_fingerprint(value.gateway_signer_fingerprint)
    verifier = _normalized_fingerprint(value.sir_convert_trusted_fingerprint)
    if not signer or not verifier:
        raise _blocked(
            "sir_convert_trust_lane_unresolved",
            "Remote proof lane requires public signer and verifier fingerprints.",
            metadata,
        )
    if signer != verifier:
        raise _blocked(
            "sir_convert_trust_lane_mismatch",
            "Local signer public key is not trusted by the remote Sir Convert verifier.",
            metadata,
        )
    return _passed(lane_kind, metadata)


def _normalized_fingerprint(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized.removeprefix("sha256:") or None


def _passed(lane_kind: str, metadata: dict[str, object]) -> TrustLanePreflightResult:
    return TrustLanePreflightResult(
        status="passed",
        lane_kind=lane_kind,
        metadata={**metadata, "job_submit_allowed": True},
    )


def _blocked(
    blocker_kind: str,
    message: str,
    metadata: dict[str, object],
) -> SirConvertTrustLanePreflightError:
    return SirConvertTrustLanePreflightError(
        blocker_kind=blocker_kind,
        message=message,
        metadata={**metadata, "job_submit_allowed": False},
    )


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
