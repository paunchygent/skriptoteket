"""Tests for SPA history fallback route."""

from __future__ import annotations

import pytest

from skriptoteket.web.routes.spa_fallback import _should_serve_spa


@pytest.mark.unit
class TestShouldServeSpa:
    """Test the path exclusion logic for SPA fallback."""

    def test_root_path_should_serve_spa(self) -> None:
        assert _should_serve_spa("/") is True

    def test_browse_paths_should_serve_spa(self) -> None:
        assert _should_serve_spa("/browse") is True
        assert _should_serve_spa("/browse/tools") is True
        assert _should_serve_spa("/browse/profession/category") is True

    def test_admin_paths_should_serve_spa(self) -> None:
        assert _should_serve_spa("/admin/tools") is True
        assert _should_serve_spa("/admin/tools/123") is True

    def test_my_runs_paths_should_serve_spa(self) -> None:
        assert _should_serve_spa("/my-runs") is True
        assert _should_serve_spa("/my-runs/abc-123") is True

    def test_api_paths_excluded(self) -> None:
        assert _should_serve_spa("/api/v1/auth/me") is False
        assert _should_serve_spa("/api/v1/editor/tools/123/draft") is False
        assert _should_serve_spa("/api/v1/runs/123") is False

    def test_static_paths_excluded(self) -> None:
        assert _should_serve_spa("/static/spa/assets/main.js") is False
        assert _should_serve_spa("/static/css/app.css") is False
        assert _should_serve_spa("/static/js/vendor.js") is False

    def test_observability_paths_excluded(self) -> None:
        assert _should_serve_spa("/healthz") is False
        assert _should_serve_spa("/metrics") is False

    def test_openapi_paths_excluded(self) -> None:
        assert _should_serve_spa("/docs") is False
        assert _should_serve_spa("/redoc") is False
        assert _should_serve_spa("/openapi.json") is False

    def test_login_path_should_serve_spa(self) -> None:
        # Login is handled by SPA (Vue Router)
        assert _should_serve_spa("/login") is True

    def test_forbidden_path_should_serve_spa(self) -> None:
        # Forbidden page is part of SPA
        assert _should_serve_spa("/forbidden") is True
