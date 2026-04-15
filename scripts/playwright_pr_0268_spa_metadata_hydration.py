"""PR-0268 browser proof for SPA metadata hydration stability.

Purpose:
    Prove that backend-injected launch metadata for the public Skriptoteket
    SPA routes remains intact after the Vue app hydrates in a real browser.

Relationships:
    - Starts a temporary ASGI app that serves static SPA assets and the
      `skriptoteket.web.routes.spa_fallback` router.
    - Complements backend initial-HTML tests in `tests/unit/web/test_spa_fallback.py`.
"""

from __future__ import annotations

import socket
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from playwright.sync_api import Page, sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from skriptoteket.web.routes import spa_fallback  # noqa: E402

PUBLIC_BASE_URL = "https://skriptoteket.hule.education"
STATIC_DIR = SRC_ROOT / "skriptoteket" / "web" / "static"
SYSTEM_CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


@dataclass(frozen=True, slots=True)
class ExpectedHead:
    """Expected hydrated document head values for one public route."""

    path: str
    title: str
    description: str
    canonical_url: str


EXPECTED_PUBLIC_HEADS = (
    ExpectedHead(
        path="/",
        title="Skriptoteket | Lektionsplanering direkt i webbläsaren",
        description=(
            "Skriptoteket samlar lärarverktyg och öppna appar som Klassrumskartan "
            "för planering direkt i webbläsaren."
        ),
        canonical_url=f"{PUBLIC_BASE_URL}/",
    ),
    ExpectedHead(
        path="/public/apps/classroom.group-seating-studio",
        title="Klassrumskartan | Skriptoteket",
        description=(
            "Planera grupper och placeringar direkt i webbläsaren med Klassrumskartan, "
            "en öppen app i Skriptoteket."
        ),
        canonical_url=f"{PUBLIC_BASE_URL}/public/apps/classroom.group-seating-studio",
    ),
)


def main() -> None:
    """Run the PR-0268 browser metadata proof."""
    port = _free_port()
    app = _build_app()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"

    try:
        _wait_for_server(base_url)
        _check_hydrated_heads(base_url)
    finally:
        server.should_exit = True
        thread.join(timeout=5)

    print("playwright-pr-0268-spa-metadata-hydration: ok")


def _build_app() -> FastAPI:
    """Create the minimal ASGI app needed for the metadata proof."""
    app = FastAPI()
    app.state.public_app_base_url = PUBLIC_BASE_URL
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.include_router(spa_fallback.router)
    return app


def _free_port() -> int:
    """Reserve a free loopback port for the temporary ASGI app."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_server(base_url: str) -> None:
    """Wait until the temporary ASGI app accepts HTTP requests."""
    last_error: Exception | None = None
    for _ in range(100):
        try:
            with urlopen(base_url, timeout=0.25) as response:
                if response.status == 200:
                    return
        except (OSError, URLError) as exc:
            last_error = exc
            time.sleep(0.05)
    raise RuntimeError(f"Temporary metadata server did not become ready: {last_error}")


def _check_hydrated_heads(base_url: str) -> None:
    """Open the public routes and assert hydrated document head values."""
    launch_options: dict[str, object] = {"headless": True}
    if SYSTEM_CHROME.exists():
        launch_options["executable_path"] = str(SYSTEM_CHROME)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**launch_options)
        page = browser.new_page()
        try:
            for expected in EXPECTED_PUBLIC_HEADS:
                _check_route(page=page, base_url=base_url, expected=expected)
        finally:
            browser.close()


def _check_route(*, page: Page, base_url: str, expected: ExpectedHead) -> None:
    """Assert one route keeps its backend metadata after Vue hydration."""
    page.goto(f"{base_url}{expected.path}", wait_until="load")
    page.wait_for_selector("#app", timeout=10_000)
    page.wait_for_function(
        """() => {
            const app = document.querySelector("#app");
            return app?.hasAttribute("data-v-app") || (app?.innerHTML || "").length > 0;
        }""",
        timeout=10_000,
    )

    head = page.evaluate(
        """() => ({
            title: document.title,
            description: document.querySelector('meta[name="description"]')?.content ?? null,
            robots: document.querySelector('meta[name="robots"]')?.content ?? null,
            canonical: document.querySelector('link[rel="canonical"]')?.href ?? null,
            ogTitle: document.querySelector('meta[property="og:title"]')?.content ?? null,
            ogDescription: document.querySelector('meta[property="og:description"]')?.content ?? null,
            ogUrl: document.querySelector('meta[property="og:url"]')?.content ?? null,
            ogType: document.querySelector('meta[property="og:type"]')?.content ?? null,
            twitterCard: document.querySelector('meta[name="twitter:card"]')?.content ?? null,
            twitterTitle: document.querySelector('meta[name="twitter:title"]')?.content ?? null,
            twitterDescription:
                document.querySelector('meta[name="twitter:description"]')?.content ?? null,
        })"""
    )

    assert head["title"] == expected.title
    assert head["description"] == expected.description
    assert head["robots"] == "index,follow"
    assert head["canonical"] == expected.canonical_url
    assert head["ogTitle"] == expected.title
    assert head["ogDescription"] == expected.description
    assert head["ogUrl"] == expected.canonical_url
    assert head["ogType"] == "website"
    assert head["twitterCard"] == "summary"
    assert head["twitterTitle"] == expected.title
    assert head["twitterDescription"] == expected.description


if __name__ == "__main__":
    main()
