from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from scripts.playwright_ui_smoke import _launch_chromium
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.hazards_store import (
    InMemoryReagentPrepChefHazardStore,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers import (
    extract_pdf_text,
    is_sds_document,
)


@dataclass(frozen=True)
class Target:
    cid: int
    key: str | None
    display_name: str | None
    queries: list[str]


def _artifact_root() -> Path:
    env = os.environ.get("ARTIFACTS_ROOT")
    if env:
        return Path(env)
    return Path(".artifacts")


def _hazards_path() -> Path:
    from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef import hazards_store

    return Path(hazards_store.__file__).with_name("hazards.json")


def _fallback_query_name(display_name: str | None) -> str | None:
    if not display_name:
        return None
    overrides = {
        "Koppar(II)oxid": "Copper(II) oxide",
    }
    return overrides.get(display_name, display_name)


def _build_queries(
    *, hazard_key: str | None, display_name: str | None, aliases: list[str]
) -> list[str]:
    names = [alias for alias in aliases if alias]
    if not names:
        fallback = _fallback_query_name(display_name)
        if fallback:
            names = [fallback]
    queries: list[str] = []
    for name in names:
        queries.append(f"{name} safety data sheet pdf")
        queries.append(f"{name} SDS pdf")
    return list(dict.fromkeys(queries))


def _select_targets(*, cids: list[int], hazards: list[str]) -> list[Target]:
    store = InMemoryReagentPrepChefHazardStore(hazards_path=_hazards_path())
    hazards_by_key = {hazard.key: hazard for hazard in store.list_all()}
    hazards_by_cid = {
        hazard.pubchem_cid: hazard for hazard in store.list_all() if hazard.pubchem_cid is not None
    }

    targets: list[Target] = []

    for cid in cids:
        hazard = hazards_by_cid.get(cid)
        aliases = list(hazard.search_aliases) if hazard else []
        queries = _build_queries(
            hazard_key=hazard.key if hazard else None,
            display_name=hazard.display_name if hazard else None,
            aliases=aliases,
        )
        targets.append(
            Target(
                cid=cid,
                key=hazard.key if hazard else None,
                display_name=hazard.display_name if hazard else None,
                queries=queries,
            )
        )

    for key in hazards:
        hazard = hazards_by_key.get(key)
        if hazard is None:
            raise SystemExit(f"Unknown hazard key: {key}")
        if hazard.pubchem_cid is None:
            raise SystemExit(f"Hazard {key} saknar pubchem_cid.")
        queries = _build_queries(
            hazard_key=hazard.key,
            display_name=hazard.display_name,
            aliases=list(hazard.search_aliases),
        )
        targets.append(
            Target(
                cid=hazard.pubchem_cid,
                key=hazard.key,
                display_name=hazard.display_name,
                queries=queries,
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


def _verify_pdf(*, url: str, timeout_ms: int, artifacts_dir: Path, prefix: str) -> dict:
    timeout = max(timeout_ms / 1000, 1)
    entry = {
        "url": url,
        "status": None,
        "content_type": "",
        "bytes": 0,
        "looks_like_sds": False,
        "checked": False,
        "error": None,
    }
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        entry["error"] = str(exc)
        return entry
    entry["status"] = response.status_code
    entry["content_type"] = response.headers.get("content-type", "")
    body = response.content
    entry["bytes"] = len(body)
    if response.status_code != 200:
        return entry
    if "application/pdf" not in entry["content_type"].lower() and not url.lower().endswith(".pdf"):
        return entry
    file_path = artifacts_dir / f"{prefix}.pdf"
    file_path.write_bytes(body)
    entry["file"] = str(file_path)
    try:
        text = extract_pdf_text(body)
        entry["checked"] = True
        entry["looks_like_sds"] = is_sds_document(text)
    except Exception as exc:  # noqa: BLE001
        entry["error"] = str(exc)
    return entry


def _search(query: str, timeout_ms: int) -> list[str]:
    url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    timeout = max(timeout_ms / 1000, 1)
    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=timeout,
    )
    if response.status_code != 200:
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    links = [link.get("href") for link in soup.select("a.result__a") if link.get("href")]
    return links


def _normalize_url(url: str) -> str | None:
    if not url:
        return None
    if url.startswith("//"):
        url = "https:" + url
    parsed = urlparse(url)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        params = parse_qs(parsed.query)
        uddg = params.get("uddg")
        if uddg and uddg[0]:
            return unquote(uddg[0])
    return url


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


def _extract_page_candidates(page) -> list[dict]:
    links = page.evaluate(
        """() => Array.from(document.querySelectorAll('a[href]')).map(a => ({
            href: a.href || '',
            text: (a.textContent || '').trim(),
            title: a.getAttribute('title') || ''
        }))"""
    )
    candidates: list[dict] = []
    for link in links:
        url = str(link.get("href") or "")
        text = str(link.get("text") or "")
        title = str(link.get("title") or "")
        candidate = _is_candidate(url, text, title)
        if candidate:
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
        help="Timeout per request (milliseconds).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".artifacts/sds-manual-lookup/report.json"),
        help="Write aggregated JSON report here.",
    )
    parser.add_argument(
        "--progress",
        type=Path,
        default=Path(".artifacts/sds-manual-lookup/progress.jsonl"),
        help="Write JSONL progress entries after each CID.",
    )
    parser.add_argument(
        "--promote-curated",
        type=Path,
        default=None,
        help="If set, append verified SDS URLs into the curated linkout store JSON.",
    )
    parser.add_argument(
        "--replace-curated",
        action="store_true",
        help="Replace curated entries for each CID instead of appending.",
    )
    args = parser.parse_args()

    targets = _select_targets(cids=args.cid, hazards=args.hazard)
    if not targets:
        raise SystemExit("No targets provided.")

    artifacts_dir = _artifact_root() / "sds-manual-lookup"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    promoted: dict[str, list[dict]] = {}

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.progress.parent.mkdir(parents=True, exist_ok=True)

    with (
        args.progress.open("w", encoding="utf-8") as progress_file,
        sync_playwright() as playwright,
    ):
        browser = _launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        for target in targets:
            print(
                f"[lookup_start] cid={target.cid} hazard={target.key or '-'} "
                f"display_name={target.display_name or '-'}",
                flush=True,
            )
            candidates: list[dict] = []
            verified: list[dict] = []
            for query in target.queries:
                links = _search(query, args.timeout_ms)
                for link in links[:5]:
                    normalized = _normalize_url(link)
                    if not normalized:
                        continue
                    entry = {
                        "query": query,
                        "url": normalized,
                        "source": "search_result",
                    }
                    if normalized.lower().endswith(".pdf"):
                        check = _verify_pdf(
                            url=normalized,
                            timeout_ms=args.timeout_ms,
                            artifacts_dir=artifacts_dir,
                            prefix=f"{target.cid}-{len(candidates)}",
                        )
                        entry.update(check)
                        if check.get("looks_like_sds"):
                            verified.append(entry)
                        candidates.append(entry)
                        continue

                    try:
                        page.goto(
                            normalized, wait_until="domcontentloaded", timeout=args.timeout_ms
                        )
                        page.wait_for_timeout(1000)
                    except Exception as exc:  # noqa: BLE001
                        entry["error"] = str(exc)
                        candidates.append(entry)
                        continue

                    page_candidates = _extract_page_candidates(page)
                    entry["page_candidates"] = page_candidates
                    candidates.append(entry)
                    for page_candidate in page_candidates:
                        url = page_candidate["url"]
                        check = _verify_pdf(
                            url=url,
                            timeout_ms=args.timeout_ms,
                            artifacts_dir=artifacts_dir,
                            prefix=f"{target.cid}-{len(candidates)}",
                        )
                        page_candidate.update(check)
                        if check.get("looks_like_sds"):
                            verified.append(page_candidate)
            screenshot_path = artifacts_dir / f"{target.cid}.png"
            page.screenshot(path=str(screenshot_path), full_page=True)
            record = {
                "cid": target.cid,
                "hazard_key": target.key,
                "display_name": target.display_name,
                "queries": target.queries,
                "candidates": candidates,
                "verified": verified,
                "screenshot": str(screenshot_path),
                "captured_at": datetime.now(tz=timezone.utc).isoformat(),
            }
            results.append(record)
            if verified:
                promoted[str(target.cid)] = [
                    {
                        "url": item["url"],
                        "source": "manual-playwright",
                        "verified": True,
                        "notes": f"{target.display_name or target.key or target.cid}",
                    }
                    for item in verified
                    if isinstance(item.get("url"), str)
                ]
            print(
                f"[lookup_done] cid={target.cid} candidates={len(candidates)} "
                f"verified={len(verified)}",
                flush=True,
            )
            progress_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            progress_file.flush()

            payload = {
                "version": 1,
                "generated_at": datetime.now(tz=timezone.utc).isoformat(),
                "results": results,
            }
            args.output.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            if args.promote_curated:
                curated_path = args.promote_curated
                curated_payload = {
                    "version": 1,
                    "as_of": datetime.now(tz=timezone.utc).date().isoformat(),
                    "entries": {},
                }
                if curated_path.is_file():
                    curated_payload = json.loads(curated_path.read_text(encoding="utf-8"))
                entries = curated_payload.get("entries") or {}
                for cid, items in promoted.items():
                    if args.replace_curated:
                        entries[cid] = items
                        continue
                    existing = entries.get(cid) or []
                    seen = {item.get("url") for item in existing if isinstance(item, dict)}
                    for item in items:
                        url = item.get("url")
                        if url in seen:
                            continue
                        seen.add(url)
                        existing.append(item)
                    entries[cid] = existing
                curated_payload["entries"] = entries
                curated_payload["as_of"] = datetime.now(tz=timezone.utc).date().isoformat()
                curated_path.write_text(
                    json.dumps(curated_payload, ensure_ascii=False, indent=2), encoding="utf-8"
                )

        context.close()
        browser.close()

    payload = {
        "version": 1,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "results": results,
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote report: {args.output}", flush=True)

    if args.promote_curated:
        print(f"Promoted verified SDS URLs into {args.promote_curated}", flush=True)
    print("[done] sds manual lookup finished", flush=True)


if __name__ == "__main__":
    main()
