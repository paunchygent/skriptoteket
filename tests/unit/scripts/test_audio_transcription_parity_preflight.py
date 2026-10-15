"""Audio Transcription live entrypoint preflight and media-copy fences."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.audio_transcription_parity_live import run

LOCAL_SIGNER_FINGERPRINT = "46aefc0edc2f71267e2df783ca27f4df2b0da269cc7e84b43cbe2de6ac7c1992"


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
