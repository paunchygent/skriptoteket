"""Request-level smoke for class-scoped draft kinds in Klassrumskartan.

This script is the canonical request-level planner API baseline. It should stay
green alongside the browser smoke so class-scoped draft ownership remains
guarded even when targeted planner proofs are pruned.

This script uses the repo's standard smoke-test config to log in, create
temporary planner assets, and verify that active drafts now coexist per class
and draft kind instead of per owner. It writes a small JSON summary artifact so
the verification trail is easy to inspect later.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import requests

from scripts._playwright_config import get_config
from scripts._playwright_huleedu_auth import create_signed_huleedu_api_session


def _api_base_url(base_url: str) -> str:
    """Map a frontend base URL to the backend API root used in local dev."""

    if base_url.startswith("http://127.0.0.1:5173") or base_url.startswith("http://localhost:5173"):
        return "http://127.0.0.1:8000"
    return base_url


def _create_roster(
    session: requests.Session, *, api_base_url: str, csrf_token: str, name: str
) -> str:
    """Create a small roster and return its id."""

    response = session.post(
        f"{api_base_url}/api/v1/apps/classroom.group-seating-studio/rosters",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "name": name,
            "students": [
                {"id": "s1", "display_name": "Ada Lovelace"},
                {"id": "s2", "display_name": "Bo Berg"},
            ],
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["id"]


def _create_template(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    name: str,
) -> str:
    """Create a small classroom template and return its id."""

    response = session.post(
        f"{api_base_url}/api/v1/apps/classroom.group-seating-studio/templates",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "name": name,
            "seats": [
                {"id": "seat-1", "x": 0, "y": 0, "zone": "front"},
                {"id": "seat-2", "x": 1, "y": 0, "zone": "front"},
            ],
            "fixtures": [],
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["id"]


def _resolve_draft(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    roster_id: str,
    draft_kind: str,
    template_id: str | None,
) -> dict[str, Any]:
    """Resolve a draft for one class and kind."""

    response = session.post(
        f"{api_base_url}/api/v1/apps/classroom.group-seating-studio/drafts/resolve",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "roster_id": roster_id,
            "draft_kind": draft_kind,
            "template_id": template_id,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    """Run the class-scoped draft-kind API smoke."""

    config = get_config()
    base_url = config.base_url.rstrip("/")
    api_base_url = _api_base_url(base_url)
    artifacts_dir = Path(".artifacts/pr-0085-live-check")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    suffix = str(int(time.time()))

    auth = create_signed_huleedu_api_session(
        email=config.email,
        display_name="Draft Kind Smoke Teacher",
        jti=f"classroom-planner-draft-kind-{suffix}",
    )
    session = auth.api_session
    csrf_token = "huleedu-gateway-context"

    roster_one_id = _create_roster(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        name=f"PR-0085 Klass A {suffix}",
    )
    roster_two_id = _create_roster(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        name=f"PR-0085 Klass B {suffix}",
    )
    template_id = _create_template(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        name=f"PR-0085 Sal {suffix}",
    )

    seating_one = _resolve_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=roster_one_id,
        draft_kind="seating",
        template_id=template_id,
    )
    seating_two = _resolve_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=roster_two_id,
        draft_kind="seating",
        template_id=template_id,
    )
    seating_one_again = _resolve_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=roster_one_id,
        draft_kind="seating",
        template_id=template_id,
    )
    grouping_one = _resolve_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=roster_one_id,
        draft_kind="grouping",
        template_id=None,
    )
    grouping_one_again = _resolve_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=roster_one_id,
        draft_kind="grouping",
        template_id=None,
    )
    seating_one_after_grouping = _resolve_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=roster_one_id,
        draft_kind="seating",
        template_id=template_id,
    )

    assert seating_one["id"] != seating_two["id"]
    assert seating_one_again["id"] == seating_one["id"]
    assert grouping_one["id"] == grouping_one_again["id"]
    assert seating_one_after_grouping["id"] == seating_one["id"]
    assert grouping_one["id"] != seating_one["id"]
    assert grouping_one["template_id"] is None
    assert grouping_one["draft_kind"] == "grouping"
    assert seating_one["draft_kind"] == "seating"

    summary = {
        "api_base_url": api_base_url,
        "roster_one_id": roster_one_id,
        "roster_two_id": roster_two_id,
        "template_id": template_id,
        "seating_one_id": seating_one["id"],
        "seating_two_id": seating_two["id"],
        "grouping_one_id": grouping_one["id"],
    }
    summary_path = artifacts_dir / "draft-kind-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Draft-kind smoke summary written to: {summary_path}")


if __name__ == "__main__":
    main()
