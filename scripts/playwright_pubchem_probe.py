from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

from playwright.sync_api import sync_playwright

from scripts.playwright_hmr_probe import _read_dotenv
from scripts.playwright_ui_smoke import _launch_chromium
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.hazards_store import (
    InMemoryReagentPrepChefHazardStore,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_index_store import (
    FileSystemReagentPrepChefSdsIndexStore,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_query_variants import (
    dedupe_preserve_order,
    looks_like_formula,
    normalize_formula_variants,
)


@dataclass
class Target:
    key: str
    display_name: str


class _NoopFetcher:
    async def fetch(self, *, hazard: object) -> object:  # pragma: no cover - script-only
        raise RuntimeError("Fetcher should not be called in probe script.")


def _hazards_path() -> Path:
    from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef import hazards_store

    return Path(hazards_store.__file__).with_name("hazards.json")


def _artifact_root() -> Path:
    env = os.environ.get("ARTIFACTS_ROOT")
    if env:
        return Path(env)
    return Path(".artifacts")


def _apply_playwright_host_override(dotenv_path: Path) -> None:
    if os.environ.get("PLAYWRIGHT_HOST_PLATFORM_OVERRIDE"):
        return
    dotenv = _read_dotenv(dotenv_path)
    override = dotenv.get("PLAYWRIGHT_HOST_PLATFORM_OVERRIDE")
    if override:
        os.environ["PLAYWRIGHT_HOST_PLATFORM_OVERRIDE"] = override


def _select_targets(
    *,
    only: list[str],
    only_missing: bool,
    sample: int | None,
    sample_seed: int,
) -> list[Target]:
    hazards_store = InMemoryReagentPrepChefHazardStore(hazards_path=_hazards_path())
    hazards = hazards_store.list_all()

    if only:
        allowed = {value.strip() for value in only if value.strip()}
        hazards = [hazard for hazard in hazards if hazard.key in allowed]

    cache_root = _artifact_root() / "sds-cache"
    index = FileSystemReagentPrepChefSdsIndexStore(
        cache_root=cache_root,
        fetcher=_NoopFetcher(),
    )
    if only_missing:
        hazards = [hazard for hazard in hazards if not index.is_cached_complete(hazard=hazard)]

    if sample is not None and sample < len(hazards):
        import random

        rng = random.Random(sample_seed)
        hazards = rng.sample(hazards, sample)

    return [Target(key=hazard.key, display_name=hazard.display_name) for hazard in hazards]


def _build_url(query: str) -> str:
    return f"https://pubchem.ncbi.nlm.nih.gov/compound/{quote(query)}"


def _build_queries(target: Target, aliases: list[str], overrides: list[str]) -> list[str]:
    base_queries = [*overrides, target.key, *aliases]
    expanded: list[str] = []
    for query in base_queries:
        if looks_like_formula(query):
            expanded.extend(normalize_formula_variants(query))
    return dedupe_preserve_order([value for value in [*base_queries, *expanded] if value])


def _safe_filename(value: str) -> str:
    return "".join(char if char.isalnum() or char in "-_" else "_" for char in value)


def _capture_pubchem_page(
    *,
    page,
    target: Target,
    query: str,
    output_dir: Path,
    timeout_ms: int,
) -> dict[str, Any]:
    url = _build_url(query)
    responses: list[dict[str, Any]] = []
    stored_files: list[dict[str, str]] = []

    def handle_response(response) -> None:
        response_url = response.url
        if "pubchem.ncbi.nlm.nih.gov/rest/" not in response_url:
            return
        content_type = response.headers.get("content-type", "")
        entry = {
            "url": response_url,
            "status": response.status,
            "content_type": content_type,
        }
        if "application/json" in content_type:
            try:
                body_text = response.text()
            except Exception:
                body_text = None
            if body_text:
                file_name = (
                    f"{_safe_filename(target.key)}_{_safe_filename(query)[:24]}"
                    f"_{len(stored_files) + 1}.json"
                )
                file_path = output_dir / file_name
                file_path.write_text(body_text, encoding="utf-8")
                stored_files.append(
                    {
                        "url": response_url,
                        "path": str(file_path),
                    }
                )
        responses.append(entry)

    page.on("response", handle_response)
    page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
    page.wait_for_timeout(4000)
    title = page.title()
    headings = page.eval_on_selector_all(
        "h1,h2,h3",
        "els => els.map(el => el.textContent || '').map(t => t.trim()).filter(Boolean)",
    )
    lower_headings = [heading.lower() for heading in headings]
    is_not_found = "404 - page not found" in lower_headings or "404: not found" in title.lower()
    safety_headings = [
        heading
        for heading in headings
        if "safety" in heading.lower() or "hazard" in heading.lower()
    ]
    screenshot_path = output_dir / f"{_safe_filename(target.key)}_{_safe_filename(query)[:24]}.png"
    page.screenshot(path=screenshot_path, full_page=True)
    page.remove_listener("response", handle_response)

    return {
        "target": {"key": target.key, "display_name": target.display_name},
        "query": query,
        "url": url,
        "title": title,
        "headings": headings,
        "safety_headings": safety_headings,
        "not_found": is_not_found,
        "responses": responses,
        "stored_json": stored_files,
        "screenshot": str(screenshot_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dotenv",
        default=os.environ.get("DOTENV_PATH") or ".env",
        help="Dotenv file to read defaults from (default: DOTENV_PATH env var or .env)",
    )
    parser.add_argument(
        "--query",
        action="append",
        default=[],
        help="Custom query override in the form KEY=QUERY (repeatable).",
    )
    parser.add_argument("--only", action="append", default=[], help="Hazard keys to probe.")
    parser.add_argument("--only-missing", action="store_true", help="Skip cached hazards.")
    parser.add_argument("--sample", type=int, default=None, help="Sample size.")
    parser.add_argument("--sample-seed", type=int, default=42)
    parser.add_argument("--timeout-ms", type=int, default=20000)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_artifact_root() / "pubchem-probe",
    )
    args = parser.parse_args()
    _apply_playwright_host_override(Path(args.dotenv))

    query_overrides: dict[str, list[str]] = {}
    for raw in args.query:
        if "=" not in raw:
            raise SystemExit("Invalid --query value. Use KEY=QUERY.")
        key, query = raw.split("=", 1)
        key = key.strip()
        query = query.strip()
        if not key or not query:
            raise SystemExit("Invalid --query value. Use KEY=QUERY.")
        query_overrides.setdefault(key, []).append(query)

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    targets = _select_targets(
        only=args.only,
        only_missing=args.only_missing,
        sample=args.sample,
        sample_seed=args.sample_seed,
    )
    if not targets:
        print("No targets selected.")
        return

    hazards_store = InMemoryReagentPrepChefHazardStore(hazards_path=_hazards_path())
    hazards_by_key = {hazard.key: hazard for hazard in hazards_store.list_all()}

    with sync_playwright() as p:
        browser = _launch_chromium(p)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        results: list[dict[str, Any]] = []
        for target in targets:
            aliases: list[str] = []
            hazard = hazards_by_key.get(target.key)
            if hazard is not None:
                aliases = list(hazard.aliases)
            overrides = query_overrides.get(target.key, [])
            queries = _build_queries(target, aliases, overrides)
            attempts: list[dict[str, Any]] = []
            selected: dict[str, Any] | None = None
            for query in queries:
                attempt = _capture_pubchem_page(
                    page=page,
                    target=target,
                    query=query,
                    output_dir=output_dir,
                    timeout_ms=args.timeout_ms,
                )
                attempts.append(attempt)
                if not attempt["not_found"]:
                    selected = attempt
                    break
            results.append(
                {
                    "target": target.__dict__,
                    "queries": queries,
                    "selected": selected,
                    "attempts": attempts,
                }
            )
        browser.close()

    report = {
        "targets": [target.__dict__ for target in targets],
        "results": results,
    }
    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote report: {report_path}")


if __name__ == "__main__":
    main()
