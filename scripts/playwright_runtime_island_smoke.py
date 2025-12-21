from __future__ import annotations

import os
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def _read_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _get_config_value(*, key: str, dotenv: dict[str, str]) -> str | None:
    return os.environ.get(key) or dotenv.get(key)


def _extract_counter(*, runtime_text: str) -> int:
    match = re.search(r"Räknare:\s*(-?\d+)", runtime_text)
    if not match:
        raise RuntimeError(f"Could not find 'Räknare: <int>' in runtime text: {runtime_text!r}")
    return int(match.group(1))


def main() -> None:
    dotenv = _read_dotenv(Path(".env"))

    base_url = _get_config_value(key="BASE_URL", dotenv=dotenv) or "http://127.0.0.1:8000"
    email = _get_config_value(key="BOOTSTRAP_SUPERUSER_EMAIL", dotenv=dotenv)
    password = _get_config_value(key="BOOTSTRAP_SUPERUSER_PASSWORD", dotenv=dotenv)

    if not email or not password:
        raise SystemExit(
            "Missing BOOTSTRAP_SUPERUSER_EMAIL/BOOTSTRAP_SUPERUSER_PASSWORD. "
            "Set them in .env (gitignored) or export them in your shell."
        )

    artifacts_dir = Path(".artifacts/ui-runtime-smoke")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    sample_csv_path = artifacts_dir / "sample.csv"
    sample_csv_path.write_text(
        "Vårdnadshavare e-post\nparent@example.com\n",
        encoding="utf-8",
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})

        page1 = context.new_page()

        # Login (bootstrap account from .env)
        page1.goto(f"{base_url}/login", wait_until="domcontentloaded")
        page1.get_by_label("E-post").fill(email)
        page1.get_by_label("Lösenord").fill(password)
        page1.get_by_role("button", name="Logga in").click()
        expect(page1.get_by_text("Inloggad som")).to_be_visible()

        # Curated app that produces ui_payload.next_actions (demo.counter)
        page1.goto(f"{base_url}/apps/demo.counter", wait_until="domcontentloaded")
        expect(page1.get_by_role("heading", name=re.compile("Interaktiv.*räknare"))).to_be_visible()

        page1.get_by_role("button", name="Starta").click()
        runtime1 = page1.locator("[data-spa-runtime='true']").first
        expect(runtime1).to_be_visible()
        expect(page1.locator("[data-spa-runtime-fallback='true']")).to_be_hidden()
        expect(runtime1.get_by_role("button", name="Öka")).to_be_visible()

        run_id = runtime1.get_attribute("data-run-id")
        if not run_id:
            raise RuntimeError("Could not determine run_id from runtime island root.")

        # Open a second tab in the same context to create a state_rev conflict
        page2 = context.new_page()
        page2.goto(f"{base_url}/apps/demo.counter", wait_until="domcontentloaded")
        runtime2 = page2.locator("[data-spa-runtime='true']").first
        expect(runtime2).to_be_visible()
        expect(page2.locator("[data-spa-runtime-fallback='true']")).to_be_hidden()
        expect(runtime2.get_by_role("button", name="Öka")).to_be_visible()

        step_field_2 = (
            runtime2.get_by_role("spinbutton", name="Steg")
            .first
        )
        initial_count_2 = _extract_counter(runtime_text=runtime2.inner_text())
        step_field_2.fill("1")
        runtime2.get_by_role("button", name="Öka").click()
        expect(runtime2).to_contain_text(re.compile(rf"Räknare:\s*{initial_count_2 + 1}(?!\d)"))

        # Page1 now has stale expected_state_rev and should show a concurrency error + refresh path.
        step_field_1 = (
            runtime1.get_by_role("spinbutton", name="Steg")
            .first
        )
        step_field_1.fill("1")
        runtime1.get_by_role("button", name="Öka").click()
        expect(runtime1).to_contain_text(
            "Din session har ändrats i en annan flik."
        )
        expect(runtime1.get_by_role("button", name="Uppdatera")).to_be_visible()

        runtime1.get_by_role("button", name="Uppdatera").click()
        expect(runtime1.get_by_role("button", name="Öka")).to_be_visible()

        initial_count_1 = _extract_counter(runtime_text=runtime1.inner_text())
        step_field_1.fill("1")
        runtime1.get_by_role("button", name="Öka").click()
        expect(runtime1).to_contain_text(re.compile(rf"Räknare:\s*{initial_count_1 + 1}(?!\d)"))

        page1.goto(f"{base_url}/my-runs/{run_id}", wait_until="domcontentloaded")
        runtime_my_run = page1.locator("[data-spa-runtime='true']").first
        expect(runtime_my_run).to_be_visible()
        expect(runtime_my_run.get_by_role("button", name="Öka")).to_be_visible()
        page1.screenshot(path=str(artifacts_dir / "runtime.png"), full_page=True)

        # Tool run page (/tools/<slug>/run): HTMX injects run_result, runtime island must mount.
        tool_slug = "ist-vh-mejl-bcc"
        response = page1.goto(
            f"{base_url}/tools/{tool_slug}/run",
            wait_until="domcontentloaded",
        )
        if response is None or response.status != 200:
            raise RuntimeError(
                f"Tool run page did not load for slug {tool_slug!r}. "
                "Ensure the script-bank tools are seeded and published (pdm run seed-script-bank)."
            )

        page1.locator("input#file").set_input_files(str(sample_csv_path))
        page1.get_by_role("button", name="Kör").click()

        runtime_tool_run = page1.locator("#result-container [data-spa-runtime='true']").first
        expect(runtime_tool_run).to_be_visible(timeout=60_000)
        expect(page1.locator("#result-container [data-spa-runtime-fallback='true']")).to_be_hidden(
            timeout=10_000
        )
        expect(runtime_tool_run).to_contain_text(re.compile(r"(Lyckades|Misslyckades|Pågår|Tidsgräns)"))
        expect(runtime_tool_run).to_contain_text("Resultat")
        page1.screenshot(path=str(artifacts_dir / "tool-run.png"), full_page=True)

        context.close()
        browser.close()

    print(f"Playwright runtime island screenshot written to: {artifacts_dir}")


if __name__ == "__main__":
    main()
