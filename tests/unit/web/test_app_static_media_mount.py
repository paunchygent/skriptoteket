"""Static media mount tests for the web app factory.

Purpose:
    Verify that published tutorial media under `MEDIA_ROOT` is served at
    `/static/media` with byte-range support, and that an absent media
    directory leaves the app bootable with 404 answers.

Relationships:
    - Verifies `skriptoteket.web.app.create_app` mount wiring.
    - Exercises `skriptoteket.web.app.OptionalDirectoryStaticFiles`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from skriptoteket.config import Settings
from skriptoteket.web import app as web_app

_CLIP_BYTES = b"0123456789abcdef"


def _create_app_with_media_root(
    *,
    monkeypatch: pytest.MonkeyPatch,
    media_root: Path,
) -> FastAPI:
    settings = Settings.model_construct(
        APP_NAME="Skriptoteket",
        APP_VERSION="0.2.0",
        ENVIRONMENT="development",
        ENABLE_DOCS=None,
        ALLOWED_HOSTS="localhost,127.0.0.1",
        MEDIA_ROOT=media_root,
    )
    monkeypatch.setattr(web_app, "Settings", lambda: settings)
    monkeypatch.setattr(web_app, "configure_logging", lambda **_: None)
    monkeypatch.setattr(web_app, "init_tracing", lambda *_: None)
    monkeypatch.setattr(web_app, "create_container", lambda _settings: object())
    monkeypatch.setattr(web_app, "setup_dishka", lambda *args, **kwargs: None)

    async def _fake_check_smtp(_settings: Settings) -> tuple[str, None]:
        return ("healthy", None)

    async def _fake_ensure_database_revision_is_current(_settings: Settings) -> None:
        return None

    monkeypatch.setattr(web_app, "check_smtp", _fake_check_smtp)
    monkeypatch.setattr(
        web_app,
        "ensure_database_revision_is_current",
        _fake_ensure_database_revision_is_current,
    )
    return web_app.create_app()


def test_media_mount_serves_file_with_range_support(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    clip_dir = tmp_path / "klassrumskartan"
    clip_dir.mkdir()
    (clip_dir / "overview.mp4").write_bytes(_CLIP_BYTES)
    app = _create_app_with_media_root(monkeypatch=monkeypatch, media_root=tmp_path)

    with TestClient(app, base_url="http://localhost") as client:
        full = client.get("/static/media/klassrumskartan/overview.mp4")
        partial = client.get(
            "/static/media/klassrumskartan/overview.mp4",
            headers={"Range": "bytes=0-3"},
        )

    assert full.status_code == 200
    assert full.content == _CLIP_BYTES
    assert full.headers["accept-ranges"] == "bytes"
    assert partial.status_code == 206
    assert partial.content == b"0123"
    assert partial.headers["content-range"] == f"bytes 0-3/{len(_CLIP_BYTES)}"


def test_media_mount_takes_precedence_over_bundled_static_assets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    app = _create_app_with_media_root(monkeypatch=monkeypatch, media_root=tmp_path)

    mount_names = [getattr(route, "name", None) for route in app.routes]

    assert mount_names.index("media") < mount_names.index("static")


def test_media_mount_answers_404_when_media_root_is_absent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing_root = tmp_path / "not-published-yet"
    app = _create_app_with_media_root(monkeypatch=monkeypatch, media_root=missing_root)

    with TestClient(app, base_url="http://localhost") as client:
        manifest = client.get("/static/media/klassrumskartan/clips.json")
        repeated = client.get("/static/media/klassrumskartan/clips.json")
        bundled = client.get("/static/css/huleedu-design-tokens.css")

    assert manifest.status_code == 404
    assert repeated.status_code == 404
    assert bundled.status_code == 200


def test_media_mount_serves_directory_published_after_startup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    media_root = tmp_path / "published-later"
    app = _create_app_with_media_root(monkeypatch=monkeypatch, media_root=media_root)

    with TestClient(app, base_url="http://localhost") as client:
        before = client.get("/static/media/klassrumskartan/clips.json")
        (media_root / "klassrumskartan").mkdir(parents=True)
        (media_root / "klassrumskartan" / "clips.json").write_text("{}", encoding="utf-8")
        after = client.get("/static/media/klassrumskartan/clips.json")

    assert before.status_code == 404
    assert after.status_code == 200
    assert after.json() == {}
