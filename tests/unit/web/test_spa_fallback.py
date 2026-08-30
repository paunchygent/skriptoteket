"""Tests for crawler files and SPA history fallback routing.

Purpose:
    Prove the backend serves crawler-owned resources directly and only returns
    the Vue SPA shell for explicitly owned route families.

Relationships:
    - Exercises `skriptoteket.web.routes.spa_fallback`.
    - Protects the launch SEO route contract from `ST-35-02`.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from skriptoteket.web.routes import spa_fallback
from skriptoteket.web.routes.spa_fallback import _should_serve_spa

HOME_TITLE = "Skriptoteket | Lektionsplanering direkt i webbläsaren"
HOME_DESCRIPTION = (
    "Skriptoteket samlar lärarverktyg och öppna appar som Klassrumskartan "
    "för planering direkt i webbläsaren."
)
PUBLIC_APP_TITLE = "Klassrumskartan | Skriptoteket"
PUBLIC_APP_DESCRIPTION = (
    "Planera grupper och placeringar direkt i webbläsaren med Klassrumskartan, "
    "en öppen app i Skriptoteket."
)
PUBLIC_APP_PATH = "/public/apps/classroom.group-seating-studio"


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.state.public_app_base_url = "https://skriptoteket.hule.education"
    app.include_router(spa_fallback.router)
    return TestClient(app)


def _assert_meta_name(html: str, name: str, content: str) -> None:
    assert f'<meta name="{name}" content="{content}" />' in html


def _assert_meta_property(html: str, property_name: str, content: str) -> None:
    assert f'<meta property="{property_name}" content="{content}" />' in html


def _assert_public_metadata(
    html: str,
    *,
    title: str,
    description: str,
    canonical_url: str,
) -> None:
    assert f"<title>{title}</title>" in html
    _assert_meta_name(html, "description", description)
    _assert_meta_name(html, "robots", "index,follow")
    assert f'<link rel="canonical" href="{canonical_url}" />' in html
    _assert_meta_property(html, "og:title", title)
    _assert_meta_property(html, "og:description", description)
    _assert_meta_property(html, "og:url", canonical_url)
    _assert_meta_property(html, "og:type", "website")
    _assert_meta_name(html, "twitter:card", "summary")
    _assert_meta_name(html, "twitter:title", title)
    _assert_meta_name(html, "twitter:description", description)


@pytest.mark.unit
class TestShouldServeSpa:
    """Test the path exclusion logic for SPA fallback."""

    @pytest.mark.parametrize(
        "path",
        [
            "/",
            PUBLIC_APP_PATH,
            "/public/apps/documents.conversion_hub/exam-converter",
            "/auth/login",
            "/auth/callback",
            "/auth/provisioning-required",
            "/forgot-password",
            "/register",
            "/reset-password",
            "/verify-email",
            "/profile",
            "/forbidden",
            "/browse",
            "/browse/professions",
            "/browse/professions/matematik",
            "/browse/professions/matematik/algebra",
            "/apps/classroom.group-seating-studio",
            "/tools/example/run",
            "/my-runs",
            "/my-runs/abc-123",
            "/vault",
            "/my-tools",
            "/editor",
            "/admin/tools",
            "/admin/tools/123",
            "/admin/users",
            "/admin/users/123",
            "/admin/tool-versions/123",
            "/suggestions/new",
            "/admin/suggestions",
            "/admin/suggestions/123",
        ],
    )
    def test_valid_spa_paths_should_serve_spa(self, path: str) -> None:
        assert _should_serve_spa(path) is True

    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/auth/me",
            "/api/v1/editor/tools/123/draft",
            "/api/v1/runs/123",
            "/static/spa/assets/main.js",
            "/static/css/app.css",
            "/static/js/vendor.js",
            "/healthz",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/robots.txt",
            "/sitemap.xml",
            "/login",
            "/browse/tools",
            "/browse/profession/category",
            "/public/apps",
            "/public/classroom.group-seating-studio",
            "/public/apps/unknown-app",
            "/this-route-should-not-exist",
            "/anything/not/owned",
        ],
    )
    def test_non_spa_paths_should_not_serve_spa(self, path: str) -> None:
        assert _should_serve_spa(path) is False


@pytest.mark.unit
class TestCrawlerRoutes:
    """Test backend-owned crawler resources."""

    def test_robots_txt_returns_real_crawler_policy(self, client: TestClient) -> None:
        response = client.get("/robots.txt")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        assert response.text == (
            "User-agent: *\nAllow: /\nSitemap: https://skriptoteket.hule.education/sitemap.xml\n"
        )
        assert "<!doctype html>" not in response.text.lower()

    def test_sitemap_xml_returns_only_approved_public_urls(self, client: TestClient) -> None:
        response = client.get("/sitemap.xml")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/xml")
        assert "<urlset" in response.text
        assert "<loc>https://skriptoteket.hule.education/</loc>" in response.text
        assert (
            "<loc>https://skriptoteket.hule.education/"
            "public/apps/classroom.group-seating-studio</loc>"
        ) in response.text
        assert (
            "<loc>https://skriptoteket.hule.education/apps/classroom.group-seating-studio</loc>"
            not in response.text
        )
        assert "/admin/tools" not in response.text
        assert "<!doctype html>" not in response.text.lower()


@pytest.mark.unit
class TestSpaFallbackResponses:
    """Test route-family status semantics for direct URL fetches."""

    @pytest.mark.parametrize(
        "path",
        [
            "/",
            "/public/apps/classroom.group-seating-studio",
            "/public/apps/documents.conversion_hub/exam-converter",
            "/auth/login",
            "/auth/callback",
            "/apps/classroom.group-seating-studio",
            "/browse/professions/matematik",
            "/editor",
            "/admin/tools",
        ],
    )
    def test_valid_spa_routes_return_spa_shell(self, client: TestClient, path: str) -> None:
        response = client.get(path)

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert "<!doctype html>" in response.text.lower()
        assert '<div id="app"></div>' in response.text

    def test_home_route_returns_public_initial_html_metadata(self, client: TestClient) -> None:
        response = client.get("/")

        assert response.status_code == 200
        _assert_public_metadata(
            response.text,
            title=HOME_TITLE,
            description=HOME_DESCRIPTION,
            canonical_url="https://skriptoteket.hule.education/",
        )

    def test_public_app_route_returns_unique_initial_html_metadata(
        self,
        client: TestClient,
    ) -> None:
        response = client.get(PUBLIC_APP_PATH)

        assert response.status_code == 200
        _assert_public_metadata(
            response.text,
            title=PUBLIC_APP_TITLE,
            description=PUBLIC_APP_DESCRIPTION,
            canonical_url=f"https://skriptoteket.hule.education{PUBLIC_APP_PATH}",
        )

    @pytest.mark.parametrize(
        "path",
        [
            "/auth/login",
            "/apps/classroom.group-seating-studio",
            "/editor",
            "/admin/tools",
        ],
    )
    def test_private_spa_routes_return_non_indexable_initial_html(
        self,
        client: TestClient,
        path: str,
    ) -> None:
        response = client.get(path)

        assert response.status_code == 200
        assert '<div id="app"></div>' in response.text
        _assert_meta_name(response.text, "robots", "noindex,follow")
        assert 'rel="canonical"' not in response.text
        assert 'property="og:url"' not in response.text

    @pytest.mark.parametrize(
        "path",
        [
            "/public/apps",
            "/public/classroom.group-seating-studio",
            "/public/apps/unknown-app",
            "/this-route-should-not-exist",
            "/anything/not/owned",
        ],
    )
    def test_malformed_and_unknown_routes_return_honest_404(
        self,
        client: TestClient,
        path: str,
    ) -> None:
        response = client.get(path)

        assert response.status_code == 404
        assert "<!doctype html>" in response.text.lower()
        assert "<body>Not Found</body>" in response.text
        _assert_meta_name(response.text, "robots", "noindex,nofollow")
        assert '<div id="app"></div>' not in response.text
