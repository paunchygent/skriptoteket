"""Local Playwright proof for the approved Exam Converter review UI."""

from __future__ import annotations

import os
from datetime import UTC, datetime

from playwright.sync_api import sync_playwright

from scripts._exam_converter_design_proof import (
    JsonObject,
    prove_review_routing_journey,
    run_dir,
    write_manifest,
)
from scripts._playwright_browser import launch_chromium


def main() -> int:
    """Exercise desktop and phone review states through the local Vite graph."""
    artifact_dir = run_dir()
    base_url = os.environ.get("EXAM_CONVERTER_DESIGN_BASE_URL", "http://127.0.0.1:5173")
    manifest: JsonObject = {
        "artifact_dir": str(artifact_dir),
        "base_url": base_url,
        "command": "pdm run python -m scripts._exam_converter_review_ui_local_proof",
        "fixture": "local-vite-module-graph",
        "status": "running",
        "timestamp_utc": datetime.now(UTC).isoformat(),
    }
    write_manifest(artifact_dir, manifest)
    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(base_url=base_url)
        page = context.new_page()
        page.set_default_timeout(60_000)
        try:
            manifest["captures"] = prove_review_routing_journey(page, artifact_dir)
            manifest["status"] = "ok"
            write_manifest(artifact_dir, manifest)
        except Exception as exc:
            manifest["error"] = f"{type(exc).__name__}: {exc}"
            manifest["status"] = "failed"
            write_manifest(artifact_dir, manifest)
            raise
        finally:
            context.close()
            browser.close()
    print(f"exam-converter-review-ui-local-proof: ok artifact_dir={artifact_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
