from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

from scripts.playwright_ui_smoke import _launch_chromium
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.hazards_store import (
    InMemoryReagentPrepChefHazardStore,
)


@dataclass(frozen=True)
class Target:
    cid: int
    key: str | None
    display_name: str | None


def _artifact_root() -> Path:
    env = os.environ.get("ARTIFACTS_ROOT")
    if env:
        return Path(env)
    return Path(".artifacts")


def _hazards_path() -> Path:
    from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef import hazards_store

    return Path(hazards_store.__file__).with_name("hazards.json")


def _select_targets(*, cids: list[int], hazards: list[str]) -> list[Target]:
    targets: list[Target] = []
    for cid in cids:
        targets.append(Target(cid=cid, key=None, display_name=None))

    if hazards:
        store = InMemoryReagentPrepChefHazardStore(hazards_path=_hazards_path())
        hazards_by_key = {hazard.key: hazard for hazard in store.list_all()}
        for key in hazards:
            hazard = hazards_by_key.get(key)
            if hazard is None:
                raise SystemExit(f"Unknown hazard key: {key}")
            if hazard.pubchem_cid is None:
                raise SystemExit(f"Hazard {key} saknar pubchem_cid.")
            targets.append(
                Target(
                    cid=hazard.pubchem_cid,
                    key=hazard.key,
                    display_name=hazard.display_name,
                )
            )

    seen: set[int] = set()
    deduped: list[Target] = []
    for target in targets:
        if target.cid in seen:
            continue
        seen.add(target.cid)
        deduped.append(target)
    return deduped


def _compound_url(cid: int) -> str:
    return f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"


def _is_candidate(url: str, text: str, title: str) -> dict | None:
    if not url:
        return None
    lowered = url.lower()
    text_lower = text.lower()
    title_lower = title.lower()
    tokens = ("sds", "msds", "safety data sheet", "safety-data-sheet")
    is_pdf = lowered.endswith(".pdf") or "format=pdf" in lowered
    is_sds = any(token in lowered for token in tokens) or any(
        token in text_lower or token in title_lower for token in tokens
    )
    if not (is_pdf or is_sds):
        return None
    return {
        "url": url,
        "text": text,
        "title": title,
        "is_pdf": is_pdf,
        "is_sds": is_sds,
    }


def _scan_page(*, page, cid: int, timeout_ms: int) -> list[dict]:
    page.goto(_compound_url(cid), wait_until="domcontentloaded", timeout=timeout_ms)
    page.wait_for_timeout(1500)

    try:
        toc_link = page.get_by_role("link", name=re.compile(r"Safety and Hazards", re.I))
        if toc_link.count() > 0:
            toc_link.first.click()
            page.wait_for_timeout(500)
    except Exception:
        pass

    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(1000)

    links = page.evaluate(
        """() => Array.from(document.querySelectorAll('a[href]')).map(a => ({
            href: a.href || '',
            text: (a.textContent || '').trim(),
            title: a.getAttribute('title') || ''
        }))"""
    )

    seen: set[str] = set()
    candidates: list[dict] = []
    for link in links:
        url = str(link.get("href") or "")
        text = str(link.get("text") or "")
        title = str(link.get("title") or "")
        if not (url.startswith("http://") or url.startswith("https://")):
            continue
        candidate = _is_candidate(url, text, title)
        if not candidate:
            continue
        if url in seen:
            continue
        seen.add(url)
        candidates.append(candidate)
    return candidates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cid", action="append", type=int, default=[], help="PubChem CID.")
    parser.add_argument("--hazard", action="append", default=[], help="Hazard key.")
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=20000,
        help="Timeout per page (milliseconds).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".artifacts/sds-linkout-scan/report.json"),
        help="Write aggregated JSON report here.",
    )
    args = parser.parse_args()

    targets = _select_targets(cids=args.cid, hazards=args.hazard)
    if not targets:
        raise SystemExit("No targets provided.")

    artifacts_dir = _artifact_root() / "sds-linkout-scan"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        for target in targets:
            print(
                f"[scan_start] cid={target.cid} hazard={target.key or '-'} "
                f"display_name={target.display_name or '-'}",
                flush=True,
            )
            candidates = _scan_page(page=page, cid=target.cid, timeout_ms=args.timeout_ms)
            screenshot_path = artifacts_dir / f"{target.cid}.png"
            page.screenshot(path=str(screenshot_path), full_page=True)
            html_path = artifacts_dir / f"{target.cid}.html"
            html_path.write_text(page.content(), encoding="utf-8")
            record = {
                "cid": target.cid,
                "hazard_key": target.key,
                "display_name": target.display_name,
                "compound_url": _compound_url(target.cid),
                "captured_at": datetime.now(tz=timezone.utc).isoformat(),
                "candidates": candidates,
                "screenshot": str(screenshot_path),
                "html": str(html_path),
            }
            results.append(record)
            print(
                f"[scan_done] cid={target.cid} candidates={len(candidates)}",
                flush=True,
            )

        context.close()
        browser.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "results": results,
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote report: {args.output}", flush=True)


if __name__ == "__main__":
    main()
