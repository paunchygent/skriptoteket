from __future__ import annotations

import argparse
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import sync_playwright

from scripts.playwright_ui_smoke import _launch_chromium


@dataclass
class HmrProbeResult:
    css_expected: bool
    vue_expected: bool
    css_observed: bool
    vue_observed: bool
    notes: list[str]


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


def _set_playwright_host_override(dotenv_path: Path) -> None:
    if os.environ.get("PLAYWRIGHT_HOST_PLATFORM_OVERRIDE"):
        return

    dotenv = _read_dotenv(dotenv_path)
    override = dotenv.get("PLAYWRIGHT_HOST_PLATFORM_OVERRIDE")
    if override:
        os.environ["PLAYWRIGHT_HOST_PLATFORM_OVERRIDE"] = override


def _tail_file(path: Path, *, max_lines: int) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        return ""
    if max_lines <= 0:
        return "\n".join(lines)
    return "\n".join(lines[-max_lines:])


def _capture_container_logs(*, seconds: int, max_lines: int) -> str:
    cmd = [
        "docker",
        "compose",
        "-f",
        "compose.yaml",
        "-f",
        "compose.dev.yaml",
        "logs",
        "--since",
        f"{seconds}s",
        "frontend",
    ]
    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return ""

    output = (result.stdout or "") + (result.stderr or "")
    if not output:
        return ""
    lines = output.splitlines()
    if max_lines <= 0:
        return "\n".join(lines)
    return "\n".join(lines[-max_lines:])


def _capture_vite_logs(
    *,
    log_source: str,
    local_log_path: Path,
    seconds: int,
    max_lines: int,
    notes: list[str],
) -> str:
    if log_source == "none":
        return ""

    if log_source in {"auto", "local"}:
        if local_log_path.exists():
            return _tail_file(local_log_path, max_lines=max_lines)
        if log_source == "local":
            notes.append(f"Local log file not found: {local_log_path}")

    if log_source in {"auto", "containers"}:
        container_logs = _capture_container_logs(seconds=seconds, max_lines=max_lines)
        if container_logs:
            return container_logs
        if log_source == "containers":
            notes.append("Failed to read container logs (docker compose logs).")

    return ""


def _write_artifact(path: Path, content: str) -> None:
    if not content:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_if_changed(path: Path, *, original: str, updated: str) -> None:
    if updated == original:
        return
    path.write_text(updated, encoding="utf-8")


def _restore_file(path: Path, *, original: str) -> None:
    path.write_text(original, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Playwright HMR probe for Vite dev server.")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("VITE_DEV_URL") or "http://127.0.0.1:5173",
        help="Vite dev server URL (default: http://127.0.0.1:5173).",
    )
    parser.add_argument(
        "--dotenv",
        default=os.environ.get("DOTENV_PATH") or ".env",
        help="Dotenv path for PLAYWRIGHT_HOST_PLATFORM_OVERRIDE (default: .env).",
    )
    parser.add_argument(
        "--log-source",
        choices=("auto", "local", "containers", "none"),
        default="auto",
        help="Where to capture Vite server logs from.",
    )
    parser.add_argument(
        "--local-log-path",
        default=".artifacts/dev-frontend.log",
        help="Local Vite log file (default: .artifacts/dev-frontend.log).",
    )
    parser.add_argument(
        "--log-seconds",
        type=int,
        default=120,
        help="How far back to fetch container logs in seconds (default: 120).",
    )
    parser.add_argument(
        "--log-lines",
        type=int,
        default=200,
        help="Max lines to include from Vite logs (default: 200).",
    )
    parser.add_argument(
        "--wait-ms",
        type=int,
        default=8000,
        help="Milliseconds to wait after each file change (default: 8000).",
    )
    parser.add_argument(
        "--artifacts-dir",
        default=".artifacts/hmr-probe",
        help="Artifacts output directory (default: .artifacts/hmr-probe).",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    artifacts_dir = Path(args.artifacts_dir)
    local_log_path = Path(args.local_log_path)
    notes: list[str] = []

    _set_playwright_host_override(Path(args.dotenv))

    css_path = Path("frontend/apps/skriptoteket/src/assets/main.css")
    vue_path = Path("frontend/apps/skriptoteket/src/App.vue")

    css_original = css_path.read_text(encoding="utf-8")
    vue_original = vue_path.read_text(encoding="utf-8")

    css_marker = "\n/* hmr-probe */\n"
    css_updated = css_original + css_marker

    vue_needle = '<div class="app-layout min-h-screen text-navy">'
    vue_replacement = '<div class="app-layout min-h-screen text-navy" data-hmr-probe="1">'
    if vue_needle in vue_original:
        vue_updated = vue_original.replace(vue_needle, vue_replacement)
        vue_expected = True
    else:
        vue_updated = vue_original
        vue_expected = False
        notes.append("App.vue root element not found; skipping Vue HMR probe.")

    console_lines: list[str] = []

    def on_console(msg: object) -> None:
        line = f"{msg.type}:{msg.text}"
        console_lines.append(line)
        print(f"console:{line}")

    def on_page_error(error: object) -> None:
        console_lines.append(f"pageerror:{error}")
        print(f"pageerror:{error}")

    try:
        with sync_playwright() as playwright:
            browser = _launch_chromium(playwright)
            page = browser.new_page()
            page.on("console", on_console)
            page.on("pageerror", on_page_error)

            page.goto(base_url, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            _write_if_changed(css_path, original=css_original, updated=css_updated)
            page.wait_for_timeout(args.wait_ms)

            if vue_expected:
                _write_if_changed(vue_path, original=vue_original, updated=vue_updated)
                page.wait_for_timeout(args.wait_ms)

            _restore_file(vue_path, original=vue_original)
            _restore_file(css_path, original=css_original)
            page.wait_for_timeout(args.wait_ms)

            browser.close()
    finally:
        # Ensure original content is restored even if Playwright crashes.
        _restore_file(vue_path, original=vue_original)
        _restore_file(css_path, original=css_original)

    console_text = "\n".join(console_lines)
    _write_artifact(artifacts_dir / "browser-console.txt", console_text)

    vite_logs = _capture_vite_logs(
        log_source=args.log_source,
        local_log_path=local_log_path,
        seconds=args.log_seconds,
        max_lines=args.log_lines,
        notes=notes,
    )
    _write_artifact(artifacts_dir / "vite-logs.txt", vite_logs)

    css_observed = "hot updated: /src/assets/main.css" in console_text
    vue_observed = "hot updated: /src/App.vue" in console_text

    result = HmrProbeResult(
        css_expected=True,
        vue_expected=vue_expected,
        css_observed=css_observed,
        vue_observed=vue_observed if vue_expected else True,
        notes=notes,
    )

    summary_lines = [
        f"base_url: {base_url}",
        f"css_expected: {result.css_expected}",
        f"css_observed: {result.css_observed}",
        f"vue_expected: {result.vue_expected}",
        f"vue_observed: {result.vue_observed}",
    ]
    if notes:
        summary_lines.append("notes:")
        summary_lines.extend([f"- {note}" for note in notes])
    summary = "\n".join(summary_lines)
    _write_artifact(artifacts_dir / "summary.txt", summary)

    print(summary)

    if not result.css_observed or (result.vue_expected and not result.vue_observed):
        raise SystemExit("HMR probe failed; see .artifacts/hmr-probe/ for details.")


if __name__ == "__main__":
    main()
