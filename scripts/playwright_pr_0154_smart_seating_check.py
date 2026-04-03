"""Live PR-0154 proof for Klassrumskartan smart seating.

This script is a targeted browser proof for a bounded slice. It is not a
canonical release gate and should be pruned once its scoped contract is covered
elsewhere.


This browser check seeds precise smart-seating scenarios through the real local
API, then verifies the shipped teacher workflow in the live SPA against the
`PR-0154` contract:

- Smart off keeps local `Slumpa`
- Smart on + no history blocks honestly
- Smart on + eligible history applies a backend result
- crowded-room and conflicting-rule cases return the best available result
- repeated smart reruns prefer a different strong candidate
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import requests
from playwright.sync_api import Page, expect, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_classroom_planner import (
    focus_workspace_mode,
    login_to_app,
    open_class_workspace,
)
from scripts._playwright_config import get_config

ARTIFACTS_DIR = Path(".artifacts/pr-0154-smart-seating")


def _api_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme and parsed.hostname and parsed.port == 5173:
        return f"{parsed.scheme}://{parsed.hostname}:8000"
    return base_url.rstrip("/")


def _login_api(*, api_base_url: str, email: str, password: str) -> tuple[requests.Session, str]:
    session = requests.Session()
    response = session.post(
        f"{api_base_url}/api/v1/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    response.raise_for_status()
    csrf_token = response.json()["csrf_token"]
    return session, csrf_token


def _api_get(session: requests.Session, *, api_base_url: str, path: str) -> dict[str, Any]:
    response = session.get(f"{api_base_url}{path}", timeout=30)
    response.raise_for_status()
    return response.json()


def _api_mutate(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = session.request(
        method=method,
        url=f"{api_base_url}{path}",
        json=payload,
        headers={"X-CSRF-Token": csrf_token},
        timeout=30,
    )
    response.raise_for_status()
    if not response.content:
        return {}
    return response.json()


def _create_roster(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    name: str,
    students: list[str],
) -> dict[str, Any]:
    return _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="POST",
        path="/api/v1/apps/classroom.group-seating-studio/rosters",
        payload={
            "name": name,
            "students": [
                {"id": _student_id_from_name(student_name), "display_name": student_name}
                for student_name in students
            ],
        },
    )


def _student_id_from_name(student_name: str) -> str:
    return student_name.lower().replace(" ", "-")


def _create_template(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    name: str,
    seats: list[dict[str, Any]],
    fixtures: list[dict[str, Any]],
    grid_cols: int,
    grid_rows: int,
) -> dict[str, Any]:
    return _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="POST",
        path="/api/v1/apps/classroom.group-seating-studio/templates",
        payload={
            "name": name,
            "grid_cols": grid_cols,
            "grid_rows": grid_rows,
            "seats": seats,
            "fixtures": fixtures,
        },
    )


def _create_seating_draft(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    roster_id: str,
    template_id: str,
) -> dict[str, Any]:
    return _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="POST",
        path="/api/v1/apps/classroom.group-seating-studio/drafts/seating/new",
        payload={"roster_id": roster_id, "template_id": template_id},
    )


def _patch_draft(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    draft_id: str,
    expected_revision: int,
    **fields: Any,
) -> dict[str, Any]:
    payload = {"expected_revision": expected_revision, **fields}
    return _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="PATCH",
        path=f"/api/v1/apps/classroom.group-seating-studio/drafts/{draft_id}",
        payload=payload,
    )


def _get_workspace(
    session: requests.Session,
    *,
    api_base_url: str,
    draft_id: str,
) -> dict[str, Any]:
    return _api_get(
        session,
        api_base_url=api_base_url,
        path=f"/api/v1/apps/classroom.group-seating-studio/drafts/{draft_id}/workspace",
    )


def _patch_smart_rules(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    roster_id: str,
    expected_revision: int,
    seating_preferences: list[dict[str, Any]],
    relationship_rules: list[dict[str, Any]],
) -> dict[str, Any]:
    return _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="PATCH",
        path=f"/api/v1/apps/classroom.group-seating-studio/rosters/{roster_id}/smart-rules",
        payload={
            "expected_revision": expected_revision,
            "seating_preferences": seating_preferences,
            "relationship_rules": relationship_rules,
        },
    )


def _create_export_checkpoint(
    session: requests.Session,
    *,
    api_base_url: str,
    csrf_token: str,
    draft_id: str,
) -> None:
    job = _api_mutate(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        method="POST",
        path=f"/api/v1/apps/classroom.group-seating-studio/drafts/seating/{draft_id}/exports/jobs",
        payload={
            "export_kind": "pdf",
            "layout_id": "pretty_brutalist_poster",
            "paper_size": "a3_landscape",
        },
    )
    job_id = job["job_id"]
    for _ in range(60):
        status_payload = _api_get(
            session,
            api_base_url=api_base_url,
            path=f"/api/v1/apps/classroom.group-seating-studio/exports/jobs/{job_id}",
        )
        status = status_payload["status"]
        if status == "succeeded":
            return
        if status == "failed":
            raise AssertionError(f"Seating export job failed: {status_payload.get('error')}")
        time.sleep(1)
    raise AssertionError("Timed out waiting for seating export checkpoint creation.")


def _select_seating_workspace(page: Page, *, roster_name: str) -> None:
    page.goto(
        page.url.split("/apps/")[0] + "/apps/classroom.group-seating-studio",
        wait_until="domcontentloaded",
    )
    open_class_workspace(page, roster_name=roster_name)
    focus_workspace_mode(page, label="Sittplatser")
    expect(page.locator('[data-test="seating-workspace"]')).to_be_visible(timeout=60000)


def _set_checkbox(page: Page, *, data_test: str, checked: bool) -> None:
    page.locator(f'[data-test="{data_test}"] input').set_checked(checked)


def _seat_assignments_by_student(workspace: dict[str, Any]) -> dict[str, str]:
    return {
        assignment["student_id"]: assignment["seat_id"]
        for assignment in workspace["seat_assignments"]
    }


def _orthogonally_adjacent(
    assignments: dict[str, str],
    *,
    seat_lookup: dict[str, tuple[int, int]],
    left_student_id: str,
    right_student_id: str,
) -> bool:
    left = seat_lookup[assignments[left_student_id]]
    right = seat_lookup[assignments[right_student_id]]
    same_row = left[1] == right[1] and abs(left[0] - right[0]) == 1
    same_column = left[0] == right[0] and abs(left[1] - right[1]) == 1
    return same_row or same_column


def _scenario_names(prefix: str) -> dict[str, str]:
    return {
        "random": f"{prefix} Random",
        "history": f"{prefix} History",
        "crowded": f"{prefix} Crowded",
        "conflict": f"{prefix} Conflict",
        "diversity": f"{prefix} Diversity",
    }


def main() -> None:
    config = get_config()
    base_url = config.base_url.rstrip("/")
    api_base_url = _api_base_url(base_url)
    names = _scenario_names(prefix=f"PR0154 {uuid4().hex[:6]}")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    session, csrf_token = _login_api(
        api_base_url=api_base_url,
        email=config.email,
        password=config.password,
    )

    random_roster = _create_roster(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        name=names["random"],
        students=["Ada Random", "Bo Random", "Cia Random"],
    )
    shared_template = _create_template(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        name=f"{names['random']} Room",
        grid_cols=4,
        grid_rows=3,
        seats=[
            {"id": "front-left", "x": 0, "y": 0, "zone": "front"},
            {"id": "front-right", "x": 1, "y": 0, "zone": "front"},
            {"id": "back-left", "x": 0, "y": 1, "zone": "back"},
            {"id": "back-right", "x": 1, "y": 1, "zone": "back"},
        ],
        fixtures=[
            {"id": "board-right", "type": "whiteboard", "x": 3, "y": 0, "width": 1, "height": 2}
        ],
    )
    random_draft = _create_seating_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=random_roster["id"],
        template_id=shared_template["id"],
    )
    random_workspace = _patch_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        draft_id=random_draft["id"],
        expected_revision=random_draft["revision"],
        seat_assignments=[{"student_id": "ada-random", "seat_id": "front-left"}],
    )

    history_roster = _create_roster(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        name=names["history"],
        students=["Ada History", "Bo History", "Cia History", "Dio History"],
    )
    history_draft = _create_seating_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=history_roster["id"],
        template_id=shared_template["id"],
    )
    history_workspace = _patch_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        draft_id=history_draft["id"],
        expected_revision=history_draft["revision"],
        seat_assignments=[
            {"student_id": "ada-history", "seat_id": "front-left"},
            {"student_id": "bo-history", "seat_id": "front-right"},
            {"student_id": "cia-history", "seat_id": "back-left"},
            {"student_id": "dio-history", "seat_id": "back-right"},
        ],
    )
    _create_export_checkpoint(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        draft_id=history_draft["id"],
    )
    history_workspace = _patch_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        draft_id=history_draft["id"],
        expected_revision=history_workspace["draft"]["revision"],
        seat_assignments=[
            {"student_id": "ada-history", "seat_id": "back-left"},
            {"student_id": "bo-history", "seat_id": "front-left"},
            {"student_id": "cia-history", "seat_id": "front-right"},
            {"student_id": "dio-history", "seat_id": "back-right"},
        ],
    )
    _patch_smart_rules(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=history_roster["id"],
        expected_revision=0,
        seating_preferences=[{"student_id": "ada-history", "near_teacher": True}],
        relationship_rules=[],
    )

    crowded_roster = _create_roster(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        name=names["crowded"],
        students=["Ada Crowded", "Bo Crowded", "Cia Crowded", "Dio Crowded", "Eli Crowded"],
    )
    crowded_draft = _create_seating_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=crowded_roster["id"],
        template_id=shared_template["id"],
    )

    conflict_roster = _create_roster(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        name=names["conflict"],
        students=["Ada Conflict", "Bo Conflict", "Cia Conflict"],
    )
    conflict_template = _create_template(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        name=f"{names['conflict']} Room",
        grid_cols=4,
        grid_rows=2,
        seats=[
            {"id": "seat-a", "x": 0, "y": 0, "zone": "front"},
            {"id": "seat-b", "x": 1, "y": 0, "zone": "front"},
            {"id": "seat-c", "x": 2, "y": 0, "zone": "front"},
        ],
        fixtures=[
            {"id": "board-top", "type": "whiteboard", "x": 0, "y": 0, "width": 1, "height": 1}
        ],
    )
    conflict_draft = _create_seating_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=conflict_roster["id"],
        template_id=conflict_template["id"],
    )
    _patch_smart_rules(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=conflict_roster["id"],
        expected_revision=0,
        seating_preferences=[],
        relationship_rules=[
            {
                "id": "conflict-apart",
                "kind": "keep_apart",
                "student_ids": ["ada-conflict", "bo-conflict", "cia-conflict"],
            }
        ],
    )

    diversity_roster = _create_roster(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        name=names["diversity"],
        students=["Ada Diversity", "Bo Diversity"],
    )
    diversity_template = _create_template(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        name=f"{names['diversity']} Room",
        grid_cols=2,
        grid_rows=1,
        seats=[
            {"id": "left", "x": 0, "y": 0, "zone": "front"},
            {"id": "right", "x": 1, "y": 0, "zone": "front"},
        ],
        fixtures=[
            {"id": "board-top", "type": "whiteboard", "x": 0, "y": 0, "width": 1, "height": 1}
        ],
    )
    diversity_draft = _create_seating_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=diversity_roster["id"],
        template_id=diversity_template["id"],
    )

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        login_to_app(page, base_url=base_url, email=config.email, password=config.password)

        _select_seating_workspace(page, roster_name=names["random"])
        before_random = _seat_assignments_by_student(random_workspace)
        expect(page.locator('[data-test="seating-smart-run-message"]')).to_have_count(0)
        page.locator('[data-test="randomize-seating"]').click()
        page.wait_for_timeout(1600)
        after_random = _seat_assignments_by_student(
            _get_workspace(session, api_base_url=api_base_url, draft_id=random_draft["id"])
        )
        assert before_random != after_random, "Smart off should keep local random seating behavior."
        page.screenshot(path=str(ARTIFACTS_DIR / "smart-off-random.png"), full_page=True)

        _set_checkbox(page, data_test="seating-smart-toggle", checked=True)
        _set_checkbox(page, data_test="seating-use-history-toggle", checked=True)
        before_blocked = _seat_assignments_by_student(
            _get_workspace(session, api_base_url=api_base_url, draft_id=random_draft["id"])
        )
        page.locator('[data-test="randomize-seating"]').click()
        expect(page.locator('[data-test="seating-smart-run-message"]')).to_contain_text(
            "För att använda historik behöver du först exportera ett sittschema för just det här klassrummet."
        )
        after_blocked = _seat_assignments_by_student(
            _get_workspace(session, api_base_url=api_base_url, draft_id=random_draft["id"])
        )
        assert before_blocked == after_blocked, "No-history block must not mutate assignments."
        page.screenshot(path=str(ARTIFACTS_DIR / "smart-no-history-blocked.png"), full_page=True)

        _select_seating_workspace(page, roster_name=names["history"])
        _set_checkbox(page, data_test="seating-smart-toggle", checked=True)
        _set_checkbox(page, data_test="seating-use-history-toggle", checked=True)
        before_history = _seat_assignments_by_student(history_workspace)
        page.locator('[data-test="randomize-seating"]').click()
        expect(page.locator('[data-test="seating-smart-run-message"]')).to_contain_text(
            "Smart placering klar"
        )
        page.wait_for_timeout(600)
        after_history = _seat_assignments_by_student(
            _get_workspace(session, api_base_url=api_base_url, draft_id=history_draft["id"])
        )
        assert before_history != after_history, (
            "Eligible history run should apply a backend result."
        )
        assert after_history["ada-history"] in {"front-right", "back-right"}, (
            "Teacher-edge inference with a right-wall whiteboard should prefer right-side seats "
            "for near-teacher students."
        )
        page.screenshot(path=str(ARTIFACTS_DIR / "smart-history-applied.png"), full_page=True)

        _select_seating_workspace(page, roster_name=names["crowded"])
        _set_checkbox(page, data_test="seating-smart-toggle", checked=True)
        page.locator('[data-test="randomize-seating"]').click()
        expect(page.locator('[data-test="seating-smart-run-message"]')).to_contain_text(
            "bästa möjliga kompromiss"
        )
        crowded_workspace = _get_workspace(
            session, api_base_url=api_base_url, draft_id=crowded_draft["id"]
        )
        assert len(crowded_workspace["seat_assignments"]) == 4
        assert len(crowded_workspace["roster"]["students"]) == 5
        page.screenshot(path=str(ARTIFACTS_DIR / "smart-crowded-compromise.png"), full_page=True)

        _select_seating_workspace(page, roster_name=names["conflict"])
        _set_checkbox(page, data_test="seating-smart-toggle", checked=True)
        page.locator('[data-test="randomize-seating"]').click()
        expect(page.locator('[data-test="seating-smart-run-message"]')).to_contain_text(
            "bästa möjliga kompromiss"
        )
        conflict_workspace = _get_workspace(
            session, api_base_url=api_base_url, draft_id=conflict_draft["id"]
        )
        conflict_assignments = _seat_assignments_by_student(conflict_workspace)
        conflict_seat_lookup = {"seat-a": (0, 0), "seat-b": (1, 0), "seat-c": (2, 0)}
        assert _orthogonally_adjacent(
            conflict_assignments,
            seat_lookup=conflict_seat_lookup,
            left_student_id="ada-conflict",
            right_student_id="bo-conflict",
        ) or _orthogonally_adjacent(
            conflict_assignments,
            seat_lookup=conflict_seat_lookup,
            left_student_id="bo-conflict",
            right_student_id="cia-conflict",
        ), "Conflicting keep-apart rules in one three-seat row should require a compromise."
        page.screenshot(path=str(ARTIFACTS_DIR / "smart-conflict-compromise.png"), full_page=True)

        _select_seating_workspace(page, roster_name=names["diversity"])
        _set_checkbox(page, data_test="seating-smart-toggle", checked=True)
        page.locator('[data-test="randomize-seating"]').click()
        page.wait_for_timeout(600)
        first_diversity = _seat_assignments_by_student(
            _get_workspace(session, api_base_url=api_base_url, draft_id=diversity_draft["id"])
        )
        page.locator('[data-test="randomize-seating"]').click()
        page.wait_for_timeout(600)
        second_diversity = _seat_assignments_by_student(
            _get_workspace(session, api_base_url=api_base_url, draft_id=diversity_draft["id"])
        )
        assert first_diversity != second_diversity, (
            "Repeated smart reruns should prefer a different strong candidate when one exists."
        )
        page.screenshot(path=str(ARTIFACTS_DIR / "smart-rerun-diversity.png"), full_page=True)

        context.close()
        browser.close()

    print(f"PR-0154 smart seating proof artifacts written to: {ARTIFACTS_DIR}")


if __name__ == "__main__":
    main()
