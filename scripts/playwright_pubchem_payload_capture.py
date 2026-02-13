from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from scripts.playwright_hmr_probe import _read_dotenv
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


def _data_root() -> Path:
    return Path("data/pubchem_payloads/raw")


def _apply_playwright_host_override(dotenv_path: Path) -> None:
    if os.environ.get("PLAYWRIGHT_HOST_PLATFORM_OVERRIDE"):
        return
    dotenv = _read_dotenv(dotenv_path)
    override = dotenv.get("PLAYWRIGHT_HOST_PLATFORM_OVERRIDE")
    if override:
        os.environ["PLAYWRIGHT_HOST_PLATFORM_OVERRIDE"] = override


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


def _endpoint_urls(cid: int) -> dict[str, str]:
    base = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound"
    return {
        "linkout": f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/linkout/compound/{cid}/JSON",
        "lcss": f"{base}/{cid}/JSON?toc=LCSS%20TOC",
        "safety": f"{base}/{cid}/JSON?heading=Safety%20and%20Hazards",
    }


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_payload(
    *,
    output_dir: Path,
    name: str,
    url: str,
    response,
) -> dict[str, Any]:
    status = response.status
    content_type = response.headers.get("content-type", "")
    body = response.body()
    entry: dict[str, Any] = {
        "url": url,
        "status": status,
        "content_type": content_type,
        "bytes": len(body),
    }
    if status == 200 and "application/json" in content_type:
        file_path = output_dir / f"{name}.json"
        file_path.write_bytes(body)
        entry["file"] = str(file_path)
        entry["sha256"] = _sha256(body)
    return entry


def _capture(
    *,
    page,
    request,
    target: Target,
    output_dir: Path,
    artifacts_dir: Path,
    timeout_ms: int,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    compound_url = _compound_url(target.cid)
    page.goto(compound_url, wait_until="domcontentloaded", timeout=timeout_ms)
    page.wait_for_timeout(3000)
    screenshot_path = artifacts_dir / f"{target.cid}.png"
    page.screenshot(path=screenshot_path, full_page=True)

    endpoints = _endpoint_urls(target.cid)
    payload_meta: dict[str, Any] = {}
    for name, url in endpoints.items():
        response = request.get(url, timeout=timeout_ms)
        payload_meta[name] = _write_payload(
            output_dir=output_dir,
            name=name,
            url=url,
            response=response,
        )

    meta = {
        "cid": target.cid,
        "hazard_key": target.key,
        "display_name": target.display_name,
        "captured_at": datetime.now(tz=timezone.utc).isoformat(),
        "compound_url": compound_url,
        "payloads": payload_meta,
        "screenshot": str(screenshot_path),
    }
    meta_path = output_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dotenv",
        default=os.environ.get("DOTENV_PATH") or ".env",
        help="Dotenv file to read defaults from (default: DOTENV_PATH env var or .env).",
    )
    parser.add_argument("--cid", action="append", type=int, default=[], help="PubChem CID.")
    parser.add_argument("--hazard", action="append", default=[], help="Hazard key.")
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=20000,
        help="Timeout per request (milliseconds).",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip CIDs that already have meta.json.",
    )
    args = parser.parse_args()
    _apply_playwright_host_override(Path(args.dotenv))

    targets = _select_targets(cids=args.cid, hazards=args.hazard)
    if not targets:
        raise SystemExit("No targets provided.")

    data_root = _data_root()
    artifacts_dir = _artifact_root() / "pubchem-payload-capture"

    with sync_playwright() as p:
        browser = _launch_chromium(p)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        request = context.request

        processed = 0
        skipped = 0
        for target in targets:
            output_dir = data_root / str(target.cid)
            if args.skip_existing and (output_dir / "meta.json").is_file():
                skipped += 1
                print(
                    f"[capture_skip] cid={target.cid} hazard={target.key or '-'} "
                    f"display_name={target.display_name or '-'}",
                    flush=True,
                )
                continue
            print(
                f"[capture_start] cid={target.cid} hazard={target.key or '-'} "
                f"display_name={target.display_name or '-'}",
                flush=True,
            )
            _capture(
                page=page,
                request=request,
                target=target,
                output_dir=output_dir,
                artifacts_dir=artifacts_dir,
                timeout_ms=args.timeout_ms,
            )
            processed += 1
            print(f"[capture_done] cid={target.cid} output_dir={output_dir}", flush=True)

        context.close()
        browser.close()

    total = len(targets)
    print(f"Summary: processed={processed} skipped={skipped} total={total}", flush=True)
    print(f"Wrote payloads under {data_root}", flush=True)


if __name__ == "__main__":
    main()
