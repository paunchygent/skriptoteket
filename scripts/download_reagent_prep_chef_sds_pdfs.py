"""Download Carl Roth SDS PDFs for Reagent Prep Chef missing-coverage targets.

This module implements a permanent, safety-first SDS download pipeline for PR-0068.
It is designed for respectful traffic patterns (rate limiting + retries + jitter),
resumable execution, and deterministic outputs.

Relationships:
- Reads curated hazards data from
  `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/hazards.json`.
- Reads missing coverage keys from `data/reagent_prep_chef/sds/gaps.md`.
- Writes SDS PDFs to `data/reagent_prep_chef/sds/files/` (gitignored).
- Produces JSON state/report artifacts suitable for later markdown sync/index rebuild.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.carlroth.com"
SEARCH_PATH = "/com/en/search/"
DEFAULT_HAZARDS_PATH = Path(
    "src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/hazards.json"
)
DEFAULT_GAPS_PATH = Path("data/reagent_prep_chef/sds/gaps.md")
DEFAULT_OUTPUT_DIR = Path("data/reagent_prep_chef/sds/files")
DEFAULT_STATE_PATH = Path(".artifacts/sds-carlroth/state.json")
DEFAULT_REPORT_PATH = Path(".artifacts/sds-carlroth/report.json")
DEFAULT_OVERRIDES_PATH = Path("scripts/data/reagent_prep_chef_sds_carlroth_overrides.json")

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
DISFAVORED_PRODUCT_TERMS = {
    "solution",
    "buffer",
    "tablet",
    "tablets",
    "mixture",
    "kit",
    "set",
    "indicator",
    "test strip",
    "hydrometer",
    "wash bottle",
}


@dataclass(frozen=True, slots=True)
class ThrottlePolicy:
    """Request pacing policy used to reduce rate-limit and ban risk.

    Attributes:
        min_delay_seconds: Lower bound for jittered delay between requests.
        max_delay_seconds: Upper bound for jittered delay between requests.
    """

    min_delay_seconds: float
    max_delay_seconds: float


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Retry/backoff policy for transient HTTP failures."""

    max_attempts: int
    base_backoff_seconds: float


@dataclass(frozen=True, slots=True)
class CompoundTarget:
    """A single compound we want to source an SDS PDF for."""

    key: str
    display_name: str
    search_queries: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProductCandidate:
    """A Carl Roth product candidate from search results."""

    url: str
    title: str


@dataclass(frozen=True, slots=True)
class SdsDocument:
    """An SDS PDF link discovered on a product page."""

    label: str
    url: str
    country_code: str | None
    language_code: str | None


@dataclass(frozen=True, slots=True)
class DownloadOutcome:
    """Outcome record for one target, used in state/report outputs."""

    key: str
    status: str
    reason: str | None
    selected_query: str | None
    selected_product_url: str | None
    selected_sds_url: str | None
    saved_path: str | None
    fallback_queries: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TargetOverride:
    """Manual per-target overrides validated from Carl Roth product pages.

    Attributes:
        product_urls: Optional explicit product pages to try before search.
        prepend_queries: Optional search queries inserted before auto-generated ones.
    """

    product_urls: tuple[str, ...]
    prepend_queries: tuple[str, ...]


class RateLimiter:
    """Simple jittered serial limiter to keep request cadence conservative."""

    def __init__(self, policy: ThrottlePolicy) -> None:
        self._policy = policy
        self._next_allowed = time.monotonic()

    def wait_turn(self) -> None:
        now = time.monotonic()
        if now < self._next_allowed:
            time.sleep(self._next_allowed - now)
        delay = random.uniform(self._policy.min_delay_seconds, self._policy.max_delay_seconds)
        self._next_allowed = time.monotonic() + delay


class ThrottledHttpClient:
    """HTTP client with pacing + retry/backoff and shared session cookies."""

    def __init__(
        self,
        *,
        throttle: ThrottlePolicy,
        retry: RetryPolicy,
        timeout_seconds: float,
        user_agent: str,
    ) -> None:
        self._limiter = RateLimiter(throttle)
        self._retry = retry
        self._timeout_seconds = timeout_seconds
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,sv-SE;q=0.8,sv;q=0.7",
            }
        )

    def close(self) -> None:
        self._session.close()

    def get_text(
        self,
        *,
        url: str,
        params: dict[str, str] | None = None,
        referer: str | None = None,
    ) -> str:
        response = self._request(url=url, params=params, referer=referer)
        return response.text

    def get_bytes(self, *, url: str, referer: str | None = None) -> tuple[bytes, dict[str, str]]:
        response = self._request(url=url, referer=referer)
        return response.content, dict(response.headers)

    def _request(
        self,
        *,
        url: str,
        params: dict[str, str] | None = None,
        referer: str | None = None,
    ) -> requests.Response:
        headers: dict[str, str] = {}
        if referer:
            headers["Referer"] = referer

        last_error: Exception | None = None
        for attempt in range(1, self._retry.max_attempts + 1):
            self._limiter.wait_turn()
            try:
                response = self._session.get(
                    url,
                    params=params,
                    headers=headers or None,
                    timeout=self._timeout_seconds,
                )
            except requests.RequestException as exc:
                last_error = exc
                self._sleep_before_retry(attempt=attempt, retry_after=None)
                continue

            if response.status_code in RETRYABLE_STATUS:
                retry_after = _parse_retry_after_seconds(response.headers.get("Retry-After"))
                self._sleep_before_retry(attempt=attempt, retry_after=retry_after)
                last_error = RuntimeError(f"HTTP {response.status_code} from {response.url}")
                continue

            response.raise_for_status()
            return response

        if last_error is None:
            raise RuntimeError(f"Request failed without explicit error for {url}")
        raise RuntimeError(f"Request failed after retries for {url}: {last_error}") from last_error

    def _sleep_before_retry(self, *, attempt: int, retry_after: float | None) -> None:
        if attempt >= self._retry.max_attempts:
            return
        jitter = random.uniform(0.1, 0.8)
        backoff = self._retry.base_backoff_seconds * (2 ** (attempt - 1))
        delay = max(retry_after or 0.0, backoff + jitter)
        time.sleep(delay)


class TargetCatalog:
    """Loads and resolves target compounds from hazards + gaps documents."""

    def __init__(self, *, hazards_path: Path, gaps_path: Path) -> None:
        self._hazards_path = hazards_path
        self._gaps_path = gaps_path

    def load_targets(
        self, *, explicit_keys: list[str], max_targets: int | None
    ) -> list[CompoundTarget]:
        hazards = self._load_hazards()
        keys = explicit_keys or self._load_missing_markdown_keys()
        targets: list[CompoundTarget] = []

        for key in keys:
            hazard = hazards.get(key)
            if hazard is None:
                continue
            display_name = str(hazard.get("display_name") or key)
            search_queries = _build_search_queries(hazard=hazard)
            if not search_queries:
                continue
            targets.append(
                CompoundTarget(
                    key=key,
                    display_name=display_name,
                    search_queries=tuple(search_queries),
                )
            )

        if max_targets is not None:
            return targets[:max_targets]
        return targets

    def _load_hazards(self) -> dict[str, dict[str, Any]]:
        payload = json.loads(self._hazards_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise RuntimeError(f"Unexpected hazards payload in {self._hazards_path}")
        out: dict[str, dict[str, Any]] = {}
        for item in payload:
            if isinstance(item, dict) and isinstance(item.get("key"), str):
                out[str(item["key"])] = item
        return out

    def _load_missing_markdown_keys(self) -> list[str]:
        content = self._gaps_path.read_text(encoding="utf-8")
        return re.findall(r"^-\s+`([^`]+)`\s*$", content, flags=re.MULTILINE)


class RothHtmlParser:
    """Parses Carl Roth search/product HTML into structured candidates."""

    @staticmethod
    def extract_product_candidates(*, html: str) -> list[ProductCandidate]:
        soup = BeautifulSoup(html, "lxml")
        by_url: dict[str, ProductCandidate] = {}

        for anchor in soup.find_all("a", href=True):
            href = str(anchor["href"])
            if "/com/en/" not in href or "/p/" not in href:
                continue
            title = _normalize_whitespace(anchor.get_text(" ", strip=True))
            if title.lower() in {"", "go to product selection", "new"}:
                continue
            url = urljoin(BASE_URL, href)
            existing = by_url.get(url)
            if existing is None or len(title) > len(existing.title):
                by_url[url] = ProductCandidate(url=url, title=title)

        return list(by_url.values())

    @staticmethod
    def extract_sds_documents(*, html: str) -> list[SdsDocument]:
        soup = BeautifulSoup(html, "lxml")
        out: list[SdsDocument] = []
        seen: set[str] = set()

        for anchor in soup.find_all("a", href=True):
            href = str(anchor["href"])
            if "/medias/SDB-" not in href or ".pdf" not in href.lower():
                continue
            absolute_url = urljoin(BASE_URL, href)
            base_url = absolute_url.split("?", 1)[0]
            if base_url in seen:
                continue
            seen.add(base_url)

            label = _normalize_whitespace(anchor.get_text(" ", strip=True))
            country_code, language_code = _extract_locale_codes(base_url)
            out.append(
                SdsDocument(
                    label=label,
                    url=absolute_url,
                    country_code=country_code,
                    language_code=language_code,
                )
            )

        return out


class RothSelector:
    """Ranks products and chooses the best SDS document by language preference."""

    def rank_products(
        self,
        *,
        target: CompoundTarget,
        query: str,
        candidates: list[ProductCandidate],
    ) -> list[ProductCandidate]:
        scored = [
            (
                self._score_product(target=target, query=query, candidate=candidate),
                candidate,
            )
            for candidate in candidates
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [candidate for _, candidate in scored]

    def choose_sds_document(self, *, docs: list[SdsDocument]) -> SdsDocument | None:
        if not docs:
            return None

        def _priority(doc: SdsDocument) -> tuple[int, str]:
            lang = (doc.language_code or "").upper()
            country = (doc.country_code or "").upper()
            if lang == "SV" and country == "SE":
                return (0, doc.label)
            if lang == "SV":
                return (1, doc.label)
            if lang == "EN":
                return (2, doc.label)
            return (3, doc.label)

        return sorted(docs, key=_priority)[0]

    def _score_product(
        self,
        *,
        target: CompoundTarget,
        query: str,
        candidate: ProductCandidate,
    ) -> int:
        title = candidate.title.lower()
        query_lower = query.lower()
        key_lower = target.key.lower()

        score = 0
        if query_lower and query_lower in title:
            score += 120
        if key_lower and key_lower in title:
            score += 80

        query_tokens = {token for token in re.split(r"[^a-z0-9]+", query_lower) if len(token) >= 3}
        for token in query_tokens:
            if token in title:
                score += 12

        if target.display_name.lower() in title:
            score += 20

        for bad_term in DISFAVORED_PRODUCT_TERMS:
            if bad_term in title:
                score -= 25

        return score


class StateStore:
    """Persists resumable execution state and outcomes."""

    def __init__(self, *, state_path: Path) -> None:
        self._path = state_path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self._path.is_file():
            return {"updated_at": _utc_now_iso(), "targets": {}}
        return json.loads(self._path.read_text(encoding="utf-8"))

    def save(self, *, payload: dict[str, Any]) -> None:
        payload["updated_at"] = _utc_now_iso()
        self._path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )


class RothSdsDownloadPipeline:
    """Coordinates search, selection, download, and reporting per target."""

    def __init__(
        self,
        *,
        client: ThrottledHttpClient,
        parser: RothHtmlParser,
        selector: RothSelector,
        output_dir: Path,
        max_product_candidates: int,
        dry_run: bool,
        overrides: dict[str, TargetOverride],
    ) -> None:
        self._client = client
        self._parser = parser
        self._selector = selector
        self._output_dir = output_dir
        self._max_product_candidates = max_product_candidates
        self._dry_run = dry_run
        self._overrides = overrides
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def run_target(self, *, target: CompoundTarget) -> DownloadOutcome:
        override = self._overrides.get(target.key)
        if override is not None:
            for product_url in override.product_urls:
                outcome = self._attempt_product_url(
                    target=target,
                    query=f"override:{product_url}",
                    product_url=product_url,
                    referer=urljoin(BASE_URL, SEARCH_PATH),
                )
                if outcome is not None:
                    return outcome

        for query in self._iter_queries(target=target, override=override):
            search_url = urljoin(BASE_URL, SEARCH_PATH)
            search_html = self._client.get_text(url=search_url, params={"text": query})
            candidates = self._parser.extract_product_candidates(html=search_html)
            ranked = self._selector.rank_products(target=target, query=query, candidates=candidates)

            for candidate in ranked[: self._max_product_candidates]:
                outcome = self._attempt_product_url(
                    target=target,
                    query=query,
                    product_url=candidate.url,
                    referer=search_url,
                )
                if outcome is not None:
                    return outcome

        return DownloadOutcome(
            key=target.key,
            status="not_found",
            reason="No suitable Carl Roth SDS PDF found after ranked search/product traversal.",
            selected_query=None,
            selected_product_url=None,
            selected_sds_url=None,
            saved_path=None,
            fallback_queries=_atlas_fallback_queries(target=target),
        )

    def _iter_queries(
        self, *, target: CompoundTarget, override: TargetOverride | None
    ) -> tuple[str, ...]:
        values: list[str] = []
        if override is not None:
            values.extend(override.prepend_queries)
        values.extend(target.search_queries)
        return tuple(_dedupe_nonempty_strings(values))

    def _attempt_product_url(
        self,
        *,
        target: CompoundTarget,
        query: str,
        product_url: str,
        referer: str,
    ) -> DownloadOutcome | None:
        product_html = self._client.get_text(url=product_url, referer=referer)
        docs = self._parser.extract_sds_documents(html=product_html)
        selected_doc = self._selector.choose_sds_document(docs=docs)
        if selected_doc is None:
            return None

        file_name = f"{target.key}__carlroth__undated.pdf"
        output_path = self._output_dir / file_name

        if self._dry_run:
            return DownloadOutcome(
                key=target.key,
                status="planned",
                reason=None,
                selected_query=query,
                selected_product_url=product_url,
                selected_sds_url=selected_doc.url,
                saved_path=str(output_path),
                fallback_queries=(),
            )

        payload, headers = self._client.get_bytes(url=selected_doc.url, referer=product_url)
        if not payload.startswith(b"%PDF"):
            return None

        revision = _resolve_revision(headers=headers)
        output_path = self._output_dir / f"{target.key}__carlroth__{revision}.pdf"
        _atomic_write_bytes(path=output_path, payload=payload)

        return DownloadOutcome(
            key=target.key,
            status="downloaded",
            reason=None,
            selected_query=query,
            selected_product_url=product_url,
            selected_sds_url=selected_doc.url,
            saved_path=str(output_path),
            fallback_queries=(),
        )


def _parse_retry_after_seconds(raw: str | None) -> float | None:
    if not raw:
        return None
    stripped = raw.strip()
    if stripped.isdigit():
        return float(stripped)
    try:
        dt = parsedate_to_datetime(stripped)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    seconds = (dt - datetime.now(tz=UTC)).total_seconds()
    return max(seconds, 0.0)


def _resolve_revision(*, headers: dict[str, str]) -> str:
    raw_last_modified = headers.get("last-modified")
    if not raw_last_modified:
        return "undated"
    try:
        parsed = parsedate_to_datetime(raw_last_modified)
    except (TypeError, ValueError):
        return "undated"
    if parsed.year <= 1970:
        return "undated"
    return parsed.date().isoformat()


def _extract_locale_codes(url_without_query: str) -> tuple[str | None, str | None]:
    match = re.search(r"/SDB-[A-Z0-9]+-([A-Z]{2})-([A-Z]{2})\.pdf$", url_without_query)
    if not match:
        return None, None
    return match.group(1), match.group(2)


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def _build_search_queries(*, hazard: dict[str, Any]) -> list[str]:
    queries: list[str] = []

    search_aliases = hazard.get("search_aliases")
    if isinstance(search_aliases, list):
        for alias in search_aliases:
            if isinstance(alias, str) and alias.strip():
                queries.append(alias.strip())

    display_name = str(hazard.get("display_name") or "").strip()
    if display_name:
        cleaned = re.sub(r"\s*\([^)]*\)", "", display_name).strip()
        if cleaned:
            queries.append(cleaned)

    key = str(hazard.get("key") or "").strip()
    if key:
        queries.append(key)

    return _dedupe_nonempty_strings(queries)


def _dedupe_nonempty_strings(values: list[str] | tuple[str, ...]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        lowered = normalized.casefold()
        if lowered in seen:
            continue
        seen.add(lowered)
        out.append(normalized)
    return out


def _load_target_overrides(*, path: Path) -> dict[str, TargetOverride]:
    if not path.is_file():
        return {}

    payload = json.loads(path.read_text(encoding="utf-8"))
    targets_payload = payload.get("targets")
    if not isinstance(targets_payload, dict):
        raise RuntimeError(f"Invalid overrides payload in {path}")

    overrides: dict[str, TargetOverride] = {}
    for key, entry in targets_payload.items():
        if not isinstance(key, str) or not isinstance(entry, dict):
            continue
        urls = entry.get("product_urls")
        queries = entry.get("prepend_queries")
        if not isinstance(urls, list):
            urls = []
        if not isinstance(queries, list):
            queries = []

        clean_urls = _dedupe_nonempty_strings([str(item) for item in urls if isinstance(item, str)])
        clean_queries = _dedupe_nonempty_strings(
            [str(item) for item in queries if isinstance(item, str)]
        )
        overrides[key] = TargetOverride(
            product_urls=tuple(clean_urls),
            prepend_queries=tuple(clean_queries),
        )

    return overrides


def _atlas_fallback_queries(*, target: CompoundTarget) -> tuple[str, ...]:
    english_anchor = target.search_queries[0] if target.search_queries else target.display_name
    return (
        f"{target.display_name} säkerhetsdatablad pdf",
        f"{english_anchor} SDS pdf",
        f"{target.key} SDS pdf",
    )


def _atomic_write_bytes(*, path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_bytes(payload)
    tmp_path.replace(path)


def _utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hazards-path", type=Path, default=DEFAULT_HAZARDS_PATH)
    parser.add_argument("--gaps-path", type=Path, default=DEFAULT_GAPS_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--overrides-path", type=Path, default=DEFAULT_OVERRIDES_PATH)
    parser.add_argument(
        "--key", action="append", default=[], help="Explicit compound key to process."
    )
    parser.add_argument("--max-targets", type=int, default=None)
    parser.add_argument("--max-product-candidates", type=int, default=8)
    parser.add_argument("--min-delay-seconds", type=float, default=1.4)
    parser.add_argument("--max-delay-seconds", type=float, default=3.2)
    parser.add_argument("--max-attempts", type=int, default=5)
    parser.add_argument("--base-backoff-seconds", type=float, default=2.0)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--user-agent",
        default=(
            "Mozilla/5.0 (compatible; Skriptoteket-SDS-Curation/1.0; "
            "+https://skriptoteket.hule.education)"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    catalog = TargetCatalog(hazards_path=args.hazards_path, gaps_path=args.gaps_path)
    targets = catalog.load_targets(explicit_keys=list(args.key), max_targets=args.max_targets)
    overrides = _load_target_overrides(path=args.overrides_path)

    state_store = StateStore(state_path=args.state_path)
    state_payload = state_store.load()
    target_state = state_payload.setdefault("targets", {})

    throttle_policy = ThrottlePolicy(
        min_delay_seconds=args.min_delay_seconds,
        max_delay_seconds=args.max_delay_seconds,
    )
    retry_policy = RetryPolicy(
        max_attempts=args.max_attempts,
        base_backoff_seconds=args.base_backoff_seconds,
    )

    client = ThrottledHttpClient(
        throttle=throttle_policy,
        retry=retry_policy,
        timeout_seconds=args.timeout_seconds,
        user_agent=args.user_agent,
    )

    pipeline = RothSdsDownloadPipeline(
        client=client,
        parser=RothHtmlParser(),
        selector=RothSelector(),
        output_dir=args.output_dir,
        max_product_candidates=args.max_product_candidates,
        dry_run=args.dry_run,
        overrides=overrides,
    )

    try:
        outcomes: list[DownloadOutcome] = []
        for target in targets:
            existing = target_state.get(target.key)
            if (
                not args.force
                and isinstance(existing, dict)
                and existing.get("status") == "downloaded"
            ):
                continue

            outcome = pipeline.run_target(target=target)
            target_state[target.key] = asdict(outcome)
            outcomes.append(outcome)
            state_store.save(payload=state_payload)
            print(f"[sds_download] key={target.key} status={outcome.status}")

        report_payload = {
            "generated_at": _utc_now_iso(),
            "summary": {
                "targets_considered": len(targets),
                "processed_this_run": len(outcomes),
                "downloaded": sum(1 for item in outcomes if item.status == "downloaded"),
                "planned": sum(1 for item in outcomes if item.status == "planned"),
                "not_found": sum(1 for item in outcomes if item.status == "not_found"),
            },
            "outcomes": [asdict(item) for item in outcomes],
        }
        args.report_path.parent.mkdir(parents=True, exist_ok=True)
        args.report_path.write_text(
            json.dumps(report_payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(f"[sds_report] wrote={args.report_path}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
