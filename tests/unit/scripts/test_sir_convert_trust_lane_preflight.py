"""Sir Convert remote inference trust-lane preflight tests.

Domain purpose:
    Prove that Conversion Hub live proof blocks incoherent HuleEdu Gateway to
    Sir Convert trust lanes before media upload or producer job creation.

Relationships:
    Exercises the proof preflight helper and the Audio Transcription parity live
    proof entrypoint without launching a browser or contacting Sir Convert.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts._sir_convert_trust_lane_preflight import (
    SirConvertTrustLanePreflightError,
    TrustLanePreflightInput,
    preflight_failure_summary,
    run_trust_lane_preflight,
)
from scripts.audio_transcription_parity_live import run

LOCAL_SIGNER_FINGERPRINT = "46aefc0edc2f71267e2df783ca27f4df2b0da269cc7e84b43cbe2de6ac7c1992"
HEMMA_VERIFIER_FINGERPRINT = "c84080a7b068dba5c42d3d06b5109d3696e8ba960c2db0abc4d1d71b3e9f3b08"


def _input(**overrides: object) -> TrustLanePreflightInput:
    values = {
        "base_url": "http://127.0.0.1:5173",
        "gateway_backend_url": "http://host.docker.internal:28085",
        "producer_backend_url": "http://host.docker.internal:28085",
        "gateway_signer_fingerprint": LOCAL_SIGNER_FINGERPRINT,
        "sir_convert_trusted_fingerprint": HEMMA_VERIFIER_FINGERPRINT,
        "sir_convert_service_profile": "prod",
        "allow_mixed_sir_convert_tunnel": False,
        "proof_lane": "auto",
    }
    values.update(overrides)
    return TrustLanePreflightInput(**values)


def test_local_signer_to_hemma_verifier_mismatch_blocks_before_submit() -> None:
    with pytest.raises(SirConvertTrustLanePreflightError) as exc_info:
        run_trust_lane_preflight(
            _input(
                allow_mixed_sir_convert_tunnel=True,
            )
        )

    error = exc_info.value
    assert error.blocker_kind == "sir_convert_trust_lane_mismatch"
    assert error.metadata["base_url_kind"] == "local"
    assert error.metadata["remote_compute"] is True
    assert error.metadata["job_submit_allowed"] is False
    assert error.metadata["gateway_signer_fingerprint"] == LOCAL_SIGNER_FINGERPRINT
    assert error.metadata["sir_convert_trusted_fingerprint"] == HEMMA_VERIFIER_FINGERPRINT


def test_mixed_tunnel_requires_explicit_opt_in_even_when_fingerprints_match() -> None:
    with pytest.raises(SirConvertTrustLanePreflightError) as exc_info:
        run_trust_lane_preflight(
            _input(
                gateway_signer_fingerprint=HEMMA_VERIFIER_FINGERPRINT,
                sir_convert_trusted_fingerprint=HEMMA_VERIFIER_FINGERPRINT,
            )
        )

    assert exc_info.value.blocker_kind == "sir_convert_mixed_tunnel_requires_explicit_opt_in"
    assert exc_info.value.metadata["job_submit_allowed"] is False


def test_matching_public_fingerprints_allow_explicit_mixed_debug_lane() -> None:
    result = run_trust_lane_preflight(
        _input(
            gateway_signer_fingerprint=HEMMA_VERIFIER_FINGERPRINT,
            sir_convert_trusted_fingerprint=HEMMA_VERIFIER_FINGERPRINT,
            allow_mixed_sir_convert_tunnel=True,
        )
    )

    assert result.status == "passed"
    assert result.lane_kind == "mixed_tunnel_debug"
    assert result.metadata["job_submit_allowed"] is True
    assert result.metadata["remote_compute"] is True


def test_hemma_remote_proof_lane_allows_local_auth_tunnel_without_debug_opt_in() -> None:
    result = run_trust_lane_preflight(
        _input(
            gateway_signer_fingerprint=LOCAL_SIGNER_FINGERPRINT,
            sir_convert_trusted_fingerprint=LOCAL_SIGNER_FINGERPRINT,
            sir_convert_service_profile="remote-proof",
            proof_lane="hemma-remote-proof",
        )
    )

    assert result.status == "passed"
    assert result.lane_kind == "hemma_remote_proof"
    assert result.metadata["job_submit_allowed"] is True
    assert result.metadata["remote_compute"] is True
    assert result.metadata["mixed_tunnel"] is False


def test_hemma_remote_proof_lane_rejects_production_service_profile() -> None:
    with pytest.raises(SirConvertTrustLanePreflightError) as exc_info:
        run_trust_lane_preflight(
            _input(
                gateway_signer_fingerprint=LOCAL_SIGNER_FINGERPRINT,
                sir_convert_trusted_fingerprint=LOCAL_SIGNER_FINGERPRINT,
                sir_convert_service_profile="prod",
                proof_lane="hemma-remote-proof",
            )
        )

    assert exc_info.value.blocker_kind == "sir_convert_trust_lane_unresolved"
    assert exc_info.value.metadata["job_submit_allowed"] is False


def test_hemma_remote_proof_lane_rejects_split_producer_target() -> None:
    with pytest.raises(SirConvertTrustLanePreflightError) as exc_info:
        run_trust_lane_preflight(
            _input(
                gateway_signer_fingerprint=LOCAL_SIGNER_FINGERPRINT,
                sir_convert_trusted_fingerprint=LOCAL_SIGNER_FINGERPRINT,
                sir_convert_service_profile="remote-proof",
                proof_lane="hemma-remote-proof",
                producer_backend_url="http://host.docker.internal:8085",
            )
        )

    assert exc_info.value.blocker_kind == "sir_convert_producer_lane_unresolved"
    assert exc_info.value.metadata["gateway_backend_url"] == "http://host.docker.internal:28085"
    assert exc_info.value.metadata["producer_backend_url"] == "http://host.docker.internal:8085"
    assert exc_info.value.metadata["job_submit_allowed"] is False


def test_production_base_url_allows_remote_inference_without_local_signer_metadata() -> None:
    result = run_trust_lane_preflight(
        _input(
            base_url="https://skriptoteket.hule.education",
            gateway_backend_url=None,
            gateway_signer_fingerprint=None,
            sir_convert_trusted_fingerprint=None,
            sir_convert_service_profile=None,
        )
    )

    assert result.status == "passed"
    assert result.lane_kind == "hemma_production"
    assert result.metadata["base_url_kind"] == "remote"
    assert result.metadata["job_submit_allowed"] is True


@pytest.mark.parametrize(
    "base_url",
    [
        "http://192.168.1.44:5173",
        "http://0.0.0.0:5173",
        "http://olofs-mba.local:5173",
    ],
)
def test_lan_and_machine_aliases_block_without_verified_remote_lane(base_url: str) -> None:
    with pytest.raises(SirConvertTrustLanePreflightError) as exc_info:
        run_trust_lane_preflight(
            _input(
                base_url=base_url,
                gateway_backend_url=None,
                gateway_signer_fingerprint=None,
                sir_convert_trusted_fingerprint=None,
                sir_convert_service_profile=None,
            )
        )

    assert exc_info.value.blocker_kind == "sir_convert_trust_lane_unresolved"
    assert exc_info.value.metadata["base_url_kind"] == "local"
    assert exc_info.value.metadata["job_submit_allowed"] is False


def test_machine_alias_allows_verified_remote_proof_gateway_lane() -> None:
    result = run_trust_lane_preflight(
        _input(
            base_url="http://olofs-mba.local:5173",
            gateway_backend_url="https://api.hule.education/sir-convert/v2/convert",
            gateway_signer_fingerprint=HEMMA_VERIFIER_FINGERPRINT,
            sir_convert_trusted_fingerprint=HEMMA_VERIFIER_FINGERPRINT,
            sir_convert_service_profile=None,
            proof_lane="remote-proof-gateway",
        )
    )

    assert result.status == "passed"
    assert result.lane_kind == "remote_proof_gateway"
    assert result.metadata["base_url_kind"] == "local"
    assert result.metadata["job_submit_allowed"] is True


def test_remote_proof_gateway_blocks_without_gateway_target() -> None:
    with pytest.raises(SirConvertTrustLanePreflightError) as exc_info:
        run_trust_lane_preflight(
            _input(
                gateway_backend_url=None,
                gateway_signer_fingerprint=HEMMA_VERIFIER_FINGERPRINT,
                sir_convert_trusted_fingerprint=HEMMA_VERIFIER_FINGERPRINT,
                sir_convert_service_profile=None,
                proof_lane="remote-proof-gateway",
            )
        )

    assert exc_info.value.blocker_kind == "sir_convert_trust_lane_unresolved"
    assert exc_info.value.metadata["remote_compute"] is False
    assert exc_info.value.metadata["job_submit_allowed"] is False


@pytest.mark.parametrize(
    "gateway_backend_url",
    [
        "http://127.0.0.1:8085",
        "http://host.docker.internal:8085",
    ],
)
def test_remote_proof_gateway_rejects_local_gateway_targets(gateway_backend_url: str) -> None:
    with pytest.raises(SirConvertTrustLanePreflightError) as exc_info:
        run_trust_lane_preflight(
            _input(
                gateway_backend_url=gateway_backend_url,
                gateway_signer_fingerprint=HEMMA_VERIFIER_FINGERPRINT,
                sir_convert_trusted_fingerprint=HEMMA_VERIFIER_FINGERPRINT,
                sir_convert_service_profile=None,
                proof_lane="remote-proof-gateway",
            )
        )

    assert exc_info.value.blocker_kind == "sir_convert_trust_lane_unresolved"
    assert exc_info.value.metadata["remote_compute"] is False
    assert exc_info.value.metadata["job_submit_allowed"] is False


def test_mixed_tunnel_debug_lane_still_requires_cli_opt_in() -> None:
    with pytest.raises(SirConvertTrustLanePreflightError) as exc_info:
        run_trust_lane_preflight(
            _input(
                gateway_signer_fingerprint=HEMMA_VERIFIER_FINGERPRINT,
                sir_convert_trusted_fingerprint=HEMMA_VERIFIER_FINGERPRINT,
                proof_lane="mixed-tunnel-debug",
            )
        )

    assert exc_info.value.blocker_kind == "sir_convert_mixed_tunnel_requires_explicit_opt_in"
    assert exc_info.value.metadata["job_submit_allowed"] is False


def test_local_base_url_cannot_self_declare_hemma_production() -> None:
    with pytest.raises(SirConvertTrustLanePreflightError) as exc_info:
        run_trust_lane_preflight(
            _input(
                gateway_backend_url=None,
                gateway_signer_fingerprint=None,
                sir_convert_trusted_fingerprint=None,
                sir_convert_service_profile=None,
                proof_lane="hemma-production",
            )
        )

    assert exc_info.value.blocker_kind == "sir_convert_trust_lane_unresolved"
    assert exc_info.value.metadata["job_submit_allowed"] is False


def test_failure_summary_keeps_only_public_redacted_metadata() -> None:
    with pytest.raises(SirConvertTrustLanePreflightError) as exc_info:
        run_trust_lane_preflight(
            _input(
                gateway_backend_url=(
                    "https://service-user:super-secret-password@convert.hule.education/"
                    "v2?token=private-token#cookie"
                ),
                allow_mixed_sir_convert_tunnel=True,
            )
        )

    summary = preflight_failure_summary(
        exc_info.value,
        base_url="http://user:base-url-password@127.0.0.1:5173/app?token=private-cookie",
        app_path="/apps/documents.conversion_hub",
        artifact_dir="/tmp/artifact",
    )
    rendered = json.dumps(summary, sort_keys=True)

    assert summary["status"] == "failed"
    assert summary["blocker_kind"] == "sir_convert_trust_lane_mismatch"
    assert summary["base_url"] == "http://127.0.0.1:5173"
    assert (
        summary["trust_lane_preflight"]["gateway_backend_url"] == "https://convert.hule.education"
    )
    assert LOCAL_SIGNER_FINGERPRINT in rendered
    assert HEMMA_VERIFIER_FINGERPRINT in rendered
    assert "super-secret-password" not in rendered
    assert "base-url-password" not in rendered
    assert "private-token" not in rendered
    assert "private-cookie" not in rendered
    assert "private" not in rendered.lower()
    assert "password" not in rendered.lower()
    assert "cookie" not in rendered.lower()
    assert "transcript text" not in rendered.lower()


def test_transcript_live_proof_exits_before_copying_media_when_preflight_blocks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in (
        "SIR_CONVERT_REMOTE_INFERENCE_BACKEND_URL",
        "API_GATEWAY_SIR_CONVERT_PROTECTED_API_BACKEND_URL",
        "SIR_CONVERT_A_LOT_V2_BASE_URL",
        "HULEEDU_GATEWAY_INTERNAL_IDENTITY_PUBLIC_KEY_FINGERPRINT",
        "HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_FINGERPRINT",
        "SIR_CONVERT_TRUSTED_HULEEDU_GATEWAY_PUBLIC_KEY_FINGERPRINT",
        "SIR_CONVERT_INTERNAL_IDENTITY_TRUSTED_PUBLIC_KEY_FINGERPRINT",
        "SIR_CONVERT_REMOTE_INFERENCE_READY_URL",
        "SIR_CONVERT_READY_URL",
        "SIR_CONVERT_REMOTE_INFERENCE_PROOF_LANE",
    ):
        monkeypatch.delenv(key, raising=False)
    audio_path = tmp_path / "source.mp3"
    audio_path.write_bytes(b"not-real-audio")
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "PLAYWRIGHT_EMAIL=proof@example.test",
                "PLAYWRIGHT_PASSWORD=super-secret-password",
            ]
        ),
        encoding="utf-8",
    )
    artifact_root = tmp_path / "proof-artifacts"

    with pytest.raises(SystemExit) as exc_info:
        run(
            [
                "--audio-file",
                str(audio_path),
                "--base-url",
                "http://127.0.0.1:5173",
                "--dotenv",
                str(dotenv_path),
                "--artifact-root",
                str(artifact_root),
            ]
        )

    assert str(exc_info.value) == "sir_convert_trust_lane_unresolved"
    run_dirs = list(artifact_root.iterdir())
    assert len(run_dirs) == 1
    summary = json.loads((run_dirs[0] / "proof-summary.json").read_text(encoding="utf-8"))
    rendered_summary = json.dumps(summary, sort_keys=True)
    assert summary["failure"]["type"] == "sir_convert_trust_lane_preflight_failed"
    assert summary["blocker_kind"] == "sir_convert_trust_lane_unresolved"
    assert list(run_dirs[0].glob(f"*{audio_path.name}")) == []
    assert "super-secret-password" not in rendered_summary
    assert "not-real-audio" not in rendered_summary


def test_transcript_live_proof_blocks_split_gateway_and_producer_lanes_before_copying_media(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in (
        "SIR_CONVERT_REMOTE_INFERENCE_BACKEND_URL",
        "API_GATEWAY_SIR_CONVERT_PROTECTED_API_BACKEND_URL",
        "SIR_CONVERT_A_LOT_V2_BASE_URL",
        "HULEEDU_GATEWAY_INTERNAL_IDENTITY_PUBLIC_KEY_FINGERPRINT",
        "HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_FINGERPRINT",
        "SIR_CONVERT_TRUSTED_HULEEDU_GATEWAY_PUBLIC_KEY_FINGERPRINT",
        "SIR_CONVERT_INTERNAL_IDENTITY_TRUSTED_PUBLIC_KEY_FINGERPRINT",
        "SIR_CONVERT_REMOTE_INFERENCE_READY_URL",
        "SIR_CONVERT_READY_URL",
        "SIR_CONVERT_REMOTE_INFERENCE_PROOF_LANE",
    ):
        monkeypatch.delenv(key, raising=False)
    audio_path = tmp_path / "source.mp3"
    audio_path.write_bytes(b"not-real-audio")
    monkeypatch.setattr(
        "scripts._sir_convert_trust_lane_preflight._read_ready_metadata",
        lambda _ready_url: {"service_profile": "remote-proof"},
    )
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "PLAYWRIGHT_EMAIL=proof@example.test",
                "PLAYWRIGHT_PASSWORD=super-secret-password",
                "SIR_CONVERT_REMOTE_INFERENCE_PROOF_LANE=hemma-remote-proof",
                "SIR_CONVERT_REMOTE_INFERENCE_BACKEND_URL=http://host.docker.internal:28085",
                "SIR_CONVERT_A_LOT_V2_BASE_URL=http://host.docker.internal:8085",
                "HULEEDU_GATEWAY_INTERNAL_IDENTITY_PUBLIC_KEY_FINGERPRINT="
                f"{LOCAL_SIGNER_FINGERPRINT}",
                "SIR_CONVERT_TRUSTED_HULEEDU_GATEWAY_PUBLIC_KEY_FINGERPRINT="
                f"{LOCAL_SIGNER_FINGERPRINT}",
            ]
        ),
        encoding="utf-8",
    )
    artifact_root = tmp_path / "proof-artifacts"

    with pytest.raises(SystemExit) as exc_info:
        run(
            [
                "--audio-file",
                str(audio_path),
                "--base-url",
                "http://127.0.0.1:5173",
                "--dotenv",
                str(dotenv_path),
                "--artifact-root",
                str(artifact_root),
            ]
        )

    assert str(exc_info.value) == "sir_convert_producer_lane_unresolved"
    run_dirs = list(artifact_root.iterdir())
    assert len(run_dirs) == 1
    summary = json.loads((run_dirs[0] / "proof-summary.json").read_text(encoding="utf-8"))
    rendered_summary = json.dumps(summary, sort_keys=True)
    assert summary["failure"]["type"] == "sir_convert_trust_lane_preflight_failed"
    assert summary["blocker_kind"] == "sir_convert_producer_lane_unresolved"
    assert summary["trust_lane_preflight"]["gateway_backend_url"] == (
        "http://host.docker.internal:28085"
    )
    assert summary["trust_lane_preflight"]["producer_backend_url"] == (
        "http://host.docker.internal:8085"
    )
    assert list(run_dirs[0].glob(f"*{audio_path.name}")) == []
    assert "super-secret-password" not in rendered_summary
    assert "not-real-audio" not in rendered_summary


def test_transcript_live_proof_blocks_running_producer_mismatch_before_copying_media(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audio_path = tmp_path / "source.mp3"
    audio_path.write_bytes(b"not-real-audio")
    monkeypatch.setattr(
        "scripts._sir_convert_trust_lane_preflight._read_ready_metadata",
        lambda _ready_url: {"service_profile": "remote-proof"},
    )
    monkeypatch.setattr(
        "scripts._proof_live_monitoring.capture_local_backend_container_snapshot",
        lambda *, artifact_dir: {
            "status": "captured",
            "environment": {
                "sir_convert_base_url": "http://host.docker.internal:8085",
            },
        },
    )

    def fail_on_copy(**_kwargs: object) -> Path:
        raise AssertionError("media must not be copied when the running producer lane is split")

    monkeypatch.setattr(
        "scripts.audio_transcription_parity_live._copy_audio_for_submission",
        fail_on_copy,
    )
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "PLAYWRIGHT_EMAIL=proof@example.test",
                "PLAYWRIGHT_PASSWORD=super-secret-password",
                "SIR_CONVERT_REMOTE_INFERENCE_PROOF_LANE=hemma-remote-proof",
                "SIR_CONVERT_REMOTE_INFERENCE_BACKEND_URL=http://host.docker.internal:28085",
                "SIR_CONVERT_A_LOT_V2_BASE_URL=http://host.docker.internal:28085",
                "HULEEDU_GATEWAY_INTERNAL_IDENTITY_PUBLIC_KEY_FINGERPRINT="
                f"{LOCAL_SIGNER_FINGERPRINT}",
                "SIR_CONVERT_TRUSTED_HULEEDU_GATEWAY_PUBLIC_KEY_FINGERPRINT="
                f"{LOCAL_SIGNER_FINGERPRINT}",
            ]
        ),
        encoding="utf-8",
    )
    artifact_root = tmp_path / "proof-artifacts"

    with pytest.raises(SystemExit) as exc_info:
        run(
            [
                "--audio-file",
                str(audio_path),
                "--base-url",
                "http://127.0.0.1:5173",
                "--dotenv",
                str(dotenv_path),
                "--artifact-root",
                str(artifact_root),
            ]
        )

    assert str(exc_info.value) == "sir_convert_running_producer_lane_mismatch"
    run_dirs = list(artifact_root.iterdir())
    assert len(run_dirs) == 1
    summary = json.loads((run_dirs[0] / "proof-summary.json").read_text(encoding="utf-8"))
    assert summary["blocker_kind"] == "sir_convert_running_producer_lane_mismatch"
    assert summary["trust_lane_preflight"]["producer_backend_url"] == (
        "http://host.docker.internal:28085"
    )
    assert summary["trust_lane_preflight"]["running_producer_backend_url"] == (
        "http://host.docker.internal:8085"
    )
    assert list(run_dirs[0].glob(f"*{audio_path.name}")) == []
